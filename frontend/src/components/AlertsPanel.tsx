import { Alert } from "@/types";
import { SeverityBadge } from "./SeverityBadge";
import { cn } from "@/lib/utils";

interface AlertsPanelProps {
  alerts: Alert[];
  className?: string;
}

export function AlertsPanel({ alerts, className }: AlertsPanelProps) {
  if (alerts.length === 0) {
    return (
      <div className={cn("rounded-lg border bg-card p-4", className)}>
        <h4 className="font-medium text-foreground mb-3">Alertes</h4>
        <p className="text-sm text-muted-foreground">Aucune alerte</p>
      </div>
    );
  }

  // Sort by severity
  const severityOrder = { CRITICAL: 0, ERROR: 1, WARNING: 2, INFO: 3 };
  const sortedAlerts = [...alerts].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  );

  const criticalCount = alerts.filter(a => a.severity === 'CRITICAL').length;
  const errorCount = alerts.filter(a => a.severity === 'ERROR').length;
  const warningCount = alerts.filter(a => a.severity === 'WARNING').length;

  return (
    <div className={cn("rounded-lg border bg-card", className)}>
      <div className="flex items-center justify-between p-4 border-b">
        <h4 className="font-medium text-foreground">Alertes ({alerts.length})</h4>
        <div className="flex items-center gap-2">
          {criticalCount > 0 && (
            <span className="text-xs bg-destructive/10 text-destructive px-2 py-0.5 rounded">
              {criticalCount} critique
            </span>
          )}
          {errorCount > 0 && (
            <span className="text-xs bg-destructive/5 text-destructive px-2 py-0.5 rounded">
              {errorCount} erreur
            </span>
          )}
          {warningCount > 0 && (
            <span className="text-xs bg-warning/10 text-warning px-2 py-0.5 rounded">
              {warningCount} avertissement
            </span>
          )}
        </div>
      </div>
      
      <div className="p-2 max-h-80 overflow-y-auto scrollbar-thin">
        <div className="space-y-2">
          {sortedAlerts.map((alert, index) => (
            <div
              key={`${alert.code}-${index}`}
              className={cn(
                "p-3 rounded-md text-sm",
                alert.severity === 'CRITICAL' && "bg-destructive/10 border border-destructive/20",
                alert.severity === 'ERROR' && "bg-destructive/5",
                alert.severity === 'WARNING' && "bg-warning/10",
                alert.severity === 'INFO' && "bg-info/10"
              )}
            >
              <div className="flex items-start gap-2">
                <SeverityBadge severity={alert.severity} showIcon={false} className="mt-0.5">
                  {alert.severity}
                </SeverityBadge>
                <div className="flex-1 min-w-0">
                  <p className="text-foreground">{alert.message}</p>
                  {alert.field && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Champ: <code className="bg-muted px-1 rounded">{alert.field}</code>
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
