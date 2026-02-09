import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const statusBadgeVariants = cva(
  "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        // Document statuses
        uploaded: "bg-secondary text-secondary-foreground",
        ocr_done: "bg-info/10 text-info",
        extraction_done: "bg-info/20 text-info",
        matched: "bg-success/10 text-success",
        rules_computed: "bg-success/20 text-success",
        needs_review: "bg-warning/10 text-warning",
        validated: "bg-success text-success-foreground",
        invalidated: "bg-destructive/10 text-destructive",
        
        // Draft statuses
        draft: "bg-muted text-muted-foreground",
        ready_to_validate: "bg-info text-info-foreground",
        
        // Payment statuses
        paid: "bg-success text-success-foreground",
        partial: "bg-warning text-warning-foreground",
        unpaid: "bg-destructive/10 text-destructive",
        
        // Legal statuses
        normal: "bg-secondary text-secondary-foreground",
        disputed: "bg-warning/10 text-warning",
        credit_note: "bg-info/10 text-info",
        procedure_690: "bg-destructive/10 text-destructive",
        
        // Declaration statuses
        finalized: "bg-success text-success-foreground",
      },
    },
    defaultVariants: {
      variant: "uploaded",
    },
  }
);

export interface StatusBadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof statusBadgeVariants> {
  status: string;
}

const statusLabels: Record<string, string> = {
  UPLOADED: 'Téléversé',
  OCR_DONE: 'OCR Terminé',
  EXTRACTION_DONE: 'Extrait',
  MATCHED: 'Rapproché',
  RULES_COMPUTED: 'Calculé',
  NEEDS_REVIEW: 'À Réviser',
  VALIDATED: 'Validé',
  INVALIDATED: 'Invalidé',
  DRAFT: 'Brouillon',
  READY_TO_VALIDATE: 'Prêt',
  PAID: 'Payé',
  PARTIAL: 'Partiel',
  UNPAID: 'Impayé',
  NORMAL: 'Normal',
  DISPUTED: 'Litige',
  CREDIT_NOTE: 'Avoir',
  PROCEDURE_690: 'Procédure 690',
  FINALIZED: 'Finalisé',
};

export function StatusBadge({ status, className, ...props }: StatusBadgeProps) {
  const variantKey = status.toLowerCase().replace(/_/g, '_') as any;
  const label = statusLabels[status] || status;
  
  return (
    <span
      className={cn(statusBadgeVariants({ variant: variantKey }), className)}
      {...props}
    >
      {label}
    </span>
  );
}
