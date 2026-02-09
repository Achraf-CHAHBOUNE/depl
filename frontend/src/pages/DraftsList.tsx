import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { draftAPI } from "@/lib/api";
import { Draft, DraftStatus } from "@/types";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { 
  Loader2, 
  Plus, 
  Search, 
  FileText, 
  Eye,
  CheckCircle,
  Clock,
  Trash2,
  Check,
  X,
  AlertCircle,
  AlertTriangle
} from "lucide-react";
import { format } from "date-fns";
import { fr } from "date-fns/locale";
import { useToast } from "@/hooks/use-toast";

const statusConfig: Record<DraftStatus, { label: string; variant: "default" | "secondary" | "outline" }> = {
  DRAFT: { label: "Brouillon", variant: "secondary" },
  VALIDATED: { label: "Validé", variant: "default" },
};

// Payment status helper - Two-phase logic:
// Phase 1: No payment proof = time-based tracking (gray/orange/red)
// Phase 2: Has payment proof = amount-based tracking (green/purple/red)
const getPaymentStatus = (draft: Draft): { color: string; label: string; bgColor: string; animate?: boolean } => {
  const paid = draft.data.payment_amount_paid || 0;
  const total = draft.data.invoice_amount_ttc || 0;
  const unpaid = Math.max(0, total - paid);
  const penaltyAmount = draft.data.penalty_amount || 0;
  const legalDueDate = draft.data.legal_due_date;
  const hasPaymentProof = !!draft.bank_statement_file_url;
  
  const WARNING_DAYS = 10;
  
  // DEBUG logging
  console.log('🔍 Payment Status Debug:', {
    draftId: draft.id,
    paid,
    total,
    legalDueDate,
    hasPaymentProof,
    bankStatementUrl: draft.bank_statement_file_url,
  });
  
  // Calculate days until due if we have a due date
  let daysUntilDue: number | null = null;
  if (legalDueDate) {
    const dueDate = new Date(legalDueDate);
    const today = new Date();
    daysUntilDue = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
    console.log('📅 Date calculation:', { dueDate: dueDate.toISOString(), today: today.toISOString(), daysUntilDue });
  } else {
    console.log('⚠️ No legalDueDate available');
  }
  
  // Check if deadline is approaching (≤ 10 days and not overdue)
  const isDeadlineApproaching = daysUntilDue !== null && daysUntilDue > 0 && daysUntilDue <= WARNING_DAYS;
  const isOverdue = daysUntilDue !== null && daysUntilDue < 0;
  
  console.log('🎯 Logic check:', { isDeadlineApproaching, isOverdue, paid, willShowOrange: isDeadlineApproaching && paid === 0 });
  
  // PRIORITY 1: Deadline warning takes precedence when no real payment made
  // Show orange warning if:
  // - Due date is approaching (≤ 10 days)
  // - AND either: no payment proof, OR payment proof exists but paid = 0
  if (isDeadlineApproaching && paid === 0) {
    console.log('✅ Showing ORANGE deadline warning');
    return { 
      color: "text-orange-800", 
      label: `Échéance ${daysUntilDue}j`, 
      bgColor: "bg-orange-200 border-2 border-orange-500",
      animate: true 
    };
  }
  
  // PRIORITY 2: Overdue takes precedence
  if (isOverdue && paid === 0) {
    console.log('✅ Showing RED overdue');
    return { color: "text-red-700", label: "En retard", bgColor: "bg-red-100" };
  }
  
  // PHASE 2: Has payment proof with actual payment - check amounts
  if (hasPaymentProof && paid > 0) {
    console.log('✅ Has payment proof with paid > 0');
    // Red: Has penalties (overdue with financial impact)
    if (penaltyAmount > 0) {
      return { color: "text-red-700", label: `Pénalités`, bgColor: "bg-red-100" };
    }
    
    // Green: Fully paid
    if (paid >= total && total > 0) {
      return { color: "text-green-700", label: "Payé", bgColor: "bg-green-100" };
    }
    
    // Purple: Partially paid
    if (paid > 0 && unpaid > 0 && total > 0) {
      return { color: "text-purple-700", label: "Partiellement payé", bgColor: "bg-purple-100" };
    }
  }
  
  // Has payment proof but paid = 0 (and not approaching deadline - handled above)
  if (hasPaymentProof && paid === 0) {
    console.log('✅ Showing RED non payé (has proof but paid=0)');
    return { color: "text-red-700", label: "Non payé", bgColor: "bg-red-100" };
  }
  
  console.log('✅ Showing GRAY default (no proof, no deadline concern)');
  // No payment proof, no due date, or due date is far (> 10 days)
  return { color: "text-gray-700", label: "En attente", bgColor: "bg-gray-100" };
};

// Traffic light status component - shows only the status indicator
const PaymentStatusIndicator = ({ draft }: { draft: Draft }) => {
  const paid = draft.data.payment_amount_paid || 0;
  const total = draft.data.invoice_amount_ttc || 0;
  const legalDueDate = draft.data.legal_due_date;
  
  const WARNING_DAYS = 10;
  
  // Calculate days until due
  let daysUntilDue: number | null = null;
  if (legalDueDate) {
    const dueDate = new Date(legalDueDate);
    const today = new Date();
    daysUntilDue = Math.ceil((dueDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  }
  
  const isOverdue = daysUntilDue !== null && daysUntilDue < 0;
  const isDeadlineApproaching = daysUntilDue !== null && daysUntilDue > 0 && daysUntilDue <= WARNING_DAYS;
  const hasPaymentFile = !!draft.bank_statement_file_url;
  const isFullyPaid = paid >= total && total > 0;
  const isPartiallyPaid = paid > 0 && paid < total;
  const noPayment = paid === 0;
  
  // FULLY PAID - Always green
  if (isFullyPaid) {
    return (
      <div 
        className="flex items-center justify-center w-8 h-8 rounded-full bg-green-100 border-2 border-green-500"
        title="Paiement complet - Facture payée intégralement"
      >
        <Check className="h-5 w-5 text-green-600" />
      </div>
    );
  }
  
  // PARTIALLY PAID
  if (isPartiallyPaid) {
    // Approaching deadline - Orange round circle with days only
    if (isDeadlineApproaching) {
      return (
        <div 
          className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 border-2 border-orange-500 animate-pulse"
          title={`Paiement partiel - Échéance dans ${daysUntilDue} jours - Compléter le paiement`}
        >
          <span className="text-xs font-bold text-orange-700">{daysUntilDue}j</span>
        </div>
      );
    }
    
    // Overdue - Red X with blink
    if (isOverdue) {
      return (
        <div 
          className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500 animate-pulse"
          title="Paiement partiel - Échéance dépassée - Pénalités applicables"
        >
          <X className="h-5 w-5 text-red-600" />
        </div>
      );
    }
    
    // Not approaching - Red X with blink
    return (
      <div 
        className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500 animate-pulse"
        title="Paiement partiel - Pénalités applicables"
      >
        <X className="h-5 w-5 text-red-600" />
      </div>
    );
  }
  
  // NO PAYMENT AT ALL
  if (noPayment) {
    // Overdue - Red X with blink
    if (isOverdue) {
      return (
        <div 
          className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500 animate-pulse"
          title="Non payé - Échéance dépassée - Action urgente requise"
        >
          <X className="h-5 w-5 text-red-600" />
        </div>
      );
    }
    
    // Approaching deadline - Orange round circle with days only
    if (isDeadlineApproaching) {
      return (
        <div 
          className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 border-2 border-orange-500 animate-pulse"
          title={`Non payé - Échéance dans ${daysUntilDue} jours - Paiement imminent`}
        >
          <span className="text-xs font-bold text-orange-700">{daysUntilDue}j</span>
        </div>
      );
    }
    
    // Not yet approaching deadline - gray
    return (
      <div 
        className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 border-2 border-gray-400"
        title="Non payé - En attente de paiement"
      >
        <Clock className="h-4 w-4 text-gray-500" />
      </div>
    );
  }
  
  // Default
  return (
    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 border-2 border-gray-400">
      <Clock className="h-4 w-4 text-gray-500" />
    </div>
  );
};

type PaymentFilter = "all" | "paid" | "partially_paid" | "unpaid";

export default function DraftsList() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const [filter, setFilter] = useState<"all" | DraftStatus>("all");
  const [paymentFilter, setPaymentFilter] = useState<PaymentFilter>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [draftToDelete, setDraftToDelete] = useState<Draft | null>(null);

  const { data: drafts, isLoading } = useQuery({
    queryKey: ["drafts"],
    queryFn: draftAPI.list,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => draftAPI.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts"] });
      toast({
        title: "Brouillon supprimé",
        description: "Le brouillon a été supprimé avec succès",
      });
      setDeleteDialogOpen(false);
      setDraftToDelete(null);
    },
    onError: (error: any) => {
      toast({
        title: "Erreur",
        description: error.message || "Impossible de supprimer le brouillon",
        variant: "destructive",
      });
    },
  });

  const handleDeleteClick = (draft: Draft, e: React.MouseEvent) => {
    e.stopPropagation();
    setDraftToDelete(draft);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = () => {
    if (draftToDelete) {
      deleteMutation.mutate(draftToDelete.id);
    }
  };

  // Helper to get payment category
  const getPaymentCategory = (draft: Draft): PaymentFilter => {
    const paid = draft.data.payment_amount_paid || 0;
    const total = draft.data.invoice_amount_ttc || 0;
    // Calculate unpaid from total - paid (don't trust backend payment_amount_unpaid)
    const unpaid = Math.max(0, total - paid);
    
    if (paid === 0) return "unpaid";
    if (unpaid === 0 && paid > 0) return "paid";
    if (paid > 0 && unpaid > 0) return "partially_paid";
    return "unpaid";
  };

  // Filter drafts
  const filteredDrafts = drafts?.filter((draft) => {
    // Status filter
    if (filter !== "all" && draft.status !== filter) return false;
    
    // Payment filter
    if (paymentFilter !== "all") {
      const category = getPaymentCategory(draft);
      if (category !== paymentFilter) return false;
    }
    
    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      return (
        draft.data.supplier_name?.toLowerCase().includes(query) ||
        draft.data.invoice_number?.toLowerCase().includes(query)
      );
    }
    
    return true;
  }) || [];

  const draftCount = drafts?.filter(d => d.status === 'DRAFT').length || 0;
  const validatedCount = drafts?.filter(d => d.status === 'VALIDATED').length || 0;
  
  // Payment counts
  const paidCount = drafts?.filter(d => getPaymentCategory(d) === 'paid').length || 0;
  const partiallyPaidCount = drafts?.filter(d => getPaymentCategory(d) === 'partially_paid').length || 0;
  const unpaidCount = drafts?.filter(d => getPaymentCategory(d) === 'unpaid').length || 0;

  // Calculate totals
  const totalPenalties = drafts?.reduce((sum, d) => sum + (d.data?.penalty_amount || 0), 0) || 0;
  const totalUnpaid = drafts?.reduce((sum, d) => {
    const total = d.data?.invoice_amount_ttc || 0;
    const paid = d.data?.payment_amount_paid || 0;
    return sum + Math.max(0, total - paid);
  }, 0) || 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Mes Brouillons</h1>
          <p className="text-muted-foreground">
            Gérez vos brouillons de factures et validez-les pour le registre DGI
          </p>
        </div>
        <Link to="/drafts/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Nouveau Brouillon
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-muted">
                <FileText className="h-5 w-5 text-muted-foreground" />
              </div>
              <div>
                <p className="text-2xl font-bold">{drafts?.length || 0}</p>
                <p className="text-sm text-muted-foreground">Total</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-warning/10">
                <Clock className="h-5 w-5 text-warning" />
              </div>
              <div>
                <p className="text-2xl font-bold">{draftCount}</p>
                <p className="text-sm text-muted-foreground">En attente</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-success/10">
                <CheckCircle className="h-5 w-5 text-success" />
              </div>
              <div>
                <p className="text-2xl font-bold">{validatedCount}</p>
                <p className="text-sm text-muted-foreground">Validés</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Financial Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-red-100">
                <AlertTriangle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">{totalPenalties.toLocaleString('fr-MA')} MAD</p>
                <p className="text-sm text-muted-foreground">Total Pénalités</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-lg bg-orange-100">
                <AlertCircle className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold text-orange-600">{totalUnpaid.toLocaleString('fr-MA')} MAD</p>
                <p className="text-sm text-muted-foreground">Total Impayé</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters & Search */}
      <Card>
        <CardHeader className="pb-4">
          <div className="flex flex-col gap-4">
            {/* Status Filter */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <p className="text-sm font-medium mb-2">Statut</p>
                <Tabs value={filter} onValueChange={(v) => setFilter(v as any)}>
                  <TabsList>
                    <TabsTrigger value="all">Tous ({drafts?.length || 0})</TabsTrigger>
                    <TabsTrigger value="DRAFT">Brouillons ({draftCount})</TabsTrigger>
                    <TabsTrigger value="VALIDATED">Validés ({validatedCount})</TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
              <div className="relative w-full sm:w-64">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Rechercher..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-9"
                />
              </div>
            </div>
            
            {/* Payment Filter */}
            <div>
              <p className="text-sm font-medium mb-2">Statut de paiement</p>
              <Tabs value={paymentFilter} onValueChange={(v) => setPaymentFilter(v as PaymentFilter)}>
                <TabsList>
                  <TabsTrigger value="all">Tous ({drafts?.length || 0})</TabsTrigger>
                  <TabsTrigger value="paid">
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500"></span>
                      Payé ({paidCount})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger value="partially_paid">
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                      Partiellement payé ({partiallyPaidCount})
                    </span>
                  </TabsTrigger>
                  <TabsTrigger value="unpaid">
                    <span className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-red-500"></span>
                      Non payé ({unpaidCount})
                    </span>
                  </TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredDrafts.length > 0 ? (
            <div className="border rounded-lg overflow-x-auto max-w-full">
              <Table className="min-w-[1100px]">
                <TableHeader>
                  <TableRow>
                    <TableHead>Fournisseur</TableHead>
                    <TableHead>N° Facture</TableHead>
                    <TableHead>Montant TTC</TableHead>
                    <TableHead>Montant Payé</TableHead>
                    <TableHead>Montant Impayé</TableHead>
                    <TableHead>Pénalités</TableHead>
                    <TableHead>Date Paiement</TableHead>
                    <TableHead>Échéance</TableHead>
                    <TableHead>Livraison</TableHead>
                    <TableHead>Statut</TableHead>
                    <TableHead className="w-[80px] text-center">
                      <Dialog>
                        <DialogTrigger asChild>
                          <div className="flex justify-center gap-1 cursor-pointer hover:opacity-70" title="Cliquer pour voir la légende des statuts de paiement">
                            <div className="w-4 h-4 rounded-full bg-red-500 border-2 border-red-600 animate-pulse" title="Non payé - Échéance dépassée"></div>
                            <div className="w-4 h-4 rounded-full bg-orange-500 border-2 border-orange-600 animate-pulse" title="Échéance dans ≤ 10 jours"></div>
                            <div className="w-4 h-4 rounded-full bg-green-500 border-2 border-green-600" title="Paiement complet"></div>
                          </div>
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl">
                          <DialogHeader>
                            <DialogTitle>Légende des indicateurs de paiement</DialogTitle>
                          </DialogHeader>
                          <div className="space-y-4 py-4">
                            {/* No Payment Section */}
                            <div className="border rounded-lg p-4 bg-gray-50">
                              <h4 className="font-semibold mb-3 text-gray-700">Sans paiement (Pas de relevé bancaire)</h4>
                              <div className="space-y-2">
                                <div className="flex items-center gap-3" title="Non payé - Échéance dépassée - Action urgente requise">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500 animate-pulse">
                                    <X className="h-5 w-5 text-red-600" />
                                  </div>
                                  <span className="text-sm">Échéance dépassée - <span className="text-red-600 font-medium">Action urgente requise</span></span>
                                </div>
                                <div className="flex items-center gap-3" title="Non payé - Échéance dans ≤ 10 jours - Paiement imminent">
                                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 border-2 border-orange-500 animate-pulse">
                                    <span className="text-xs font-bold text-orange-700">7j</span>
                                  </div>
                                  <span className="text-sm">Échéance dans ≤ 10 jours - <span className="text-orange-600 font-medium">Attention, paiement imminent</span></span>
                                </div>
                                <div className="flex items-center gap-3" title="Non payé - Échéance lointaine - En attente">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 border-2 border-gray-400">
                                    <Clock className="h-4 w-4 text-gray-500" />
                                  </div>
                                  <span className="text-sm">Pas de paiement, échéance lointaine - <span className="text-gray-500">En attente</span></span>
                                </div>
                              </div>
                            </div>

                            {/* Partial Payment Section */}
                            <div className="border rounded-lg p-4 bg-orange-50">
                              <h4 className="font-semibold mb-3 text-orange-700">Paiement partiel</h4>
                              <div className="space-y-2">
                                <div className="flex items-center gap-3" title="Paiement partiel - Échéance dépassée - Pénalités applicables">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500 animate-pulse">
                                    <X className="h-5 w-5 text-red-600" />
                                  </div>
                                  <span className="text-sm">Échéance dépassée avec paiement partiel - <span className="text-red-600 font-medium">Pénalités applicables</span></span>
                                </div>
                                <div className="flex items-center gap-3" title="Paiement partiel - Échéance dans ≤ 10 jours - Compléter le paiement">
                                  <div className="flex items-center justify-center w-10 h-10 rounded-full bg-orange-100 border-2 border-orange-500 animate-pulse">
                                    <span className="text-xs font-bold text-orange-700">5j</span>
                                  </div>
                                  <span className="text-sm">Échéance dans ≤ 10 jours, paiement partiel - <span className="text-orange-600 font-medium">Compléter le paiement</span></span>
                                </div>
                              </div>
                            </div>

                            {/* Full Payment Section */}
                            <div className="border rounded-lg p-4 bg-green-50">
                              <h4 className="font-semibold mb-3 text-green-700">Paiement complet</h4>
                              <div className="space-y-2">
                                <div className="flex items-center gap-3" title="Paiement complet - Facture payée intégralement">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-green-100 border-2 border-green-500">
                                    <Check className="h-5 w-5 text-green-600" />
                                  </div>
                                  <span className="text-sm">Payé à temps - <span className="text-green-600 font-medium">Conforme</span></span>
                                </div>
                                <div className="flex items-center gap-3" title="Paiement complet - Payé en retard - Pénalités de retard applicables">
                                  <div className="flex items-center justify-center w-8 h-8 rounded-full bg-red-100 border-2 border-red-500">
                                    <Check className="h-5 w-5 text-red-600" />
                                  </div>
                                  <span className="text-sm">Payé en retard - <span className="text-red-600 font-medium">Pénalités de retard applicables</span></span>
                                </div>
                              </div>
                            </div>
                          </div>
                        </DialogContent>
                      </Dialog>
                    </TableHead>
                    <TableHead>Création</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredDrafts.map((draft) => (
                    <TableRow 
                      key={draft.id}
                      className="cursor-pointer hover:bg-muted/50"
                      onClick={() => navigate(`/drafts/${draft.id}/review`)}
                    >
                      <TableCell className="font-medium">
                        {draft.data.supplier_name || (
                          <span className="text-muted-foreground italic">Non renseigné</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {draft.data.invoice_number || "-"}
                      </TableCell>
                      <TableCell>
                        {draft.data.invoice_amount_ttc 
                          ? `${draft.data.invoice_amount_ttc.toLocaleString('fr-MA')} MAD`
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.payment_amount_paid > 0
                          ? `${draft.data.payment_amount_paid.toLocaleString('fr-MA')} MAD`
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {(() => {
                          const total = draft.data.invoice_amount_ttc || 0;
                          const paid = draft.data.payment_amount_paid || 0;
                          const unpaid = Math.max(0, total - paid);
                          return unpaid > 0 ? `${unpaid.toLocaleString('fr-MA')} MAD` : "-";
                        })()}
                      </TableCell>
                      <TableCell>
                        {draft.data.penalty_amount > 0
                          ? `${draft.data.penalty_amount.toLocaleString('fr-MA')} MAD`
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.payment_date
                          ? (() => {
                              try {
                                const date = draft.data.payment_date?.includes('/') 
                                  ? new Date(draft.data.payment_date.split('/').reverse().join('-'))
                                  : new Date(draft.data.payment_date);
                                return format(date, 'dd/MM/yyyy', { locale: fr });
                              } catch { return draft.data.payment_date; }
                            })()
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {draft.data.legal_due_date 
                          ? (() => {
                              try {
                                const date = draft.data.legal_due_date?.includes('/') 
                                  ? new Date(draft.data.legal_due_date.split('/').reverse().join('-'))
                                  : new Date(draft.data.legal_due_date);
                                return format(date, 'dd/MM/yyyy', { locale: fr });
                              } catch { return draft.data.legal_due_date; }
                            })()
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        {(draft.data.invoice_delivery_date || draft.data.delivery_date)
                          ? (() => {
                              const dateValue = draft.data.invoice_delivery_date || draft.data.delivery_date;
                              try {
                                const date = dateValue?.includes('/') 
                                  ? new Date(dateValue.split('/').reverse().join('-'))
                                  : new Date(dateValue!);
                                return format(date, 'dd/MM/yyyy', { locale: fr });
                              } catch { return dateValue; }
                            })()
                          : "-"
                        }
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusConfig[draft.status].variant}>
                          {statusConfig[draft.status].label}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-center">
                        <div className="flex justify-center">
                          <PaymentStatusIndicator draft={draft} />
                        </div>
                      </TableCell>
                      <TableCell>
                        {draft.created_at 
                          ? (() => {
                              try {
                                const date = draft.created_at?.includes('/') 
                                  ? new Date(draft.created_at.split('/').reverse().join('-'))
                                  : new Date(draft.created_at);
                                return format(date, 'dd/MM/yyyy', { locale: fr });
                              } catch { return draft.created_at; }
                            })()
                          : "-"
                        }
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          {draft.invoice_file_url && (
                            <Button 
                              variant="ghost" 
                              size="icon"
                              className="h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation();
                                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                                window.open(`${apiUrl}${draft.invoice_file_url}`, '_blank');
                              }}
                              title="Voir facture"
                            >
                              <FileText className="h-4 w-4 text-blue-600" />
                            </Button>
                          )}
                          {draft.bank_statement_file_url && (
                            <Button 
                              variant="ghost" 
                              size="icon"
                              className="h-8 w-8"
                              onClick={(e) => {
                                e.stopPropagation();
                                const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
                                window.open(`${apiUrl}${draft.bank_statement_file_url}`, '_blank');
                              }}
                              title="Voir relevé bancaire"
                            >
                              <svg className="h-4 w-4 text-green-600" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <rect x="2" y="5" width="20" height="14" rx="2"/>
                                <line x1="2" y1="10" x2="22" y2="10"/>
                              </svg>
                            </Button>
                          )}
                          <Button 
                            variant="ghost" 
                            size="icon"
                            className="h-8 w-8"
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate(`/drafts/${draft.id}/review`);
                            }}
                            title="Modifier"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="icon"
                            className="h-8 w-8"
                            onClick={(e) => handleDeleteClick(draft, e)}
                            disabled={deleteMutation.isPending}
                            title="Supprimer"
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          ) : (
            <div className="text-center py-12">
              <FileText className="h-12 w-12 mx-auto text-muted-foreground/50 mb-4" />
              <p className="text-muted-foreground">
                {searchQuery 
                  ? "Aucun brouillon ne correspond à votre recherche"
                  : "Aucun brouillon pour le moment"
                }
              </p>
              {!searchQuery && (
                <Link to="/drafts/new">
                  <Button className="mt-4">
                    <Plus className="h-4 w-4 mr-2" />
                    Créer un brouillon
                  </Button>
                </Link>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Confirmer la suppression</AlertDialogTitle>
            <AlertDialogDescription>
              Êtes-vous sûr de vouloir supprimer le brouillon{" "}
              <strong>{draftToDelete?.data.invoice_number || "sans numéro"}</strong> ?
              Cette action est irréversible.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleteMutation.isPending}>
              Annuler
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {deleteMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Suppression...
                </>
              ) : (
                "Supprimer"
              )}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
