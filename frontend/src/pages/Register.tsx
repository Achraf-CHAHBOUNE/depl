import { useQuery } from "@tanstack/react-query";
import { draftAPI } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Loader2, ClipboardCheck, FileText } from "lucide-react";
import { format } from "date-fns";
import { fr } from "date-fns/locale";

export default function Register() {
  const { data: drafts, isLoading } = useQuery({
    queryKey: ["drafts"],
    queryFn: draftAPI.list,
  });

  // Only show validated drafts in the register
  const validatedDrafts = drafts?.filter(d => d.status === 'VALIDATED') || [];

  // Calculate totals
  const totalAmount = validatedDrafts.reduce((sum, d) => sum + (d.data.invoice_amount_ttc || 0), 0);
  const totalPenalties = validatedDrafts.reduce((sum, d) => sum + (d.data.penalty_amount || 0), 0);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Registre DGI</h1>
        <p className="text-muted-foreground">
          Liste des factures validées pour la déclaration DGI
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-primary/10">
                <ClipboardCheck className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{validatedDrafts.length}</p>
                <p className="text-sm text-muted-foreground">Factures validées</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-info/10">
                <FileText className="h-5 w-5 text-info" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalAmount.toLocaleString('fr-MA')} MAD</p>
                <p className="text-sm text-muted-foreground">Total TTC</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-warning/10">
                <FileText className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="text-2xl font-bold">{totalPenalties.toLocaleString('fr-MA')} MAD</p>
                <p className="text-sm text-muted-foreground">Total pénalités</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Register Table */}
      <Card>
        <CardHeader>
          <CardTitle>Factures Enregistrées</CardTitle>
          <CardDescription>
            Ces factures sont prêtes pour l'export DGI
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : validatedDrafts.length > 0 ? (
            <div className="border rounded-lg overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Fournisseur</TableHead>
                    <TableHead>ICE Fournisseur</TableHead>
                    <TableHead>N° Facture</TableHead>
                    <TableHead>Date Facture</TableHead>
                    <TableHead>Montant TTC</TableHead>
                    <TableHead>Date Paiement</TableHead>
                    <TableHead>Jours Retard</TableHead>
                    <TableHead>Pénalité</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {validatedDrafts.map((draft) => (
                    <TableRow key={draft.id}>
                      <TableCell className="font-medium">
                        {draft.data.supplier_name || "-"}
                      </TableCell>
                      <TableCell className="font-mono text-xs">
                        {draft.data.supplier_ice || "-"}
                      </TableCell>
                      <TableCell>
                        {draft.data.invoice_number || "-"}
                      </TableCell>
                      <TableCell>
                        {draft.data.invoice_issue_date 
                          ? format(new Date(draft.data.invoice_issue_date), 'dd/MM/yyyy')
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.invoice_amount_ttc 
                          ? `${draft.data.invoice_amount_ttc.toLocaleString('fr-MA')} MAD`
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.payment_date 
                          ? format(new Date(draft.data.payment_date), 'dd/MM/yyyy')
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.days_overdue !== undefined ? (
                          <Badge variant={draft.data.days_overdue > 0 ? "destructive" : "secondary"}>
                            {draft.data.days_overdue} jours
                          </Badge>
                        ) : "-"}
                      </TableCell>
                      <TableCell>
                        {draft.data.penalty_amount !== undefined && draft.data.penalty_amount > 0 ? (
                          <span className="text-warning font-medium">
                            {draft.data.penalty_amount.toLocaleString('fr-MA')} MAD
                          </span>
                        ) : (
                          <span className="text-success">0 MAD</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12">
              <ClipboardCheck className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">
                Aucune facture validée dans le registre
              </p>
              <p className="text-sm text-muted-foreground mt-1">
                Validez des brouillons pour les ajouter au registre
              </p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
