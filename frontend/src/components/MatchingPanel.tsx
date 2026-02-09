import { MatchingResult, PaymentMatch } from "@/types";
import { cn } from "@/lib/utils";
import { CheckCircle, XCircle, AlertTriangle } from "lucide-react";

interface MatchingPanelProps {
  matching: MatchingResult | null;
  className?: string;
}

export function MatchingPanel({ matching, className }: MatchingPanelProps) {
  if (!matching) {
    return (
      <div className={cn("rounded-lg border bg-card p-4", className)}>
        <h4 className="font-medium text-foreground mb-3">Rapprochement des Paiements</h4>
        <p className="text-sm text-muted-foreground">Aucune donnée de rapprochement disponible</p>
      </div>
    );
  }

  const getConfidenceColor = (score: number) => {
    if (score >= 80) return "text-success";
    if (score >= 60) return "text-warning";
    return "text-destructive";
  };

  const getConfidenceIcon = (score: number) => {
    if (score >= 80) return CheckCircle;
    if (score >= 60) return AlertTriangle;
    return XCircle;
  };

  const ConfidenceIcon = getConfidenceIcon(matching.overall_confidence);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('fr-MA', {
      style: 'currency',
      currency: 'MAD',
      minimumFractionDigits: 2
    }).format(amount);
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'PAID': return 'Payé';
      case 'PARTIALLY_PAID': return 'Partiellement payé';
      case 'UNPAID': return 'Non payé';
      default: return status;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'PAID': return 'text-success bg-success/10';
      case 'PARTIALLY_PAID': return 'text-warning bg-warning/10';
      case 'UNPAID': return 'text-destructive bg-destructive/10';
      default: return 'text-muted-foreground bg-muted';
    }
  };

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="flex items-center justify-between p-4 border-b">
        <h4 className="font-medium text-foreground">Rapprochement des Paiements</h4>
        <div className={cn("flex items-center gap-1", getConfidenceColor(matching.overall_confidence))}>
          <ConfidenceIcon className="h-4 w-4" />
          <span className="font-medium">{matching.overall_confidence}%</span>
        </div>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Status */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Statut:</span>
          <span className={cn("px-2 py-0.5 rounded text-xs font-medium", getStatusColor(matching.payment_status))}>
            {getStatusLabel(matching.payment_status)}
          </span>
        </div>

        {/* Summary */}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Total payé:</span>
          <span className="font-medium text-foreground">{formatCurrency(matching.total_paid)}</span>
        </div>
        
        {matching.remaining_amount > 0 && (
          <div className="flex items-center gap-2 text-sm text-warning bg-warning/10 px-2 py-1 rounded">
            <AlertTriangle className="h-4 w-4" />
            <span>Reste à payer: {formatCurrency(matching.remaining_amount)}</span>
          </div>
        )}

        {/* Payment matches */}
        {matching.matches.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Paiements Rapprochés ({matching.matches.length})
            </p>
            {matching.matches.map((match: PaymentMatch, index: number) => (
              <div
                key={match.payment_id || index}
                className="flex items-center justify-between p-2 rounded bg-muted/50 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className={cn(
                    "text-xs px-1.5 py-0.5 rounded",
                    match.confidence_score >= 80 ? "bg-success/10 text-success" :
                    match.confidence_score >= 60 ? "bg-warning/10 text-warning" :
                    "bg-destructive/10 text-destructive"
                  )}>
                    {match.confidence_score}%
                  </span>
                </div>
                <span className="font-medium text-foreground">
                  {formatCurrency(match.matched_amount)}
                </span>
              </div>
            ))}
          </div>
        )}

        {matching.matches.length === 0 && (
          <p className="text-sm text-muted-foreground">Aucun paiement rapproché</p>
        )}
      </div>
    </div>
  );
}
