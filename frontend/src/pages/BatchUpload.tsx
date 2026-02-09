import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { batchAPI } from "@/lib/api";
import { FileDropzone } from "@/components/FileDropzone";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { ArrowLeft, ArrowRight, FileText, CreditCard, Loader2, CheckCircle } from "lucide-react";

export default function BatchUpload() {
  const { id: batchId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  
  const [invoiceFiles, setInvoiceFiles] = useState<File[]>([]);
  const [paymentFiles, setPaymentFiles] = useState<File[]>([]);
  const [invoicesUploaded, setInvoicesUploaded] = useState(false);
  const [paymentsUploaded, setPaymentsUploaded] = useState(false);

  const { data: batch, isLoading } = useQuery({
    queryKey: ["batch", batchId],
    queryFn: () => batchAPI.get(batchId!),
    enabled: !!batchId,
  });

  const uploadInvoicesMutation = useMutation({
    mutationFn: () => batchAPI.uploadInvoices(batchId!, invoiceFiles),
    onSuccess: (result) => {
      setInvoicesUploaded(true);
      queryClient.invalidateQueries({ queryKey: ["batch", batchId] });
      toast({
        title: "Factures téléchargées",
        description: `${result.uploaded_count} fichier(s) téléchargé(s)`,
      });
    },
    onError: () => {
      toast({
        title: "Erreur",
        description: "Échec du téléchargement des factures",
        variant: "destructive",
      });
    },
  });

  const uploadPaymentsMutation = useMutation({
    mutationFn: () => batchAPI.uploadPayments(batchId!, paymentFiles),
    onSuccess: (result) => {
      setPaymentsUploaded(true);
      queryClient.invalidateQueries({ queryKey: ["batch", batchId] });
      toast({
        title: "Paiements téléchargés",
        description: `${result.uploaded_count} fichier(s) téléchargé(s)`,
      });
    },
    onError: () => {
      toast({
        title: "Erreur",
        description: "Échec du téléchargement des paiements",
        variant: "destructive",
      });
    },
  });

  const processMutation = useMutation({
    mutationFn: () => batchAPI.process(batchId!),
    onSuccess: () => {
      toast({
        title: "Traitement lancé",
        description: "Le lot est en cours de traitement...",
      });
      navigate(`/batches/${batchId}/processing`);
    },
    onError: () => {
      toast({
        title: "Erreur",
        description: "Impossible de lancer le traitement",
        variant: "destructive",
      });
    },
  });

  const handleUploadInvoices = () => {
    if (invoiceFiles.length === 0) return;
    uploadInvoicesMutation.mutate();
  };

  const handleUploadPayments = () => {
    if (paymentFiles.length === 0) return;
    uploadPaymentsMutation.mutate();
  };

  const handleStartProcessing = () => {
    if (!invoicesUploaded) {
      toast({
        title: "Factures requises",
        description: "Veuillez télécharger au moins une facture",
        variant: "destructive",
      });
      return;
    }
    processMutation.mutate();
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Téléchargement des Documents</h1>
          <p className="text-muted-foreground">
            Lot: {batch?.company_name} • ICE: {batch?.company_ice}
          </p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Invoices Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Factures
              {invoicesUploaded && <CheckCircle className="h-5 w-5 text-success" />}
            </CardTitle>
            <CardDescription>
              Téléchargez vos factures fournisseurs au format PDF
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileDropzone
              onFilesSelected={setInvoiceFiles}
              disabled={uploadInvoicesMutation.isPending || invoicesUploaded}
            />
            
            {invoiceFiles.length > 0 && !invoicesUploaded && (
              <Button
                onClick={handleUploadInvoices}
                disabled={uploadInvoicesMutation.isPending}
                className="w-full"
              >
                {uploadInvoicesMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                Télécharger {invoiceFiles.length} facture(s)
              </Button>
            )}

            {invoicesUploaded && (
              <p className="text-sm text-success flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Factures téléchargées avec succès
              </p>
            )}
          </CardContent>
        </Card>

        {/* Payments Upload */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="h-5 w-5" />
              Paiements
              {paymentsUploaded && <CheckCircle className="h-5 w-5 text-success" />}
            </CardTitle>
            <CardDescription>
              Téléchargez vos relevés bancaires ou preuves de paiement (optionnel)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileDropzone
              onFilesSelected={setPaymentFiles}
              disabled={uploadPaymentsMutation.isPending || paymentsUploaded}
            />
            
            {paymentFiles.length > 0 && !paymentsUploaded && (
              <Button
                onClick={handleUploadPayments}
                disabled={uploadPaymentsMutation.isPending}
                className="w-full"
              >
                {uploadPaymentsMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : null}
                Télécharger {paymentFiles.length} paiement(s)
              </Button>
            )}

            {paymentsUploaded && (
              <p className="text-sm text-success flex items-center gap-2">
                <CheckCircle className="h-4 w-4" />
                Paiements téléchargés avec succès
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Start Processing */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="font-medium text-foreground">Lancer le traitement</h4>
              <p className="text-sm text-muted-foreground">
                OCR, extraction, rapprochement et calcul des pénalités
              </p>
            </div>
            <Button
              onClick={handleStartProcessing}
              disabled={!invoicesUploaded || processMutation.isPending}
              size="lg"
            >
              {processMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
              ) : (
                <ArrowRight className="h-4 w-4 mr-2" />
              )}
              Démarrer le traitement
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
