import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { batchAPI, draftAPI } from "@/lib/api";
import { Batch } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { StatusBadge } from "@/components/StatusBadge";
import { Skeleton } from "@/components/ui/skeleton";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { FileOutput, Download, Plus, Loader2, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "@/hooks/use-toast";

/**
 * Format date to DD/MM/YYYY format for DGI compliance
 */
const formatDGIDate = (dateStr: string | undefined): string => {
  if (!dateStr) return '';
  try {
    return format(new Date(dateStr), 'dd/MM/yyyy');
  } catch {
    return dateStr;
  }
};

/**
 * Format number with 2 decimal places
 */
const formatAmount = (amount: number | undefined): string => {
  if (amount === undefined || amount === null) return '0.00';
  return amount.toFixed(2);
};

/**
 * Escape CSV field - handle commas, quotes, and newlines
 */
const escapeCSVField = (value: string | number | undefined): string => {
  if (value === undefined || value === null) return '';
  const str = String(value);
  // If contains comma, quote, or newline, wrap in quotes and escape internal quotes
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

export default function Declarations() {
  const queryClient = useQueryClient();

  // For now, we'll use batches that are validated/exported as declarations
  const { data: rawData, isLoading, error, refetch } = useQuery({
    queryKey: ["batches"],
    queryFn: batchAPI.list,
  });

  // Normalize API response - handle both array and object responses
  const batches = Array.isArray(rawData)
    ? rawData
    : (rawData as any)?.items ?? (rawData as any)?.data ?? (rawData as any)?.batches ?? [];

  const validatedBatches = batches.filter((b: Batch) => 
    b.status === 'validated' || b.status === 'exported'
  );

  const handleExport = async (batchId: string) => {
    try {
      // Load drafts data
      const drafts = await queryClient.fetchQuery({
        queryKey: ["drafts"],
        queryFn: draftAPI.list,
      });
      
      const validatedDrafts = drafts?.filter(d => d.status === 'VALIDATED') || [];

      if (validatedDrafts.length === 0) {
        toast({
          title: "Aucune donnée",
          description: "Aucun brouillon validé à exporter",
          variant: "destructive"
        });
        return;
      }

      // DGI CSV format - 17 columns matching official form
      // Use exact French headers as per DGI requirements
      const headers = [
        "N° IF",
        "Raison Sociale",
        "ICE",
        "N° RC",
        "Adresse",
        "N° Facture",
        "Date Émission",
        "Nature Marchandises/Travaux/Services",
        "Date Livraison",
        "Montant TTC",
        "Montant Non Payé",
        "Montant Payé",
        "Mode Paiement",
        "Mois Retard Non Payé",
        "Mois Retard Payé",
        "Pénalité",
        "Date Validation"
      ];

      const csvRows: string[] = [headers.join(',')];

      validatedDrafts.forEach((d) => {
        const row = [
          escapeCSVField(d.data.supplier_if),
          escapeCSVField(d.data.supplier_name),
          escapeCSVField(d.data.supplier_ice),
          escapeCSVField(d.data.supplier_rc),
          escapeCSVField(d.data.supplier_address),
          escapeCSVField(d.data.invoice_number),
          formatDGIDate(d.data.invoice_issue_date),
          escapeCSVField(d.data.nature_of_goods),
          formatDGIDate(d.data.invoice_delivery_date),
          formatAmount(d.data.invoice_amount_ttc),
          formatAmount(d.data.payment_amount_unpaid),
          formatAmount(d.data.payment_amount_paid),
          escapeCSVField(d.data.payment_mode),
          String(d.data.months_delay_unpaid || 0),
          String(d.data.months_delay_paid || 0),
          formatAmount(d.data.penalty_amount),
          d.validated_at ? formatDGIDate(d.validated_at) : '',
        ];
        csvRows.push(row.join(','));
      });

      const csvContent = csvRows.join("\n");
      
      // Add UTF-8 BOM for Excel compatibility
      const BOM = '\uFEFF';
      const blob = new Blob([BOM + csvContent], { type: "text/csv;charset=utf-8;" });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      
      // Filename per DGI format: Declaration_DGI_Article_78-2_{period}_{date}.csv
      const today = format(new Date(), 'yyyy-MM-dd');
      const period = format(new Date(), 'yyyy-MM', { locale: fr });
      link.setAttribute("download", `Declaration_DGI_Article_78-2_${period}_${today}.csv`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({ 
        title: "Export CSV réussi", 
        description: `${validatedDrafts.length} brouillon(s) exporté(s) au format DGI`
      });
    } catch (error) {
      console.error('[Export Error]', error);
      toast({ 
        title: "Erreur d'export", 
        description: error instanceof Error ? error.message : "Impossible de télécharger le fichier",
        variant: "destructive" 
      });
    }
  };

  const formatCurrency = (amount: number) => 
    new Intl.NumberFormat("fr-MA", { style: "currency", currency: "MAD" }).format(amount);

  // Error state
  if (error) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Déclarations DGI</h1>
            <p className="text-muted-foreground">Exporter les lots validés pour la déclaration fiscale</p>
          </div>
        </div>

        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
              <h3 className="font-medium text-lg mb-2">Erreur de chargement</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {error instanceof Error ? error.message : "Impossible de charger les données"}
              </p>
              <Button variant="outline" onClick={() => refetch()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Réessayer
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Déclarations DGI</h1>
          <p className="text-muted-foreground">Exporter les lots validés pour la déclaration fiscale</p>
        </div>
        <Link to="/batches/new">
          <Button><Plus className="h-4 w-4 mr-2" />Nouveau Lot</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileOutput className="h-5 w-5" />
            Lots Validés ({validatedBatches.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-24" />
                </div>
              ))}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Entreprise</TableHead>
                  <TableHead>ICE</TableHead>
                  <TableHead>Factures</TableHead>
                  <TableHead>Statut</TableHead>
                  <TableHead>Date de Validation</TableHead>
                  <TableHead>Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {validatedBatches.map((batch: Batch) => (
                  <TableRow key={batch.batch_id}>
                    <TableCell className="font-medium">{batch.company_name}</TableCell>
                    <TableCell className="font-mono text-sm">{batch.company_ice}</TableCell>
                    <TableCell>{batch.total_invoices}</TableCell>
                    <TableCell><StatusBadge status={batch.status} /></TableCell>
                    <TableCell>
                      {batch.validated_at 
                        ? format(new Date(batch.validated_at), "dd/MM/yyyy", { locale: fr })
                        : "—"
                      }
                    </TableCell>
                    <TableCell>
                      <Button 
                        variant="outline" 
                        size="sm" 
                        onClick={() => handleExport(batch.batch_id)}
                      >
                        <Download className="h-4 w-4 mr-1" />CSV DGI
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {validatedBatches.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center py-12">
                      <FileOutput className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                      <p className="font-medium text-foreground mb-1">Aucun lot validé</p>
                      <p className="text-sm text-muted-foreground">
                        Validez un lot pour pouvoir l'exporter au format DGI.
                      </p>
                      <Link to="/drafts" className="inline-block mt-4">
                        <Button variant="outline" size="sm">
                          Voir les brouillons
                        </Button>
                      </Link>
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
