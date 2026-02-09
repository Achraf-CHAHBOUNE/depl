import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { CheckCircle, AlertTriangle, Loader2 } from "lucide-react";
import { DraftData } from "@/types";

interface ValidationDialogProps {
  formData: Partial<DraftData>;
  onConfirm: () => void;
  isLoading?: boolean;
  disabled?: boolean;
  children?: React.ReactNode;
}

/**
 * Confirmation dialog before validating a draft
 */
export function ValidationDialog({
  formData,
  onConfirm,
  isLoading = false,
  disabled = false,
  children,
}: ValidationDialogProps) {
  // Check for potential issues
  const hasUnpaidAmount = (formData.payment_amount_unpaid || 0) > 0;
  const hasPenalty = (formData.penalty_amount || 0) > 0;
  
  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>
        {children || (
          <Button disabled={disabled || isLoading}>
            {isLoading ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <CheckCircle className="h-4 w-4 mr-2" />
            )}
            Valider le Brouillon
          </Button>
        )}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-primary" />
            Confirmer la validation
          </AlertDialogTitle>
          <AlertDialogDescription asChild>
            <div className="space-y-4">
              <p>
                Êtes-vous sûr de vouloir valider ce brouillon ? Une fois validé, 
                il sera ajouté au registre DGI et ne pourra plus être modifié.
              </p>
              
              {/* Summary */}
              <div className="bg-muted rounded-lg p-3 text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Fournisseur:</span>
                  <span className="font-medium text-foreground">
                    {formData.supplier_name || "Non renseigné"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">N° Facture:</span>
                  <span className="font-medium text-foreground">
                    {formData.invoice_number || "Non renseigné"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Montant TTC:</span>
                  <span className="font-medium text-foreground">
                    {formData.invoice_amount_ttc?.toLocaleString("fr-MA") || 0} MAD
                  </span>
                </div>
              </div>
              
              {/* Warnings */}
              {(hasUnpaidAmount || hasPenalty) && (
                <div className="bg-warning/10 border border-warning/30 rounded-lg p-3 flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-warning flex-shrink-0 mt-0.5" />
                  <div className="text-sm">
                    <p className="font-medium text-foreground">Attention</p>
                    <ul className="list-disc list-inside text-muted-foreground">
                      {hasUnpaidAmount && (
                        <li>
                          Montant non payé: {formData.payment_amount_unpaid?.toLocaleString("fr-MA")} MAD
                        </li>
                      )}
                      {hasPenalty && (
                        <li>
                          Pénalité calculée: {formData.penalty_amount?.toLocaleString("fr-MA")} MAD
                        </li>
                      )}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Annuler</AlertDialogCancel>
          <AlertDialogAction onClick={onConfirm} disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Validation...
              </>
            ) : (
              <>
                <CheckCircle className="h-4 w-4 mr-2" />
                Confirmer la validation
              </>
            )}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
