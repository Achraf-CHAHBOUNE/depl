import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { draftAPI, settingsAPI } from "@/lib/api";
import { FileDropzone } from "@/components/FileDropzone";
import { OCRProgressIndicator } from "@/components/OCRProgressIndicator";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import { Loader2, FileText, Building2, ArrowRight, AlertCircle, RefreshCw } from "lucide-react";

export default function DraftCreate() {
  const navigate = useNavigate();
  const { toast } = useToast();
  
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [bankStatementFile, setBankStatementFile] = useState<File | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);

  // Load company settings
  const { data: companySettings, isLoading: loadingSettings, error: settingsError, refetch: refetchSettings } = useQuery({
    queryKey: ["company-settings"],
    queryFn: settingsAPI.getCompany,
  });

  const createMutation = useMutation({
    mutationFn: draftAPI.create,
    onMutate: () => {
      setIsProcessing(true);
      setProcessingError(null);
    },
    onSuccess: (draft) => {
      toast({
        title: "Brouillon créé",
        description: "Le traitement OCR est terminé. Vous pouvez maintenant vérifier les données.",
      });
      navigate(`/drafts/${draft.id}/review`);
    },
    onError: (error: Error) => {
      setIsProcessing(false);
      setProcessingError(error.message || "Impossible de créer le brouillon");
      toast({
        title: "Erreur",
        description: error.message || "Impossible de créer le brouillon",
        variant: "destructive",
      });
    },
  });

  const handleInvoiceFiles = (files: File[]) => {
    setInvoiceFile(files[0] || null);
    setProcessingError(null);
  };

  const handleBankStatementFiles = (files: File[]) => {
    setBankStatementFile(files[0] || null);
    setProcessingError(null);
  };

  const handleSubmit = () => {
    if (!invoiceFile) {
      toast({
        title: "Fichier manquant",
        description: "Veuillez sélectionner au moins une facture",
        variant: "destructive",
      });
      return;
    }

    if (!companySettings) {
      toast({
        title: "Paramètres manquants",
        description: "Les paramètres de l'entreprise ne sont pas configurés",
        variant: "destructive",
      });
      return;
    }

    createMutation.mutate({
      invoice_file: invoiceFile,
      payment_file: bankStatementFile, // Optional - can be null
      company_name: companySettings.name,
      company_ice: companySettings.ice,
      company_rc: companySettings.rc,
    });
  };

  const handleRetry = () => {
    setProcessingError(null);
    handleSubmit();
  };

  const canSubmit = invoiceFile && companySettings && !createMutation.isPending && !isProcessing;

  // Show processing state
  if (isProcessing || createMutation.isPending) {
    return (
      <div className="space-y-6 animate-fade-in max-w-2xl mx-auto">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Nouveau Brouillon</h1>
          <p className="text-muted-foreground">
            Traitement de vos documents en cours...
          </p>
        </div>

        <OCRProgressIndicator 
          isProcessing={true} 
          error={processingError}
          hasPaymentFile={!!bankStatementFile}
        />

        {processingError && (
          <div className="flex justify-center gap-3">
            <Button variant="outline" onClick={() => navigate("/drafts")}>
              Annuler
            </Button>
            <Button onClick={handleRetry}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Réessayer
            </Button>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in max-w-5xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Nouveau Brouillon</h1>
        <p className="text-muted-foreground">
          Téléchargez une facture fournisseur et le relevé bancaire correspondant
        </p>
      </div>

      {/* File Upload Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Invoice Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5 text-primary" />
              Facture Fournisseur
            </CardTitle>
            <CardDescription>
              Téléchargez le PDF de la facture fournisseur
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileDropzone
              onFilesSelected={handleInvoiceFiles}
              accept={{ 'application/pdf': ['.pdf'] }}
              maxFiles={1}
              disabled={createMutation.isPending}
            />
            {invoiceFile && (
              <p className="mt-2 text-sm text-success">
                ✓ {invoiceFile.name}
              </p>
            )}
          </CardContent>
        </Card>

        {/* Bank Statement Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 className="h-5 w-5 text-info" />
              Relevé Bancaire <span className="text-sm font-normal text-muted-foreground">(Optionnel)</span>
            </CardTitle>
            <CardDescription>
              Vous pouvez ajouter le relevé bancaire maintenant ou plus tard
            </CardDescription>
          </CardHeader>
          <CardContent>
            <FileDropzone
              onFilesSelected={handleBankStatementFiles}
              accept={{ 'application/pdf': ['.pdf'] }}
              maxFiles={1}
              disabled={createMutation.isPending}
            />
            {bankStatementFile && (
              <p className="mt-2 text-sm text-success">
                ✓ {bankStatementFile.name}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Company Info (Read-only) */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building2 className="h-5 w-5" />
            Informations Entreprise
          </CardTitle>
          <CardDescription>
            Ces informations proviennent de vos paramètres
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loadingSettings ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="space-y-2">
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ))}
            </div>
          ) : settingsError ? (
            <div className="text-center py-4">
              <AlertCircle className="h-8 w-8 mx-auto text-destructive mb-2" />
              <p className="text-sm text-destructive mb-2">
                Erreur de chargement des paramètres
              </p>
              <Button variant="outline" size="sm" onClick={() => refetchSettings()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Réessayer
              </Button>
            </div>
          ) : companySettings ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <Label className="text-muted-foreground text-xs">Raison Sociale</Label>
                <Input value={companySettings.name} disabled className="bg-muted" />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">ICE</Label>
                <Input value={companySettings.ice} disabled className="bg-muted" />
              </div>
              <div>
                <Label className="text-muted-foreground text-xs">RC</Label>
                <Input value={companySettings.rc || '-'} disabled className="bg-muted" />
              </div>
            </div>
          ) : (
            <div className="text-center py-4">
              <AlertCircle className="h-8 w-8 mx-auto text-warning mb-2" />
              <p className="text-sm text-muted-foreground">
                Veuillez configurer les informations de votre entreprise dans les paramètres.
              </p>
              <Button 
                variant="outline" 
                size="sm" 
                className="mt-2"
                onClick={() => navigate("/settings")}
              >
                Aller aux paramètres
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit Button */}
      <div className="flex justify-end gap-3">
        <Button variant="outline" onClick={() => navigate("/drafts")}>
          Annuler
        </Button>
        <Button 
          onClick={handleSubmit} 
          disabled={!canSubmit}
        >
          {createMutation.isPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Traitement OCR en cours...
            </>
          ) : (
            <>
              Créer le Brouillon
              <ArrowRight className="h-4 w-4 ml-2" />
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
