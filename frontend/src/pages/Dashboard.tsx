import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { draftAPI, dashboardAPI } from "@/lib/api";
import { KpiCard } from "@/components/KpiCard";
import { StatusBadge } from "@/components/StatusBadge";
import { DashboardSkeleton } from "@/components/LoadingSkeletons";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { 
  FileText, 
  CheckCircle, 
  Download, 
  ArrowRight,
  Clock,
  Plus,
  FilePlus,
  ClipboardCheck,
  AlertCircle,
  RefreshCw
} from "lucide-react";
import { format } from "date-fns";
import { fr } from "date-fns/locale";

export default function Dashboard() {
  const { data: drafts, isLoading: loadingDrafts, error: draftsError, refetch: refetchDrafts } = useQuery({
    queryKey: ["drafts"],
    queryFn: draftAPI.list,
  });

  const { data: activity } = useQuery({
    queryKey: ["dashboard-activity"],
    queryFn: dashboardAPI.getActivity,
  });

  // Show skeleton while loading
  if (loadingDrafts) {
    return <DashboardSkeleton />;
  }

  // Show error state
  if (draftsError) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Tableau de bord</h1>
            <p className="text-muted-foreground">Gestion des brouillons de factures DGI</p>
          </div>
        </div>

        <Card>
          <CardContent className="py-12">
            <div className="text-center">
              <AlertCircle className="h-12 w-12 mx-auto text-destructive mb-4" />
              <h3 className="font-medium text-lg mb-2">Erreur de chargement</h3>
              <p className="text-sm text-muted-foreground mb-4">
                {draftsError instanceof Error ? draftsError.message : "Impossible de charger les données"}
              </p>
              <Button variant="outline" onClick={() => refetchDrafts()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Réessayer
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Calculate stats from drafts
  const stats = {
    totalDrafts: drafts?.length || 0,
    draftsPending: drafts?.filter(d => d.status === 'DRAFT').length || 0,
    draftsValidated: drafts?.filter(d => d.status === 'VALIDATED').length || 0,
    totalPenalties: drafts?.reduce((sum, d) => sum + (d.data.penalty_amount || 0), 0) || 0,
  };

  const recentDrafts = drafts?.slice(0, 5) || [];

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-foreground">Tableau de bord</h1>
          <p className="text-muted-foreground">Gestion des brouillons de factures DGI</p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/drafts/new">
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              Nouveau Brouillon
            </Button>
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          title="Total Brouillons"
          value={stats.totalDrafts}
          subtitle="Tous les brouillons"
          icon={FileText}
        />
        <KpiCard
          title="En attente"
          value={stats.draftsPending}
          subtitle="À réviser"
          icon={Clock}
        />
        <KpiCard
          title="Validés"
          value={stats.draftsValidated}
          subtitle="Dans le registre"
          icon={CheckCircle}
        />
        <KpiCard
          title="Total Pénalités"
          value={`${stats.totalPenalties.toLocaleString('fr-MA')} MAD`}
          subtitle="Montant calculé"
          icon={ClipboardCheck}
        />
      </div>

      {/* Quick Actions & Recent Drafts */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-lg">Actions rapides</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <Link to="/drafts/new" className="block">
              <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-3">
                  <FilePlus className="h-5 w-5 text-primary" />
                  <span className="font-medium text-foreground">Créer un nouveau brouillon</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Link>
            <Link to="/drafts" className="block">
              <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-3">
                  <FileText className="h-5 w-5 text-info" />
                  <span className="font-medium text-foreground">Voir mes brouillons</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Link>
            <Link to="/registre-dgi" className="block">
              <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                <div className="flex items-center gap-3">
                  <Download className="h-5 w-5 text-success" />
                  <span className="font-medium text-foreground">Exporter pour DGI</span>
                </div>
                <ArrowRight className="h-4 w-4 text-muted-foreground" />
              </div>
            </Link>
          </CardContent>
        </Card>

        {/* Recent Drafts */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-lg">Brouillons récents</CardTitle>
          </CardHeader>
          <CardContent>
            {recentDrafts.length > 0 ? (
              <div className="space-y-4">
                {recentDrafts.map((draft) => (
                  <Link key={draft.id} to={`/drafts/${draft.id}/review`} className="block">
                    <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-foreground truncate">
                            {draft.data.supplier_name || 'Fournisseur non renseigné'}
                          </p>
                          <StatusBadge status={draft.status === 'VALIDATED' ? 'validated' : 'validation_pending'} />
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                          <span>{draft.data.invoice_number || '-'}</span>
                          <span>•</span>
                          <span>{draft.data.invoice_amount_ttc?.toLocaleString('fr-MA') || '0'} MAD</span>
                          <span>•</span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {format(new Date(draft.created_at), 'dd MMM, HH:mm', { locale: fr })}
                          </span>
                        </div>
                      </div>
                      {draft.alerts.length > 0 && (
                        <span className="text-xs bg-warning/10 text-warning px-2 py-0.5 rounded">
                          {draft.alerts.length} alertes
                        </span>
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            ) : (
              <div className="text-center py-12">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="font-medium text-foreground mb-1">Aucun brouillon</p>
                <p className="text-sm text-muted-foreground mb-4">
                  Créez votre premier brouillon pour commencer.
                </p>
                <Link to="/drafts/new">
                  <Button variant="outline" size="sm">
                    <Plus className="h-4 w-4 mr-2" />
                    Créer un brouillon
                  </Button>
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
