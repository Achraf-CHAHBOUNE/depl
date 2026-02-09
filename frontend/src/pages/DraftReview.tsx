import { useState, useEffect, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { draftAPI } from "@/lib/api";
import { DraftData, LegalResult } from "@/types";
import { calculatePenalty, PenaltyCalculationResult } from "@/lib/penaltyCalculator";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { AlertsPanel } from "@/components/AlertsPanel";
import { ComputedLegalPanel } from "@/components/ComputedLegalPanel";
import { PenaltyBreakdown } from "@/components/PenaltyBreakdown";
import { FieldStatusIndicator, FieldWrapper, FieldStatus } from "@/components/FieldStatusIndicator";
import { ValidationDialog } from "@/components/ValidationDialog";
import { DraftReviewSkeleton } from "@/components/LoadingSkeletons";
import { useToast } from "@/hooks/use-toast";
import { 
  Save, 
  Building2, 
  FileText, 
  CreditCard,
  AlertTriangle,
  ArrowLeft,
  ExternalLink,
  Clock,
  Calendar,
  BookOpen,
  Upload,
  Loader2
} from "lucide-react";
import { format } from "date-fns";
import { fr } from "date-fns/locale";

/** Field labels for French display */
const FIELD_LABELS: Record<string, string> = {
  supplier_name: 'Nom fournisseur',
  supplier_ice: 'ICE',
  supplier_rc: 'N° RC',
  supplier_address: 'Adresse',
  invoice_number: 'N° facture',
  invoice_issue_date: 'Date émission',
  invoice_delivery_date: 'Date livraison',
  invoice_amount_ttc: 'Montant TTC',
  nature_of_goods: 'Nature marchandises',
  payment_mode: 'Mode paiement',
  payment_date: 'Date paiement',
  payment_amount_paid: 'Montant payé',
  payment_reference: 'Référence paiement',
  contractual_delay_days: 'Délai contractuel',
  sector_delay_days: 'Délai sectoriel',
  agreed_payment_date: 'Date paiement convenue',
  is_periodic_transaction: 'Opération périodique',
  transaction_month: 'Mois transaction',
  transaction_year: 'Année transaction',
  service_completion_date: 'Date service fait',
  is_disputed: 'Facture contestée',
  litigation_amount: 'Montant litige',
  judicial_recourse_date: 'Date recours judiciaire',
  judgment_date: 'Date jugement',
  penalty_suspension_months: 'Mois suspension'
};

/** Required fields for DGI compliance */
const REQUIRED_FIELDS = [
  'supplier_name',
  'invoice_number',
  'invoice_issue_date',
  'invoice_delivery_date',
  'invoice_amount_ttc',
  'nature_of_goods',
  'payment_mode',
];

export default function DraftReview() {
  const { id: draftId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { toast } = useToast();
  const queryClient = useQueryClient();

  // Helper function to format amounts
  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('fr-MA', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const [formData, setFormData] = useState<Partial<DraftData>>({});
  const [hasChanges, setHasChanges] = useState(false);
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({});
  const [showPaymentUpload, setShowPaymentUpload] = useState(false);
  const [paymentFile, setPaymentFile] = useState<File | null>(null);
  const [isUploadingPayment, setIsUploadingPayment] = useState(false);
  const [localCalculation, setLocalCalculation] = useState<PenaltyCalculationResult | null>(null);

  // Load draft data
  const { data: draft, isLoading, error } = useQuery({
    queryKey: ["draft", draftId],
    queryFn: () => draftAPI.get(draftId!),
    enabled: !!draftId,
    refetchOnWindowFocus: false, // Prevent auto-refetch when window regains focus
    refetchInterval: false, // Disable automatic refetching
  });

  // Update form data from draft ONLY when there are no unsaved changes
  // This prevents background refetches from overwriting user's typing
  useEffect(() => {
    if (draft?.data && !hasChanges) {
      console.log('📥 Loading draft data into form (no unsaved changes)');
      setFormData(draft.data);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draft]); // Only depend on draft, not hasChanges

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: (updates: Partial<DraftData>) => draftAPI.update(draftId!, updates),
    onSuccess: async () => {
      // Check if payment amounts were updated - if so, trigger reprocessing
      const paymentFieldsUpdated = 
        formData.payment_amount_paid !== draft?.data.payment_amount_paid ||
        formData.payment_date !== draft?.data.payment_date ||
        formData.invoice_amount_ttc !== draft?.data.invoice_amount_ttc;
      
      if (paymentFieldsUpdated) {
        console.log('💰 Payment fields updated, triggering reprocessing to recalculate penalties...');
        try {
          // Trigger reprocessing to recalculate penalties
          await draftAPI.reprocess(draftId!);
          console.log('✅ Reprocessing complete');
        } catch (error) {
          console.error('⚠️ Reprocessing failed:', error);
        }
      }
      
      // Invalidate and refetch to get updated data from database
      await queryClient.invalidateQueries({ queryKey: ["draft", draftId] });
      
      // Force refetch to get fresh data
      const freshData = await queryClient.fetchQuery({
        queryKey: ["draft", draftId],
        queryFn: () => draftAPI.get(draftId!),
      });
      
      // Update form with fresh data from database
      if (freshData?.data) {
        setFormData(freshData.data);
      }
      
      setHasChanges(false);
      
      toast({
        title: "Modifications enregistrées",
        description: "Le brouillon a été mis à jour avec succès.",
      });
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur",
        description: error.message || "Impossible d'enregistrer les modifications",
        variant: "destructive",
      });
    },
  });

  // Validate mutation
  const validateMutation = useMutation({
    mutationFn: () => draftAPI.validate(draftId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      toast({
        title: "Brouillon validé",
        description: "Le brouillon a été validé et ajouté au registre.",
      });
      navigate("/drafts");
    },
    onError: (error: Error) => {
      toast({
        title: "Erreur de validation",
        description: error.message || "Impossible de valider le brouillon",
        variant: "destructive",
      });
    },
  });

  // Calculate penalties locally (instant, no API call)
  const calculatePenaltiesLocally = useCallback((data: Partial<DraftData>) => {
    console.log('🧮 Calculating penalties locally (instant)');
    
    const result = calculatePenalty({
      invoice_delivery_date: data.invoice_delivery_date,
      invoice_amount_ttc: data.invoice_amount_ttc,
      payment_date: data.payment_date,
      payment_amount_paid: data.payment_amount_paid,
      contractual_delay_days: data.contractual_delay_days,
      service_completion_date: data.service_completion_date,
      is_disputed: data.is_disputed,
    });
    
    setLocalCalculation(result);
    
    // Update formData with calculated values for display
    setFormData(prev => ({
      ...prev,
      legal_due_date: result.legal_due_date,
      applied_legal_delay_days: result.applied_legal_delay_days,
      days_overdue: result.days_overdue,
      months_of_delay: result.months_of_delay,
      penalty_rate: result.penalty_rate,
      penalty_amount: result.penalty_amount,
      payment_amount_unpaid: result.unpaid_amount,
      penalty_suspended: result.penalty_suspended,
      calculation_breakdown: result.calculation_breakdown,
    }));
    
    console.log('✅ Local calculation complete:', {
      days_overdue: result.days_overdue,
      months: result.months_of_delay,
      rate: result.penalty_rate,
      amount: result.penalty_amount
    });
  }, []);

  const updateField = useCallback((field: keyof DraftData, value: unknown) => {
    setFormData(prev => {
      const updated = { ...prev, [field]: value };
      
      // Auto-calculate payment_amount_unpaid when payment_amount_paid changes
      if (field === 'payment_amount_paid') {
        const paid = typeof value === 'number' ? value : (typeof value === 'string' ? parseFloat(value) : 0);
        const total = prev.invoice_amount_ttc || 0;
        updated.payment_amount_unpaid = Math.max(0, total - paid);
        
        console.log('💰 Auto-calculated unpaid:', {
          total,
          paid,
          unpaid: updated.payment_amount_unpaid
        });
      }
      
      // Recalculate unpaid if invoice total changes
      if (field === 'invoice_amount_ttc') {
        const total = typeof value === 'number' ? value : (typeof value === 'string' ? parseFloat(value) : 0);
        const paid = prev.payment_amount_paid || 0;
        updated.payment_amount_unpaid = Math.max(0, total - paid);
        
        console.log('💰 Auto-calculated unpaid (total changed):', {
          total,
          paid,
          unpaid: updated.payment_amount_unpaid
        });
      }
      
      return updated;
    });
    setHasChanges(true);
    
    // Clear validation error for this field
    if (validationErrors[field]) {
      setValidationErrors(prev => {
        const updated = { ...prev };
        delete updated[field];
        return updated;
      });
    }
  }, [validationErrors]);

  // Auto-calculate penalties when critical fields change (instant, no debounce needed)
  useEffect(() => {
    if (formData.invoice_delivery_date && formData.invoice_amount_ttc) {
      calculatePenaltiesLocally(formData);
    }
  }, [
    formData.invoice_delivery_date,
    formData.invoice_amount_ttc,
    formData.payment_date,
    formData.payment_amount_paid,
    formData.contractual_delay_days,
    formData.service_completion_date,
    formData.is_disputed,
    calculatePenaltiesLocally,
  ]);

  const handleSave = useCallback(() => {
    console.log('💾 handleSave called - Current formData:', formData);
    console.log('   supplier_name in formData:', formData.supplier_name);
    
    // Guard 1: Prevent updates on validated/exported drafts
    if (draft?.status === 'VALIDATED') {
      toast({
        title: "Modification impossible",
        description: "Ce brouillon est validé et ne peut plus être modifié.",
        variant: "destructive",
      });
      return;
    }
    
    // Guard 2: Check if there are actual changes
    if (!hasChanges) {
      toast({
        title: "Aucune modification",
        description: "Aucune modification à enregistrer.",
      });
      return;
    }
    
    // Sanitize payload - send only editable fields, exclude computed/immutable fields
    const sanitizedPayload: Partial<DraftData> = {
      // Supplier info (editable)
      supplier_name: formData.supplier_name,
      supplier_ice: formData.supplier_ice,
      supplier_rc: formData.supplier_rc,
      supplier_address: formData.supplier_address,
      
      // Invoice info (editable)
      invoice_number: formData.invoice_number,
      invoice_issue_date: formData.invoice_issue_date,
      invoice_delivery_date: formData.invoice_delivery_date,
      invoice_amount_ttc: formData.invoice_amount_ttc,
      nature_of_goods: formData.nature_of_goods,
      
      // Payment info (editable)
      payment_date: formData.payment_date,
      payment_amount_paid: formData.payment_amount_paid,
      payment_amount_unpaid: formData.payment_amount_unpaid,
      payment_reference: formData.payment_reference,
      payment_mode: formData.payment_mode,
      
      // Delay configuration (editable)
      contractual_delay_days: formData.contractual_delay_days,
      sector_delay_days: formData.sector_delay_days,
      agreed_payment_date: formData.agreed_payment_date,
      
      // Periodic transactions (editable)
      is_periodic_transaction: formData.is_periodic_transaction,
      transaction_month: formData.transaction_month,
      transaction_year: formData.transaction_year,
      
      // Public establishment (editable)
      service_completion_date: formData.service_completion_date,
      
      // Litigation (editable)
      is_disputed: formData.is_disputed,
      litigation_amount: formData.litigation_amount,
      judicial_recourse_date: formData.judicial_recourse_date,
      judgment_date: formData.judgment_date,
      penalty_suspension_months: formData.penalty_suspension_months,
      
      // Field tracking (preserve)
      missing_fields: formData.missing_fields || [],
      uncertain_fields: formData.uncertain_fields || [],
    };
    
    // Remove undefined values to avoid sending null/undefined fields
    Object.keys(sanitizedPayload).forEach(key => {
      if (sanitizedPayload[key as keyof DraftData] === undefined) {
        delete sanitizedPayload[key as keyof DraftData];
      }
    });
    
    saveMutation.mutate(sanitizedPayload);
  }, [formData, draft, hasChanges, toast, saveMutation]);

  // Keyboard shortcut for save (Ctrl+S)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        handleSave();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleSave]);

  // Real-time validation check
  useEffect(() => {
    const errors: Record<string, string> = {};
    
    REQUIRED_FIELDS.forEach(field => {
      const value = formData[field as keyof DraftData];
      if (value === undefined || value === null || value === '') {
        errors[field] = `${FIELD_LABELS[field] || field} est obligatoire`;
      }
    });
    
    setValidationErrors(errors);
  }, [formData]);

  const validateRequiredFields = (): boolean => {
    const errors: Record<string, string> = {};
    
    REQUIRED_FIELDS.forEach(field => {
      const value = formData[field as keyof DraftData];
      if (value === undefined || value === null || value === '') {
        errors[field] = `${FIELD_LABELS[field] || field} est obligatoire`;
      }
    });
    
    setValidationErrors(errors);
    
    if (Object.keys(errors).length > 0) {
      toast({
        title: "Champs obligatoires manquants",
        description: `Veuillez remplir: ${Object.keys(errors).map(f => FIELD_LABELS[f] || f).join(', ')}`,
        variant: "destructive",
      });
      return false;
    }
    
    return true;
  };

  const handleValidateClick = () => {
    if (hasChanges) {
      toast({
        title: "Modifications non enregistrées",
        description: "Veuillez enregistrer vos modifications avant de valider.",
        variant: "destructive",
      });
      return;
    }
    
    if (!validateRequiredFields()) {
      return;
    }
  };

  const handleConfirmValidation = () => {
    validateMutation.mutate();
  };

  const getFieldStatus = (field: string): FieldStatus => {
    if (validationErrors[field]) return "missing";
    if (draft?.data?.missing_fields?.includes(field)) return "missing";
    if (draft?.data?.uncertain_fields?.includes(field)) return "uncertain";
    return "ok";
  };

  if (isLoading) {
    return <DraftReviewSkeleton />;
  }

  if (error || !draft) {
    return (
      <div className="text-center py-12">
        <AlertTriangle className="h-12 w-12 mx-auto text-destructive mb-4" />
        <p className="text-destructive font-medium">Brouillon non trouvé</p>
        <p className="text-sm text-muted-foreground mt-2">
          {error instanceof Error ? error.message : "Une erreur est survenue"}
        </p>
        <Button variant="outline" className="mt-4" onClick={() => navigate("/drafts")}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Retour à la liste
        </Button>
      </div>
    );
  }

  const isValidated = draft.status === 'VALIDATED';

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/drafts")}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-foreground">
                Révision du Brouillon
              </h1>
              <Badge variant={isValidated ? "default" : "secondary"}>
                {isValidated ? "Validé" : "Brouillon"}
              </Badge>
            </div>
            <p className="text-muted-foreground">
              {draft.company_name} • Créé le {format(new Date(draft.created_at), 'dd MMM yyyy', { locale: fr })}
            </p>
          </div>
        </div>
        
        {!isValidated && (
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              onClick={handleSave}
              disabled={!hasChanges || saveMutation.isPending}
            >
              <Save className="h-4 w-4 mr-2" />
              {saveMutation.isPending ? "Enregistrement..." : "Enregistrer"}
            </Button>
            
            {(!formData.payment_date || !formData.payment_amount_paid) && (
              <Button
                variant="outline"
                onClick={() => setShowPaymentUpload(true)}
              >
                <Upload className="h-4 w-4 mr-2" />
                Ajouter Paiement
              </Button>
            )}
            
            <ValidationDialog
              formData={formData}
              onConfirm={handleConfirmValidation}
              isLoading={validateMutation.isPending}
              disabled={hasChanges}
            />
          </div>
        )}
      </div>

      {/* PDF Document Access */}
      {(draft.invoice_file_url || draft.bank_statement_file_url) && (
        <Card className="bg-muted/30">
          <CardContent className="py-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <FileText className="h-4 w-4" />
                <span className="font-medium">Documents sources :</span>
              </div>
              {draft.invoice_file_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(draft.invoice_file_url, '_blank')}
                  className="gap-2"
                >
                  <FileText className="h-4 w-4" />
                  Voir facture PDF
                  <ExternalLink className="h-3 w-3" />
                </Button>
              )}
              {draft.bank_statement_file_url && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => window.open(draft.bank_statement_file_url, '_blank')}
                  className="gap-2"
                >
                  <CreditCard className="h-4 w-4" />
                  Voir relevé bancaire PDF
                  <ExternalLink className="h-3 w-3" />
                </Button>
              )}
              <span className="text-xs text-muted-foreground ml-auto">
                {isValidated ? "Documents en lecture seule" : "Consultez les documents originaux pour vérification"}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Warning Banner for Missing Fields */}
      {(draft.data.missing_fields.length > 0 || draft.data.uncertain_fields.length > 0 || Object.keys(validationErrors).length > 0) && (
        <div className="bg-warning/10 border border-warning/30 rounded-lg p-4 flex items-start gap-3">
          <AlertTriangle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-foreground">Vérification requise</p>
            <p className="text-sm text-muted-foreground">
              Certains champs sont manquants ou incertains. Veuillez les compléter ou vérifier avant de valider.
            </p>
            {Object.keys(validationErrors).length > 0 && (
              <p className="text-sm text-destructive mt-1">
                Champs obligatoires: {Object.keys(validationErrors).map(f => FIELD_LABELS[f] || f).join(', ')}
              </p>
            )}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main Form - 2 columns */}
        <div className="lg:col-span-2 space-y-6">
          {/* Supplier Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-primary" />
                Fournisseur
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="md:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Raison Sociale <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('supplier_name')} 
                    fieldName="Raison Sociale" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('supplier_name')}>
                  <Input
                    value={formData.supplier_name || ''}
                    onChange={(e) => updateField('supplier_name', e.target.value)}
                    disabled={isValidated}
                    placeholder="Nom du fournisseur"
                  />
                </FieldWrapper>
                {validationErrors.supplier_name && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.supplier_name}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    ICE <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('supplier_ice')} 
                    fieldName="ICE" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('supplier_ice')}>
                  <Input
                    value={formData.supplier_ice || ''}
                    onChange={(e) => updateField('supplier_ice', e.target.value)}
                    disabled={isValidated}
                    placeholder="15 chiffres"
                  />
                </FieldWrapper>
                {validationErrors.supplier_ice && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.supplier_ice}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>N° RC</Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('supplier_rc')} 
                    fieldName="N° RC" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('supplier_rc')}>
                  <Input
                    value={formData.supplier_rc || ''}
                    onChange={(e) => updateField('supplier_rc', e.target.value)}
                    disabled={isValidated}
                    placeholder="Numéro RC"
                  />
                </FieldWrapper>
              </div>
              
              <div className="md:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <Label>Adresse</Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('supplier_address')} 
                    fieldName="Adresse" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('supplier_address')}>
                  <Input
                    value={formData.supplier_address || ''}
                    onChange={(e) => updateField('supplier_address', e.target.value)}
                    disabled={isValidated}
                    placeholder="Adresse complète"
                  />
                </FieldWrapper>
              </div>
            </CardContent>
          </Card>

          {/* Invoice Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-info" />
                Facture
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Numéro de Facture <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('invoice_number')} 
                    fieldName="Numéro de Facture" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('invoice_number')}>
                  <Input
                    value={formData.invoice_number || ''}
                    onChange={(e) => updateField('invoice_number', e.target.value)}
                    disabled={isValidated}
                    placeholder="FAC-XXXX"
                  />
                </FieldWrapper>
                {validationErrors.invoice_number && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.invoice_number}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Montant TTC <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('invoice_amount_ttc')} 
                    fieldName="Montant TTC" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('invoice_amount_ttc')}>
                  <Input
                    type="number"
                    value={formData.invoice_amount_ttc || ''}
                    onChange={(e) => updateField('invoice_amount_ttc', parseFloat(e.target.value) || 0)}
                    disabled={isValidated}
                    placeholder="0.00 MAD"
                  />
                </FieldWrapper>
                {validationErrors.invoice_amount_ttc && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.invoice_amount_ttc}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Date d'émission <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('invoice_issue_date')} 
                    fieldName="Date d'émission" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('invoice_issue_date')}>
                  <Input
                    type="date"
                    value={formData.invoice_issue_date || ''}
                    onChange={(e) => updateField('invoice_issue_date', e.target.value)}
                    disabled={isValidated}
                  />
                </FieldWrapper>
                {validationErrors.invoice_issue_date && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.invoice_issue_date}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Date de Livraison <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('invoice_delivery_date')} 
                    fieldName="Date de Livraison" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('invoice_delivery_date')}>
                  <Input
                    type="date"
                    value={formData.invoice_delivery_date || ''}
                    onChange={(e) => updateField('invoice_delivery_date', e.target.value)}
                    disabled={isValidated}
                  />
                </FieldWrapper>
                {validationErrors.invoice_delivery_date && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.invoice_delivery_date}</p>
                )}
              </div>
              
              <div className="md:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Nature des Marchandises/Travaux/Services <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('nature_of_goods')} 
                    fieldName="Nature des Marchandises" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('nature_of_goods')}>
                  <Input
                    value={formData.nature_of_goods || ''}
                    onChange={(e) => updateField('nature_of_goods', e.target.value)}
                    disabled={isValidated}
                    placeholder="Décrivez la nature des marchandises, travaux ou services"
                  />
                </FieldWrapper>
                {validationErrors.nature_of_goods && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.nature_of_goods}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Payment Section */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-success" />
                Paiement
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>Date de Paiement</Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('payment_date')} 
                    fieldName="Date de Paiement" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('payment_date')}>
                  <Input
                    type="date"
                    value={formData.payment_date || ''}
                    onChange={(e) => updateField('payment_date', e.target.value)}
                    disabled={isValidated}
                  />
                </FieldWrapper>
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Mode de Paiement <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('payment_mode')} 
                    fieldName="Mode de Paiement" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('payment_mode')}>
                  <select
                    value={formData.payment_mode || ''}
                    onChange={(e) => updateField('payment_mode', e.target.value)}
                    disabled={isValidated}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="">Sélectionnez...</option>
                    <option value="virement">Virement bancaire</option>
                    <option value="cheque">Chèque</option>
                    <option value="especes">Espèces</option>
                    <option value="effet">Effet de commerce</option>
                    <option value="compensation">Compensation</option>
                  </select>
                </FieldWrapper>
                {validationErrors.payment_mode && (
                  <p className="text-xs text-destructive mt-1">{validationErrors.payment_mode}</p>
                )}
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label className="flex items-center gap-1">
                    Montant Payé (MAD) <span className="text-destructive">*</span>
                  </Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('payment_amount_paid')} 
                    fieldName="Montant Payé" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('payment_amount_paid')}>
                  <Input
                    type="number"
                    value={formData.payment_amount_paid || ''}
                    onChange={(e) => updateField('payment_amount_paid', parseFloat(e.target.value) || 0)}
                    disabled={isValidated}
                    placeholder="0.00"
                  />
                </FieldWrapper>
              </div>
              
              <div>
                <div className="flex items-center justify-between mb-1">
                  <Label>Montant Non Payé (MAD)</Label>
                  <span className="text-xs text-muted-foreground">
                    Auto-calculé
                  </span>
                </div>
                <Input
                  type="number"
                  value={formData.payment_amount_unpaid?.toFixed(2) || '0.00'}
                  disabled
                  className="bg-muted font-mono"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  = {formatAmount(formData.invoice_amount_ttc || 0)} - {formatAmount(formData.payment_amount_paid || 0)}
                </p>
              </div>
              
              <div className="md:col-span-2">
                <div className="flex items-center justify-between mb-1">
                  <Label>Référence</Label>
                  <FieldStatusIndicator 
                    status={getFieldStatus('payment_reference')} 
                    fieldName="Référence paiement" 
                  />
                </div>
                <FieldWrapper status={getFieldStatus('payment_reference')}>
                  <Input
                    value={formData.payment_reference || ''}
                    onChange={(e) => updateField('payment_reference', e.target.value)}
                    disabled={isValidated}
                    placeholder="VIR-XXXX"
                  />
                </FieldWrapper>
              </div>
            </CardContent>
          </Card>

          {/* Delay Configuration Section - NEW */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clock className="h-5 w-5 text-warning" />
                Configuration des Délais
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Délais contractuels ou sectoriels (optionnel)
              </p>
            </CardHeader>
            <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label>Délai Contractuel (jours)</Label>
                <Input
                  type="number"
                  value={formData.contractual_delay_days || ''}
                  onChange={(e) => updateField('contractual_delay_days', parseInt(e.target.value) || 0)}
                  disabled={isValidated}
                  placeholder="Ex: 90 jours"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Maximum 120 jours selon DGI
                </p>
              </div>
              
              <div>
                <Label>Délai Sectoriel (jours)</Label>
                <Input
                  type="number"
                  value={formData.sector_delay_days || ''}
                  onChange={(e) => updateField('sector_delay_days', parseInt(e.target.value) || 0)}
                  disabled={isValidated}
                  placeholder="Délai spécifique au secteur"
                />
              </div>
              
              <div className="md:col-span-2">
                <Label>Date de Paiement Convenue</Label>
                <Input
                  type="date"
                  value={formData.agreed_payment_date || ''}
                  onChange={(e) => updateField('agreed_payment_date', e.target.value)}
                  disabled={isValidated}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Si différente de la date d'échéance légale
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Periodic Transactions Section - NEW */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-info" />
                Opérations Périodiques
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Pour les transactions récurrentes mensuelles
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_periodic"
                  checked={formData.is_periodic_transaction || false}
                  onChange={(e) => updateField('is_periodic_transaction', e.target.checked)}
                  disabled={isValidated}
                  className="h-4 w-4"
                />
                <Label htmlFor="is_periodic" className="cursor-pointer">
                  Cette facture fait partie d'une opération périodique
                </Label>
              </div>
              
              {formData.is_periodic_transaction && (
                <div className="grid grid-cols-2 gap-4 pt-2 border-t">
                  <div>
                    <Label>Mois</Label>
                    <select
                      value={formData.transaction_month || ''}
                      onChange={(e) => updateField('transaction_month', parseInt(e.target.value))}
                      disabled={isValidated}
                      className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                    >
                      <option value="">Sélectionnez...</option>
                      {[...Array(12)].map((_, i) => (
                        <option key={i + 1} value={i + 1}>
                          {new Date(2024, i).toLocaleDateString('fr-FR', { month: 'long' })}
                        </option>
                      ))}
                    </select>
                  </div>
                  
                  <div>
                    <Label>Année</Label>
                    <Input
                      type="number"
                      value={formData.transaction_year || ''}
                      onChange={(e) => updateField('transaction_year', parseInt(e.target.value))}
                      disabled={isValidated}
                      placeholder="2024"
                      min="2020"
                      max="2030"
                    />
                  </div>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Public Establishment Section - NEW */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Building2 className="h-5 w-5 text-primary" />
                Établissements Publics
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Pour les factures aux établissements publics uniquement
              </p>
            </CardHeader>
            <CardContent>
              <div>
                <Label>Date de Service Fait</Label>
                <Input
                  type="date"
                  value={formData.service_completion_date || ''}
                  onChange={(e) => updateField('service_completion_date', e.target.value)}
                  disabled={isValidated}
                />
                <p className="text-xs text-muted-foreground mt-1">
                  Date de réalisation du service pour établissements publics
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Litigation Section - NEW */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-destructive" />
                Contentieux et Litiges
              </CardTitle>
              <p className="text-sm text-muted-foreground">
                Gestion des factures contestées et procédures judiciaires
              </p>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="is_disputed"
                  checked={formData.is_disputed || false}
                  onChange={(e) => updateField('is_disputed', e.target.checked)}
                  disabled={isValidated}
                  className="h-4 w-4"
                />
                <Label htmlFor="is_disputed" className="cursor-pointer">
                  Cette facture est contestée (litige en cours)
                </Label>
              </div>
              
              {formData.is_disputed && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2 border-t">
                  <div className="md:col-span-2">
                    <Label>Montant du Litige (MAD)</Label>
                    <Input
                      type="number"
                      value={formData.litigation_amount || ''}
                      onChange={(e) => updateField('litigation_amount', parseFloat(e.target.value) || 0)}
                      disabled={isValidated}
                      placeholder="0.00"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Montant total en contestation
                    </p>
                  </div>
                  
                  <div>
                    <Label>Date Recours Judiciaire</Label>
                    <Input
                      type="date"
                      value={formData.judicial_recourse_date || ''}
                      onChange={(e) => updateField('judicial_recourse_date', e.target.value)}
                      disabled={isValidated}
                    />
                  </div>
                  
                  <div>
                    <Label>Date du Jugement</Label>
                    <Input
                      type="date"
                      value={formData.judgment_date || ''}
                      onChange={(e) => updateField('judgment_date', e.target.value)}
                      disabled={isValidated}
                    />
                  </div>
                  
                  <div className="md:col-span-2">
                    <Label>Mois de Suspension des Pénalités</Label>
                    <Input
                      type="number"
                      value={formData.penalty_suspension_months || ''}
                      onChange={(e) => updateField('penalty_suspension_months', parseInt(e.target.value) || 0)}
                      disabled={isValidated}
                      placeholder="0"
                    />
                    <p className="text-xs text-muted-foreground mt-1">
                      Nombre de mois pendant lesquels les pénalités sont suspendues
                    </p>
                  </div>
                  
                  <div className="md:col-span-2 p-3 bg-warning/10 border border-warning/20 rounded-md">
                    <p className="text-sm text-warning flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4" />
                      Les pénalités sont automatiquement suspendues pendant la période de litige
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - 1 column */}
        <div className="space-y-6">
          {/* Legal Calculations - Always instant, no loading */}
          <ComputedLegalPanel
            legal={{
              invoice_id: draftId!,
              legal_start_date: formData.invoice_delivery_date,
              legal_due_date: localCalculation?.legal_due_date || formData.legal_due_date,
              applied_legal_delay_days: localCalculation?.applied_legal_delay_days || formData.applied_legal_delay_days || 60,
              actual_payment_date: formData.payment_date,
              days_overdue: localCalculation?.days_overdue || formData.days_overdue || 0,
              months_of_delay: localCalculation?.months_of_delay || formData.months_of_delay || 0,
              months_delay_unpaid: formData.months_delay_unpaid || 0,
              months_delay_paid: formData.months_delay_paid || 0,
              penalty_rate: localCalculation?.penalty_rate || formData.penalty_rate || 0,
              penalty_amount: localCalculation?.penalty_amount || formData.penalty_amount || 0,
              penalty_suspended: localCalculation?.penalty_suspended || formData.penalty_suspended || formData.is_disputed || false,
              legal_status: formData.legal_status || (formData.is_disputed ? 'DISPUTED' : 'NORMAL'),
              invoice_amount_ttc: formData.invoice_amount_ttc || 0,
              paid_amount: formData.payment_amount_paid || 0,
              unpaid_amount: localCalculation?.unpaid_amount || formData.payment_amount_unpaid || 0,
              alerts: draft.alerts,
              computation_notes: formData.computation_notes || [],
              calculation_breakdown: localCalculation?.calculation_breakdown || formData.calculation_breakdown || draft.data.calculation_breakdown,
              requires_manual_review: draft.data.missing_fields.length > 0,
            }}
          />

          {/* Penalty Calculation Breakdown - Always visible with local calculations */}
          {(localCalculation?.calculation_breakdown || formData.calculation_breakdown || draft.data.calculation_breakdown) && (
            <PenaltyBreakdown
              breakdown={localCalculation?.calculation_breakdown || formData.calculation_breakdown || draft.data.calculation_breakdown}
              penaltyAmount={localCalculation?.penalty_amount || formData.penalty_amount || 0}
              penaltySuspended={localCalculation?.penalty_suspended || formData.penalty_suspended || formData.is_disputed || false}
            />
          )}

          {/* Alerts */}
          {draft.alerts.length > 0 && (
            <AlertsPanel alerts={draft.alerts} />
          )}
        </div>
      </div>

      {/* Payment Upload Dialog */}
      {showPaymentUpload && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Ajouter le Paiement
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!isUploadingPayment ? (
                <>
                  <div>
                    <Label>Relevé Bancaire (PDF)</Label>
                    <Input
                      type="file"
                      accept=".pdf"
                      onChange={(e) => setPaymentFile(e.target.files?.[0] || null)}
                    />
                    {paymentFile && (
                      <p className="text-sm text-success mt-2">✓ {paymentFile.name}</p>
                    )}
                  </div>

                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="outline"
                      onClick={() => {
                        setShowPaymentUpload(false);
                        setPaymentFile(null);
                      }}
                    >
                      Annuler
                    </Button>
                    <Button
                      onClick={async () => {
                        if (!paymentFile) {
                          toast({
                            title: "Fichier manquant",
                            description: "Veuillez sélectionner un fichier PDF",
                            variant: "destructive",
                          });
                          return;
                        }

                        setIsUploadingPayment(true);
                        try {
                          // completeWithPayment handles upload, processing, and polling until completion
                          await draftAPI.completeWithPayment(draftId!, paymentFile);
                          
                          // CRITICAL: Poll until payment data is actually available
                          // (workflow complete != data committed to queryable storage)
                          let attempts = 0;
                          const maxAttempts = 10;
                          let freshData = null;
                          
                          while (attempts < maxAttempts) {
                            await new Promise(resolve => setTimeout(resolve, 500));
                            
                            // Invalidate and fetch fresh
                            await queryClient.invalidateQueries({ queryKey: ["draft", draftId] });
                            freshData = await draftAPI.get(draftId!);
                            
                            // Check if payment data is now available
                            const hasPayment = freshData?.data?.payment_amount_paid > 0 || freshData?.data?.payment_date;
                            
                            if (hasPayment) {
                              console.log("✅ Payment data found after", attempts + 1, "attempts");
                              break;
                            }
                            
                            console.log(`⏳ Waiting for payment data... (${attempts + 1}/${maxAttempts})`);
                            attempts++;
                          }
                          
                          // Update form with whatever we got (even if still 0 after max attempts)
                          setHasChanges(false);
                          if (freshData?.data) {
                            setFormData({ ...freshData.data });
                            console.log("💾 Form data updated:", freshData.data);
                          }
                          
                          // Update React Query cache
                          queryClient.setQueryData(["draft", draftId], freshData);
                          
                          toast({
                            title: "Paiement ajouté",
                            description: "Le relevé bancaire a été traité avec succès",
                          });
                          
                          // Wait for backend to commit, then refresh
                          await new Promise(resolve => setTimeout(resolve, 3000));
                          window.location.reload();
                          
                          setShowPaymentUpload(false);
                          setPaymentFile(null);
                        } catch (error: any) {
                          toast({
                            title: "Erreur",
                            description: error.message || "Impossible d'ajouter le paiement",
                            variant: "destructive",
                          });
                        } finally {
                          setIsUploadingPayment(false);
                        }
                      }}
                      disabled={!paymentFile}
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      Scanner et Traiter
                    </Button>
                  </div>
                </>
              ) : (
                <div className="py-8 text-center space-y-4">
                  <Loader2 className="h-12 w-12 animate-spin mx-auto text-primary" />
                  <div>
                    <p className="font-medium">Traitement en cours...</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Extraction et analyse du paiement
                    </p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
