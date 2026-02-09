import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Calculator, TrendingUp, AlertCircle, CheckCircle } from "lucide-react";

interface CalculationStep {
  label: string;
  formula: string;
  due_date?: string;
  payment_date?: string;
  days_overdue?: number;
  months_of_delay?: number;
  base_rate?: number;
  months?: number;
  increment?: number;
  penalty_rate?: number;
  unpaid_amount?: number;
  base_penalty?: number;
  legal_status?: string;
  penalty_suspended?: boolean;
  final_penalty?: number;
}

interface MonthBreakdown {
  month: number;
  rate: number;
  is_applied: boolean;
}

interface CalculationBreakdown {
  base_rate_percent: number;
  monthly_increment_percent: number;
  months_breakdown: MonthBreakdown[];
  calculation_steps: {
    step1_delay: CalculationStep;
    step2_rate: CalculationStep;
    step3_amount: CalculationStep;
    step4_status: CalculationStep;
  };
}

interface PenaltyBreakdownProps {
  breakdown: CalculationBreakdown;
  penaltyAmount: number;
  penaltySuspended: boolean;
}

export function PenaltyBreakdown({ breakdown, penaltyAmount, penaltySuspended }: PenaltyBreakdownProps) {
  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-MA', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const formatDate = (dateStr?: string) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: 'long',
      year: 'numeric'
    });
  };

  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Calculator className="h-5 w-5 text-primary" />
          Détail du Calcul des Pénalités DGI
        </CardTitle>
        <p className="text-sm text-muted-foreground">
          Calcul conforme à l'Article 78-3 du Code Général des Impôts
        </p>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Configuration des taux */}
        <div className="p-4 bg-muted/50 rounded-lg">
          <h4 className="font-semibold mb-3 flex items-center gap-2">
            <TrendingUp className="h-4 w-4" />
            Configuration DGI
          </h4>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Taux de base (1er mois):</span>
              <span className="ml-2 font-semibold text-primary">{breakdown.base_rate_percent.toFixed(2)}%</span>
            </div>
            <div>
              <span className="text-muted-foreground">Incrément mensuel:</span>
              <span className="ml-2 font-semibold text-primary">+{breakdown.monthly_increment_percent.toFixed(2)}%</span>
            </div>
          </div>
        </div>

        {/* Étapes de calcul */}
        <div className="space-y-4">
          <h4 className="font-semibold">Étapes de Calcul</h4>
          
          {/* Étape 1: Calcul du retard */}
          <div className="border-l-4 border-blue-500 pl-4 py-2">
            <div className="flex items-start justify-between mb-2">
              <h5 className="font-medium text-blue-700">
                1. {breakdown.calculation_steps.step1_delay.label}
              </h5>
              <Badge variant="outline" className="bg-blue-50">
                {breakdown.calculation_steps.step1_delay.months_of_delay} mois
              </Badge>
            </div>
            <div className="text-sm space-y-1 text-muted-foreground">
              <p>📅 Date d'échéance: <span className="font-mono">{formatDate(breakdown.calculation_steps.step1_delay.due_date)}</span></p>
              <p>💳 Date de paiement: <span className="font-mono">{formatDate(breakdown.calculation_steps.step1_delay.payment_date)}</span></p>
              <p>⏱️ Retard: <span className="font-semibold text-foreground">{breakdown.calculation_steps.step1_delay.days_overdue} jours calendaires</span></p>
            </div>
            <div className="mt-2 p-2 bg-blue-50 rounded text-sm font-mono">
              {breakdown.calculation_steps.step1_delay.formula}
            </div>
          </div>

          {/* Étape 2: Calcul du taux */}
          <div className="border-l-4 border-purple-500 pl-4 py-2">
            <div className="flex items-start justify-between mb-2">
              <h5 className="font-medium text-purple-700">
                2. {breakdown.calculation_steps.step2_rate.label}
              </h5>
              <Badge variant="outline" className="bg-purple-50">
                {breakdown.calculation_steps.step2_rate.penalty_rate}%
              </Badge>
            </div>
            <div className="mt-2 p-2 bg-purple-50 rounded text-sm font-mono">
              {breakdown.calculation_steps.step2_rate.formula}
            </div>
            
            {/* Tableau des taux par mois */}
            <div className="mt-3 overflow-x-auto">
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-purple-100">
                    <th className="border p-2 text-left">Mois</th>
                    <th className="border p-2 text-right">Taux</th>
                    <th className="border p-2 text-center">Appliqué</th>
                  </tr>
                </thead>
                <tbody>
                  {breakdown.months_breakdown.slice(0, 15).map((month) => (
                    <tr key={month.month} className={month.is_applied ? 'bg-purple-50 font-semibold' : ''}>
                      <td className="border p-2">Mois {month.month}</td>
                      <td className="border p-2 text-right font-mono">{month.rate.toFixed(2)}%</td>
                      <td className="border p-2 text-center">
                        {month.is_applied ? (
                          <CheckCircle className="h-4 w-4 text-green-600 inline" />
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {breakdown.months_breakdown.length > 15 && (
                <div className="mt-2 p-2 bg-purple-100 rounded text-xs text-center text-purple-700">
                  <AlertCircle className="h-3 w-3 inline mr-1" />
                  Affichage limité à 15 mois. Total: {breakdown.months_breakdown.length} mois de retard.
                </div>
              )}
            </div>
          </div>

          {/* Étape 3: Calcul du montant */}
          <div className="border-l-4 border-orange-500 pl-4 py-2">
            <div className="flex items-start justify-between mb-2">
              <h5 className="font-medium text-orange-700">
                3. {breakdown.calculation_steps.step3_amount.label}
              </h5>
              <Badge variant="outline" className="bg-orange-50">
                {formatAmount(breakdown.calculation_steps.step3_amount.base_penalty || 0)} MAD
              </Badge>
            </div>
            <div className="text-sm space-y-1 text-muted-foreground mb-2">
              <p>💰 Montant impayé: <span className="font-semibold text-foreground">{formatAmount(breakdown.calculation_steps.step3_amount.unpaid_amount || 0)} MAD</span></p>
              <p>📊 Taux appliqué: <span className="font-semibold text-foreground">{breakdown.calculation_steps.step3_amount.penalty_rate}%</span></p>
            </div>
            <div className="mt-2 p-2 bg-orange-50 rounded text-sm font-mono">
              {breakdown.calculation_steps.step3_amount.formula}
            </div>
          </div>

          {/* Étape 4: Application du statut */}
          <div className={`border-l-4 ${penaltySuspended ? 'border-yellow-500' : 'border-green-500'} pl-4 py-2`}>
            <div className="flex items-start justify-between mb-2">
              <h5 className={`font-medium ${penaltySuspended ? 'text-yellow-700' : 'text-green-700'}`}>
                4. {breakdown.calculation_steps.step4_status.label}
              </h5>
              <Badge variant={penaltySuspended ? "destructive" : "default"} className={penaltySuspended ? "bg-yellow-500" : "bg-green-500"}>
                {breakdown.calculation_steps.step4_status.legal_status}
              </Badge>
            </div>
            <div className={`mt-2 p-2 ${penaltySuspended ? 'bg-yellow-50' : 'bg-green-50'} rounded text-sm font-mono`}>
              {breakdown.calculation_steps.step4_status.formula}
            </div>
            {penaltySuspended && (
              <div className="mt-2 flex items-start gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-sm">
                <AlertCircle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                <p className="text-yellow-800">
                  La pénalité est <strong>suspendue</strong> en raison du statut juridique de la facture. 
                  Le montant calculé ({formatAmount(breakdown.calculation_steps.step3_amount.base_penalty || 0)} MAD) 
                  ne sera pas appliqué tant que le statut n'est pas résolu.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Résultat final */}
        <div className={`p-4 rounded-lg ${penaltySuspended ? 'bg-yellow-100 border-2 border-yellow-300' : 'bg-green-100 border-2 border-green-300'}`}>
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground mb-1">Pénalité Finale</p>
              <p className="text-2xl font-bold">
                {formatAmount(penaltyAmount)} MAD
              </p>
            </div>
            {penaltySuspended ? (
              <Badge variant="destructive" className="bg-yellow-500 text-yellow-900">
                SUSPENDUE
              </Badge>
            ) : (
              <Badge variant="default" className="bg-green-600">
                APPLICABLE
              </Badge>
            )}
          </div>
        </div>

        {/* Note légale */}
        <div className="text-xs text-muted-foreground p-3 bg-muted/30 rounded border">
          <p className="font-semibold mb-1">📋 Référence légale:</p>
          <p>
            Calcul conforme à l'Article 78-3 du Code Général des Impôts marocain.
            Règle DGI: "Tout mois entamé est décompté entièrement" - même un seul jour de retard 
            dans un mois calendaire compte comme un mois complet de pénalité.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
