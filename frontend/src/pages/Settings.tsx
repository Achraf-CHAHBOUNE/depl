import { useQuery } from "@tanstack/react-query";
import { settingsAPI } from "@/lib/api";
import { CompanySettings, RulesConfig, Holiday } from "@/types";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Building, Scale, Calendar, Loader2 } from "lucide-react";
import { format } from "date-fns";

export default function Settings() {
  const { data: company, isLoading: loadingCompany } = useQuery<CompanySettings>({
    queryKey: ["company"],
    queryFn: settingsAPI.getCompany,
  });

  const { data: rules, isLoading: loadingRules } = useQuery<RulesConfig>({
    queryKey: ["rules"],
    queryFn: settingsAPI.getRulesConfig,
  });

  const { data: holidays, isLoading: loadingHolidays } = useQuery<Holiday[]>({
    queryKey: ["holidays"],
    queryFn: settingsAPI.getHolidays,
  });

  if (loadingCompany || loadingRules || loadingHolidays) {
    return <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-foreground">Paramètres</h1>
        <p className="text-muted-foreground">Gérer le profil de l'entreprise et la configuration du système</p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Building className="h-5 w-5" />Profil de l'Entreprise</CardTitle></CardHeader>
          <CardContent className="grid sm:grid-cols-2 gap-4">
            <div><Label>Nom de l'Entreprise</Label><Input value={company?.name || ""} readOnly /></div>
            <div><Label>ICE</Label><Input value={company?.ice || ""} readOnly /></div>
            <div><Label>RC</Label><Input value={company?.rc || ""} readOnly /></div>
            <div><Label>Adresse</Label><Input value={company?.address || ""} readOnly /></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Scale className="h-5 w-5" />Configuration des Règles</CardTitle></CardHeader>
          <CardContent className="grid sm:grid-cols-2 gap-4">
            <div><Label>Taux de Base des Pénalités</Label><Input value={`${(rules?.PENALTY_BASE_RATE || 0) * 100}%`} readOnly /></div>
            <div><Label>Incrément Mensuel</Label><Input value={`${(rules?.PENALTY_MONTHLY_INCREMENT || 0) * 100}%`} readOnly /></div>
            <div><Label>Tolérance de Montant</Label><Input value={`${(rules?.AMOUNT_TOLERANCE || 0) * 100}%`} readOnly /></div>
            <div><Label>Confiance Minimum</Label><Input value={`${rules?.MIN_CONFIDENCE_SCORE || 0}%`} readOnly /></div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center gap-2"><Calendar className="h-5 w-5" />Calendrier des Jours Fériés</CardTitle></CardHeader>
          <CardContent>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2">
              {holidays?.map((h) => (
                <div key={h.id} className="flex items-center justify-between p-2 border rounded text-sm">
                  <span>{h.name}</span>
                  <span className="text-muted-foreground">{format(new Date(h.date), "dd/MM")}</span>
                </div>
              ))}
              {(!holidays || holidays.length === 0) && (
                <p className="text-muted-foreground col-span-full text-center py-4">Aucun jour férié configuré</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
