import { LegalResult } from "@/types";
import { format, addDays } from "date-fns";
import { fr } from "date-fns/locale";
import { cn } from "@/lib/utils";
import { 
  AlertTriangle, 
  Calendar, 
  Clock, 
  DollarSign, 
  Percent, 
  RefreshCw,
  Calculator,
  Info
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface ComputedLegalPanelProps {
  legal: LegalResult | null;
  onRecompute?: () => void;
  isLoading?: boolean;
  className?: string;
}

export function ComputedLegalPanel({ 
  legal, 
  onRecompute,
  isLoading = false,
  className 
}: ComputedLegalPanelProps) {
  if (!legal) {
    return (
      <div className={cn("rounded-lg border bg-card p-4", className)}>
        <h4 className="font-medium text-foreground mb-3">Calcul Légal</h4>
        <p className="text-sm text-muted-foreground">
          Aucun calcul effectué. Assurez-vous que la date de livraison est définie.
        </p>
        {onRecompute && (
          <Button 
            variant="outline" 
            size="sm" 
            className="mt-3"
            onClick={onRecompute}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-2", isLoading && "animate-spin")} />
            Calculer
          </Button>
        )}
      </div>
    );
  }

  const formatDate = (date: string | null | undefined) => {
    if (!date) return '—';
    return format(new Date(date), 'dd/MM/yyyy', { locale: fr });
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-MA', {
      style: 'currency',
      currency: 'MAD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  // Calculate due date from delivery date + legal delay
  const calculatedDueDate = legal.legal_start_date 
    ? format(addDays(new Date(legal.legal_start_date), legal.applied_legal_delay_days), 'dd/MM/yyyy', { locale: fr })
    : '—';

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="flex items-center justify-between p-4 border-b">
        <h4 className="font-medium text-foreground flex items-center gap-2">
          <Calculator className="h-4 w-4" />
          Calcul Légal
        </h4>
        {onRecompute && (
          <Button 
            variant="ghost" 
            size="sm"
            onClick={onRecompute}
            disabled={isLoading}
          >
            <RefreshCw className={cn("h-4 w-4 mr-1", isLoading && "animate-spin")} />
            Recalculer
          </Button>
        )}
      </div>
      
      <div className="p-4 space-y-4">
        {/* Legal Delay Section */}
        <div className="bg-muted/50 rounded-lg p-3 space-y-2">
          <div className="flex items-center gap-2 text-sm font-medium">
            <Clock className="h-4 w-4 text-primary" />
            <span>Délai Légal</span>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-3 w-3 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="text-sm">
                    Le délai légal par défaut est de 60 jours à compter de la date de livraison 
                    (Article 78-2 de la loi n° 15-95).
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          
          <div className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Délai appliqué:</span>
              <span className="font-medium text-foreground">
                {legal.applied_legal_delay_days} jours
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Formule:</span>
              <span className="font-mono text-xs text-muted-foreground">
                Date livraison + {legal.applied_legal_delay_days}j
              </span>
            </div>
          </div>
        </div>

        {/* Dates section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Date de livraison:</span>
            <span className="font-medium text-foreground">{formatDate(legal.legal_start_date)}</span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Calendar className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Date d'échéance:</span>
            <span className={cn(
              "font-medium",
              legal.days_overdue > 0 ? "text-destructive" : "text-success"
            )}>
              {calculatedDueDate}
            </span>
          </div>
          {legal.actual_payment_date && (
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span className="text-muted-foreground">Date de paiement:</span>
              <span className="font-medium text-foreground">{formatDate(legal.actual_payment_date)}</span>
            </div>
          )}
        </div>

        <Separator />

        {/* Overdue section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <AlertTriangle className={cn(
              "h-4 w-4",
              legal.days_overdue > 0 ? "text-destructive" : "text-success"
            )} />
            <span className="text-muted-foreground">Jours de retard:</span>
            <span className={cn(
              "font-bold text-lg",
              legal.days_overdue > 0 ? "text-destructive" : "text-success"
            )}>
              {legal.days_overdue}
            </span>
          </div>
          <div className="flex items-center gap-2 text-sm">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Mois de retard (total):</span>
            <span className="font-medium text-foreground">{legal.months_of_delay}</span>
          </div>
        </div>

        <Separator />

        {/* DGI Delay Details */}
        <div className="space-y-2 bg-primary/5 rounded-lg p-3 border border-primary/20">
          <div className="flex items-center gap-2">
            <p className="text-xs font-medium text-primary uppercase tracking-wide">
              Détail des retards (DGI)
            </p>
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger>
                  <Info className="h-3 w-3 text-muted-foreground" />
                </TooltipTrigger>
                <TooltipContent side="top" className="max-w-xs">
                  <p className="text-sm">
                    Ces champs sont requis pour la déclaration DGI. Ils distinguent le retard 
                    sur les montants payés hors délai et les montants non encore payés.
                  </p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Mois retard (non payé):</span>
            <span className={cn(
              "font-medium",
              (legal.months_delay_unpaid || 0) > 0 ? "text-destructive" : "text-foreground"
            )}>
              {legal.months_delay_unpaid || 0} mois
            </span>
          </div>
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Mois retard (payé hors délai):</span>
            <span className={cn(
              "font-medium",
              (legal.months_delay_paid || 0) > 0 ? "text-warning" : "text-foreground"
            )}>
              {legal.months_delay_paid || 0} mois
            </span>
          </div>
        </div>

        <Separator />

        {/* Penalty section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm">
            <Percent className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Taux de pénalité:</span>
            <span className="font-medium text-foreground">
              {(legal.penalty_rate * 100).toFixed(2)}%
            </span>
          </div>
          
          {/* Penalty formula */}
          <div className="bg-muted/50 rounded p-2 text-xs font-mono text-muted-foreground">
            Pénalité = Montant × Taux × Mois de retard
          </div>
          
          <div className="flex items-center gap-2 text-sm">
            <DollarSign className="h-4 w-4 text-muted-foreground" />
            <span className="text-muted-foreground">Montant pénalité:</span>
            <span className={cn(
              "font-bold text-lg",
              legal.penalty_amount > 0 ? "text-destructive" : "text-success"
            )}>
              {formatCurrency(legal.penalty_amount)}
            </span>
          </div>
          
          {legal.penalty_suspended && (
            <div className="flex items-center gap-2 text-sm bg-warning/10 text-warning px-2 py-1 rounded">
              <AlertTriangle className="h-4 w-4" />
              <span>Pénalités suspendues (litige/procédure)</span>
            </div>
          )}
        </div>

        {/* Amounts summary */}
        <Separator />
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Montant TTC:</span>
            <span className="font-medium">{formatCurrency(legal.invoice_amount_ttc)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Montant payé:</span>
            <span className="font-medium text-success">{formatCurrency(legal.paid_amount)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">Montant impayé:</span>
            <span className={cn(
              "font-medium",
              legal.unpaid_amount > 0 ? "text-destructive" : "text-foreground"
            )}>
              {formatCurrency(legal.unpaid_amount)}
            </span>
          </div>
        </div>

        {/* Status */}
        {legal.legal_status && legal.legal_status !== 'NORMAL' && (
          <>
            <Separator />
            <div className="text-xs text-muted-foreground">
              Statut: <span className="font-medium">{legal.legal_status}</span>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
