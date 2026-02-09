import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { batchAPI } from "@/lib/api";
import { Batch, BatchStatus } from "@/types";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { 
  Loader2, 
  CheckCircle, 
  XCircle, 
  FileSearch, 
  FileText, 
  Link as LinkIcon,
  Calculator,
  ClipboardCheck,
  AlertTriangle
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ProcessingStep {
  key: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  statuses: BatchStatus[];
}

const PROCESSING_STEPS: ProcessingStep[] = [
  { 
    key: 'ocr', 
    label: 'OCR - Extraction de texte', 
    icon: FileSearch,
    statuses: ['ocr_processing'] 
  },
  { 
    key: 'extraction', 
    label: 'Extraction des données', 
    icon: FileText,
    statuses: ['extraction_done'] 
  },
  { 
    key: 'matching', 
    label: 'Rapprochement factures-paiements', 
    icon: LinkIcon,
    statuses: ['matching_done'] 
  },
  { 
    key: 'rules', 
    label: 'Calcul des délais et pénalités', 
    icon: Calculator,
    statuses: ['rules_calculated'] 
  },
  { 
    key: 'validation', 
    label: 'Vérification finale', 
    icon: ClipboardCheck,
    statuses: ['validation_pending', 'validated', 'exported'] 
  },
];

export default function BatchProcessing() {
  const { id: batchId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [pollingEnabled, setPollingEnabled] = useState(true);

  const { data: batch, error } = useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => batchAPI.get(batchId!),
    enabled: !!batchId,
    refetchInterval: pollingEnabled ? 2000 : false,
  });

  // Handle status changes
  useEffect(() => {
    if (!batch) return;

    if (batch.status === 'validation_pending') {
      setPollingEnabled(false);
      navigate(`/batches/${batchId}/validate`);
    } else if (batch.status === 'validated' || batch.status === 'exported') {
      setPollingEnabled(false);
      navigate(`/batches/${batchId}/results`);
    } else if (batch.status === 'failed') {
      setPollingEnabled(false);
    }
  }, [batch?.status, batchId, navigate]);

  const getStepStatus = (step: ProcessingStep): 'pending' | 'active' | 'completed' | 'failed' => {
    if (!batch) return 'pending';
    if (batch.status === 'failed') return 'failed';

    const stepIndex = PROCESSING_STEPS.findIndex(s => s.key === step.key);
    const currentStepIndex = PROCESSING_STEPS.findIndex(s => s.statuses.includes(batch.status));

    if (currentStepIndex > stepIndex) return 'completed';
    if (currentStepIndex === stepIndex) return 'active';
    return 'pending';
  };

  if (error) {
    return (
      <div className="max-w-2xl mx-auto py-12">
        <Card className="border-destructive/50">
          <CardContent className="pt-6 text-center">
            <XCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-foreground mb-2">Erreur</h2>
            <p className="text-muted-foreground">Impossible de charger le lot</p>
            <Button className="mt-4" onClick={() => navigate("/dashboard")}>
              Retour au tableau de bord
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-2xl font-bold text-foreground">Traitement en cours</h1>
        <p className="text-muted-foreground mt-1">
          {batch?.company_name} • Lot #{batchId?.slice(0, 8)}
        </p>
      </div>

      {/* Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Progression</CardTitle>
            <StatusBadge status={batch?.status || 'created'} />
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Progress value={batch?.progress_percentage || 0} className="h-3" />
            <p className="text-sm text-center text-muted-foreground">
              {batch?.progress_percentage || 0}% - {batch?.current_step || 'Initialisation...'}
            </p>
          </div>

          {/* Steps */}
          <div className="space-y-4">
            {PROCESSING_STEPS.map((step) => {
              const status = getStepStatus(step);
              const Icon = step.icon;
              
              return (
                <div 
                  key={step.key}
                  className={cn(
                    "flex items-center gap-4 p-3 rounded-lg border",
                    status === 'active' && "border-primary bg-primary/5",
                    status === 'completed' && "border-success/50 bg-success/5",
                    status === 'failed' && "border-destructive/50 bg-destructive/5",
                    status === 'pending' && "border-border opacity-50"
                  )}
                >
                  <div className={cn(
                    "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center",
                    status === 'active' && "bg-primary text-primary-foreground",
                    status === 'completed' && "bg-success text-success-foreground",
                    status === 'failed' && "bg-destructive text-destructive-foreground",
                    status === 'pending' && "bg-muted text-muted-foreground"
                  )}>
                    {status === 'active' ? (
                      <Loader2 className="h-5 w-5 animate-spin" />
                    ) : status === 'completed' ? (
                      <CheckCircle className="h-5 w-5" />
                    ) : status === 'failed' ? (
                      <XCircle className="h-5 w-5" />
                    ) : (
                      <Icon className="h-5 w-5" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className={cn(
                      "font-medium",
                      status === 'active' && "text-primary",
                      status === 'completed' && "text-success",
                      status === 'failed' && "text-destructive",
                      status === 'pending' && "text-muted-foreground"
                    )}>
                      {step.label}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Error message */}
          {batch?.status === 'failed' && batch.error_message && (
            <div className="flex items-start gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
              <AlertTriangle className="h-5 w-5 text-destructive flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-destructive">Erreur de traitement</p>
                <p className="text-sm text-muted-foreground mt-1">{batch.error_message}</p>
              </div>
            </div>
          )}

          {/* Stats */}
          {batch && (
            <div className="grid grid-cols-3 gap-4 pt-4 border-t">
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">{batch.total_invoices}</p>
                <p className="text-xs text-muted-foreground">Factures</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-foreground">{batch.total_payments}</p>
                <p className="text-xs text-muted-foreground">Paiements</p>
              </div>
              <div className="text-center">
                <p className={cn(
                  "text-2xl font-bold",
                  batch.critical_alerts_count > 0 ? "text-destructive" : 
                  batch.alerts_count > 0 ? "text-warning" : "text-foreground"
                )}>
                  {batch.alerts_count}
                </p>
                <p className="text-xs text-muted-foreground">Alertes</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Failed state actions */}
      {batch?.status === 'failed' && (
        <div className="flex gap-3">
          <Button variant="outline" className="flex-1" onClick={() => navigate("/dashboard")}>
            Retour au tableau de bord
          </Button>
          <Button className="flex-1" onClick={() => navigate(`/batches/${batchId}/upload`)}>
            Réessayer
          </Button>
        </div>
      )}
    </div>
  );
}
