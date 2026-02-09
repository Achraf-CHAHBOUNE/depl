import { useState, useEffect } from "react";
import { Loader2, FileText, CheckCircle, AlertCircle, Eye, FileSearch } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type ProcessingStep = 
  | "uploading"
  | "ocr_invoice"
  | "ocr_statement"
  | "extracting"
  | "matching"
  | "calculating"
  | "complete"
  | "error";

interface OCRProgressIndicatorProps {
  isProcessing: boolean;
  error?: string | null;
  onComplete?: () => void;
  hasPaymentFile?: boolean;
}

const ALL_STEPS: { id: ProcessingStep; label: string; icon: typeof FileText; requiresPayment?: boolean }[] = [
  { id: "uploading", label: "Téléchargement des fichiers", icon: FileText },
  { id: "ocr_invoice", label: "OCR de la facture", icon: Eye },
  { id: "ocr_statement", label: "OCR du relevé bancaire", icon: FileSearch, requiresPayment: true },
  { id: "extracting", label: "Extraction des données", icon: FileText },
  { id: "matching", label: "Rapprochement", icon: FileText, requiresPayment: true },
  { id: "calculating", label: "Calcul des pénalités", icon: FileText, requiresPayment: true },
];

/**
 * Shows OCR processing progress with animated steps
 */
export function OCRProgressIndicator({ 
  isProcessing, 
  error,
  onComplete,
  hasPaymentFile = true
}: OCRProgressIndicatorProps) {
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [progress, setProgress] = useState(0);
  
  // Filter steps based on whether payment file exists
  const STEPS = hasPaymentFile 
    ? ALL_STEPS 
    : ALL_STEPS.filter(step => !step.requiresPayment);

  useEffect(() => {
    if (!isProcessing) {
      setCurrentStep(0);
      setProgress(0);
      return;
    }

    // Simulate progress through steps
    const stepDuration = 2000; // 2 seconds per step
    const progressInterval = 100;
    const progressIncrement = 100 / ((STEPS.length * stepDuration) / progressInterval);

    const progressTimer = setInterval(() => {
      setProgress(prev => {
        const next = prev + progressIncrement;
        return next > 100 ? 100 : next;
      });
    }, progressInterval);

    const stepTimer = setInterval(() => {
      setCurrentStep(prev => {
        const next = prev + 1;
        if (next >= STEPS.length) {
          clearInterval(stepTimer);
          clearInterval(progressTimer);
          onComplete?.();
          return prev;
        }
        return next;
      });
    }, stepDuration);

    return () => {
      clearInterval(progressTimer);
      clearInterval(stepTimer);
    };
  }, [isProcessing, onComplete]);

  if (error) {
    return (
      <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-6 text-center">
        <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
        <h3 className="font-medium text-lg text-foreground mb-2">
          Erreur de traitement
        </h3>
        <p className="text-sm text-muted-foreground">{error}</p>
      </div>
    );
  }

  if (!isProcessing) return null;

  return (
    <div className="bg-card border rounded-lg p-6 space-y-6">
      <div className="text-center">
        <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary mb-4" />
        <h3 className="font-medium text-lg text-foreground">
          Traitement OCR en cours
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Veuillez patienter pendant l'analyse de vos documents...
        </p>
      </div>

      <Progress value={progress} className="h-2" />

      <div className="space-y-3">
        {STEPS.map((step, index) => {
          const isComplete = index < currentStep;
          const isCurrent = index === currentStep;
          const isPending = index > currentStep;
          const Icon = step.icon;

          return (
            <div
              key={step.id}
              className={cn(
                "flex items-center gap-3 p-3 rounded-lg transition-colors",
                isComplete && "bg-success/10",
                isCurrent && "bg-primary/10",
                isPending && "opacity-50"
              )}
            >
              <div
                className={cn(
                  "h-8 w-8 rounded-full flex items-center justify-center",
                  isComplete && "bg-success text-success-foreground",
                  isCurrent && "bg-primary text-primary-foreground",
                  isPending && "bg-muted text-muted-foreground"
                )}
              >
                {isComplete ? (
                  <CheckCircle className="h-4 w-4" />
                ) : isCurrent ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Icon className="h-4 w-4" />
                )}
              </div>
              <span
                className={cn(
                  "text-sm font-medium",
                  isComplete && "text-success",
                  isCurrent && "text-primary",
                  isPending && "text-muted-foreground"
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
