import { useQuery } from "@tanstack/react-query";
import { batchAPI } from "@/lib/api";
import { Batch } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { 
  BookOpen, 
  Download, 
  FileText, 
  CreditCard, 
  AlertCircle, 
  RefreshCw,
  FileDown
} from "lucide-react";
import { toast } from "@/hooks/use-toast";
import { useState } from "react";

/**
 * Format date to DD/MM/YYYY format for DGI compliance
 */
const formatDGIDate = (dateStr: string | undefined): string => {
  if (!dateStr) return '—';
  try {
    return format(new Date(dateStr), 'dd/MM/yyyy', { locale: fr });
  } catch {
    return dateStr || '—';
  }
};

/**
 * Format amount with MAD currency
 */
const formatAmount = (amount: number | undefined): string => {
  if (amount === undefined || amount === null) return '0,00 MAD';
  return new Intl.NumberFormat('fr-MA', { 
    style: 'currency', 
    currency: 'MAD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(amount);
};

/**
 * Escape CSV field - handle commas, quotes, and newlines
 */
const escapeCSVField = (value: string | number | undefined): string => {
  if (value === undefined || value === null) return '';
  const str = String(value);
  if (str.includes(',') || str.includes('"') || str.includes('\n')) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

/**
 * Extract invoice records from validated batches
 */
interface InvoiceRecord {
  batchId: string;
  batchValidatedAt: string;
  supplierName: string;
  supplierICE: string;
  supplierRC?: string;
  invoiceNumber: string;
  invoiceDate: string;
  deliveryDate?: string;
  paymentDate?: string;
  amountTTC: number;
  amountPaid: number;
  amountUnpaid: number;
  legalDueDate?: string;
  monthsDelay: number;
  penaltyAmount: number;
  hasInvoicePDF: boolean;
  hasPaymentPDF: boolean;
  invoiceDocumentId?: string;
  paymentDocumentId?: string;
}

export default function RegistreDGI() {
  const [exportingAll, setExportingAll] = useState(false);

  // Fetch all batches and filter validated ones
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

  // Extract invoice records from validated batches
  const invoiceRecords: InvoiceRecord[] = [];
  
  validatedBatches.forEach((batch: Batch) => {
    // Extract from invoices_data (backend format)
    const invoices = batch.invoices_data || [];
    const payments = batch.payments_data || [];
    const legalResults = batch.legal_results || [];
    const documents = (batch as any).documents || [];

    // Find invoice and payment document IDs
    const invoiceDoc = documents.find((d: any) => d.document_type === 'invoice');
    const paymentDoc = documents.find((d: any) => d.document_type === 'payment');
    
    console.log(`📄 Batch ${batch.batch_id}: Found ${documents.length} documents`, {
      invoiceDoc: invoiceDoc?.document_id,
      paymentDoc: paymentDoc?.document_id,
      hasInvoice: !!invoiceDoc,
      hasPayment: !!paymentDoc
    });

    invoices.forEach((invoice: any, idx: number) => {
      const legalResult = legalResults[idx] || {};
      
      // Find matching payment by invoice_id
      const matchingResult = batch.matching_results?.find((m: any) => 
        m.invoice_id === invoice.invoice_id
      );
      
      const payment = payments.find((p: any) => 
        p.payment_id === matchingResult?.matches?.[0]?.payment_id
      );

      // Calculate paid and unpaid amounts from matching result
      const totalPaid = matchingResult?.total_paid || 0;
      const invoiceTotal = invoice.amounts?.total_ttc || invoice.amount_ttc || invoice.invoice_amount_ttc || 0;
      const amountUnpaid = Math.max(0, invoiceTotal - totalPaid);

      const record = {
        batchId: batch.batch_id,
        batchValidatedAt: batch.validated_at || batch.updated_at,
        // Handle nested supplier structure
        supplierName: invoice.supplier?.name || invoice.supplier_name || '—',
        supplierICE: invoice.supplier?.ice || invoice.supplier_ice || '—',
        supplierRC: invoice.supplier?.rc || invoice.supplier_rc,
        // Handle nested invoice structure
        invoiceNumber: invoice.invoice?.number || invoice.invoice_number || '—',
        invoiceDate: invoice.invoice?.issue_date || invoice.invoice_issue_date || invoice.invoice_date,
        deliveryDate: invoice.invoice?.delivery_date || invoice.invoice_delivery_date || invoice.delivery_date,
        // Handle payment date from matching results or payment data
        paymentDate: matchingResult?.payment_dates?.[0] || payment?.date || payment?.payment_date,
        // Handle nested amounts structure
        amountTTC: invoiceTotal,
        amountPaid: totalPaid,
        amountUnpaid: amountUnpaid,
        legalDueDate: legalResult.legal_due_date,
        monthsDelay: legalResult.months_of_delay || legalResult.months_delay || 0,
        penaltyAmount: legalResult.penalty_amount || 0,
        hasInvoicePDF: !!invoiceDoc,
        hasPaymentPDF: !!paymentDoc,
        invoiceDocumentId: invoiceDoc?.document_id,
        paymentDocumentId: paymentDoc?.document_id,
      };
      
      console.log(`📋 Invoice record created:`, {
        invoiceNumber: record.invoiceNumber,
        hasInvoicePDF: record.hasInvoicePDF,
        hasPaymentPDF: record.hasPaymentPDF,
        invoiceDocId: record.invoiceDocumentId,
        paymentDocId: record.paymentDocumentId
      });
      
      invoiceRecords.push(record);
    });
  });

  /**
   * View invoice PDF
   */
  const handleViewInvoice = (record: InvoiceRecord) => {
    if (!record.hasInvoicePDF || !record.invoiceDocumentId) {
      toast({
        title: "PDF non disponible",
        description: "Le PDF de la facture n'est pas disponible",
        variant: "destructive"
      });
      return;
    }
    // Open PDF in new tab using full API URL
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.open(`${apiUrl}/api/batches/${record.batchId}/documents/${record.invoiceDocumentId}/pdf`, '_blank');
  };

  /**
   * View payment PDF
   */
  const handleViewPayment = (record: InvoiceRecord) => {
    if (!record.hasPaymentPDF || !record.paymentDocumentId) {
      toast({
        title: "PDF non disponible",
        description: "Le PDF du relevé bancaire n'est pas disponible",
        variant: "destructive"
      });
      return;
    }
    // Open PDF in new tab using full API URL
    const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    window.open(`${apiUrl}/api/batches/${record.batchId}/documents/${record.paymentDocumentId}/pdf`, '_blank');
  };

  /**
   * Export single invoice record to CSV
   */
  const handleExportSingle = async (record: InvoiceRecord) => {
    try {
      // Create CSV for single record
      const headers = [
        "N° IF",
        "Raison Sociale",
        "ICE",
        "N° RC",
        "N° Facture",
        "Date Émission",
        "Date Livraison",
        "Montant TTC (MAD)",
        "Date Échéance Légale",
        "Date Paiement",
        "Mois de Retard",
        "Pénalité (MAD)",
        "Date Validation"
      ];

      const row = [
        escapeCSVField(''),
        escapeCSVField(record.supplierName),
        escapeCSVField(record.supplierICE),
        escapeCSVField(record.supplierRC || ''),
        escapeCSVField(record.invoiceNumber),
        formatDGIDate(record.invoiceDate),
        formatDGIDate(record.deliveryDate),
        escapeCSVField(record.amountTTC.toFixed(2)),
        formatDGIDate(record.legalDueDate),
        formatDGIDate(record.paymentDate),
        String(record.monthsDelay),
        escapeCSVField(record.penaltyAmount.toFixed(2)),
        formatDGIDate(record.batchValidatedAt),
      ];

      const csvContent = [headers.join(','), row.join(',')].join('\n');
      const BOM = '\uFEFF';
      const blob = new Blob([BOM + csvContent], { type: "text/csv;charset=utf-8;" });
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `Facture_${record.invoiceNumber}_${format(new Date(), 'yyyy-MM-dd')}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      
      toast({ 
        title: "Export réussi", 
        description: `Facture ${record.invoiceNumber} exportée`
      });
    } catch (error) {
      console.error('[Export Error]', error);
      toast({ 
        title: "Erreur d'export", 
        description: error instanceof Error ? error.message : "Impossible d'exporter",
        variant: "destructive" 
      });
    }
  };

  /**
   * Export all validated records to CSV
   */
  const handleExportAll = async () => {
    if (invoiceRecords.length === 0) {
      toast({
        title: "Aucune donnée",
        description: "Aucun enregistrement validé à exporter",
        variant: "destructive"
      });
      return;
    }

    setExportingAll(true);

    try {
      // DGI CSV format - Official columns
      const headers = [
        "N° IF",
        "Raison Sociale",
        "ICE",
        "N° RC",
        "N° Facture",
        "Date Émission",
        "Date Livraison",
        "Montant TTC (MAD)",
        "Date Échéance Légale",
        "Date Paiement",
        "Mois de Retard",
        "Pénalité (MAD)",
        "Date Validation"
      ];

      const csvRows: string[] = [headers.join(',')];

      invoiceRecords.forEach((record) => {
        const row = [
          escapeCSVField(''), // N° IF - to be filled by company
          escapeCSVField(record.supplierName),
          escapeCSVField(record.supplierICE),
          escapeCSVField(record.supplierRC || ''),
          escapeCSVField(record.invoiceNumber),
          formatDGIDate(record.invoiceDate),
          formatDGIDate(record.deliveryDate),
          escapeCSVField(record.amountTTC.toFixed(2)),
          formatDGIDate(record.legalDueDate),
          formatDGIDate(record.paymentDate),
          String(record.monthsDelay),
          escapeCSVField(record.penaltyAmount.toFixed(2)),
          formatDGIDate(record.batchValidatedAt),
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
      
      // Filename: Registre_DGI_Article_78-2_{date}.csv
      const today = format(new Date(), 'yyyy-MM-dd');
      link.setAttribute("download", `Registre_DGI_Article_78-2_${today}.csv`);
      
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({ 
        title: "Export réussi", 
        description: `${invoiceRecords.length} enregistrement(s) exporté(s) au format DGI`
      });
    } catch (error) {
      console.error('[Export All Error]', error);
      toast({ 
        title: "Erreur d'export", 
        description: error instanceof Error ? error.message : "Impossible d'exporter le registre",
        variant: "destructive" 
      });
    } finally {
      setExportingAll(false);
    }
  };

  // Error state
  if (error) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Registre DGI</h1>
            <p className="text-muted-foreground">Registre des factures validées pour déclaration DGI</p>
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
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <BookOpen className="h-7 w-7" />
            Registre DGI
          </h1>
          <p className="text-muted-foreground mt-1">
            Registre des factures validées - Article 78-2 (Retards de paiement)
          </p>
        </div>
        <Button 
          onClick={handleExportAll}
          disabled={exportingAll || invoiceRecords.length === 0}
          size="lg"
        >
          {exportingAll ? (
            <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <FileDown className="h-4 w-4 mr-2" />
          )}
          Exporter tout le registre
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Total Enregistrements
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{invoiceRecords.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Factures validées
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Lots Validés
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{validatedBatches.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Lots traités
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Montant Impayé Total
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {formatAmount(invoiceRecords.reduce((sum, r) => sum + r.amountUnpaid, 0))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Reste à payer
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Pénalités Totales
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatAmount(invoiceRecords.reduce((sum, r) => sum + r.penaltyAmount, 0))}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Montant cumulé
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Enregistrements Validés
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-4">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="flex items-center gap-4">
                  <Skeleton className="h-4 w-32" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-20" />
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-8 w-32" />
                </div>
              ))}
            </div>
          ) : (
            <div className="border rounded-lg">
              <Table className="w-full">
                <TableHeader>
                  <TableRow>
                    <TableHead>Fournisseur</TableHead>
                    <TableHead className="text-xs">ICE</TableHead>
                    <TableHead className="text-xs">N° Fact.</TableHead>
                    <TableHead className="text-xs">Date Émis.</TableHead>
                    <TableHead className="text-xs">Date Liv.</TableHead>
                    <TableHead className="text-xs">Date Paiem.</TableHead>
                    <TableHead className="text-right text-xs">Montant TTC</TableHead>
                    <TableHead className="text-right text-xs">Payé</TableHead>
                    <TableHead className="text-right text-xs">Impayé</TableHead>
                    <TableHead className="text-xs">Échéance</TableHead>
                    <TableHead className="text-center text-xs">Retard</TableHead>
                    <TableHead className="text-right text-xs">Pénalité</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoiceRecords.map((record, idx) => (
                    <TableRow key={`${record.batchId}-${idx}`}>
                      <TableCell className="font-medium">
                        {record.supplierName}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {record.supplierICE}
                      </TableCell>
                      <TableCell className="font-mono text-sm">
                        {record.invoiceNumber}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDGIDate(record.invoiceDate)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDGIDate(record.deliveryDate)}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDGIDate(record.paymentDate)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatAmount(record.amountTTC)}
                      </TableCell>
                      <TableCell className="text-right text-green-600">
                        {record.amountPaid > 0 ? formatAmount(record.amountPaid) : '—'}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {record.amountUnpaid > 0 ? (
                          <span className="text-orange-600">
                            {formatAmount(record.amountUnpaid)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">
                        {formatDGIDate(record.legalDueDate)}
                      </TableCell>
                      <TableCell className="text-center">
                        {(() => {
                          // Simplified 2-state badge for validated register
                          // Green = Paid, Red = Unpaid (with optional months delay info)
                          if (record.amountPaid >= record.amountTTC && record.amountTTC > 0) {
                            return (
                              <Badge className="bg-green-500 hover:bg-green-600">
                                Payé
                              </Badge>
                            );
                          }
                          
                          // Unpaid - show red with months delay if applicable
                          if (record.monthsDelay > 0) {
                            return (
                              <Badge variant="destructive">
                                {record.monthsDelay} mois
                              </Badge>
                            );
                          }
                          
                          // Simple red badge for unpaid without delay info
                          return (
                            <Badge variant="destructive">
                              Non payé
                            </Badge>
                          );
                        })()}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {record.penaltyAmount > 0 ? (
                          <span className="text-destructive">
                            {formatAmount(record.penaltyAmount)}
                          </span>
                        ) : (
                          <span className="text-muted-foreground">
                            0,00 MAD
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleViewInvoice(record)}
                            disabled={!record.hasInvoicePDF}
                            title="Voir facture PDF"
                          >
                            <FileText className="h-4 w-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm"
                            onClick={() => handleViewPayment(record)}
                            disabled={!record.hasPaymentPDF}
                            title="Voir relevé bancaire PDF"
                          >
                            <CreditCard className="h-4 w-4" />
                          </Button>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => handleExportSingle(record)}
                            title="Exporter cette facture en CSV"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                  {invoiceRecords.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={11} className="text-center py-12">
                        <BookOpen className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                        <p className="font-medium text-foreground mb-1">
                          Aucun enregistrement validé
                        </p>
                        <p className="text-sm text-muted-foreground">
                          Les factures validées apparaîtront ici pour la déclaration DGI.
                        </p>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Footer */}
      {invoiceRecords.length > 0 && (
        <Card className="bg-muted/50">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="h-5 w-5 text-muted-foreground mt-0.5" />
              <div className="text-sm text-muted-foreground">
                <p className="font-medium text-foreground mb-1">
                  Registre immuable
                </p>
                <p>
                  Les enregistrements validés sont en lecture seule et ne peuvent plus être modifiés.
                  Ce registre constitue la source officielle pour votre déclaration DGI Article 78-2.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
