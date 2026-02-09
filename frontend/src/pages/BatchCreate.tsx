import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { batchAPI, settingsAPI } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/hooks/use-toast";
import { ArrowLeft, Building, FolderPlus, Loader2 } from "lucide-react";

export default function BatchCreate() {
  const navigate = useNavigate();
  const { user } = useAuth();
  
  const [formData, setFormData] = useState({
    company_name: "",
    company_ice: "",
    company_rc: "",
  });

  // Fetch company settings to pre-fill
  const { data: company } = useQuery({
    queryKey: ["company-settings"],
    queryFn: settingsAPI.getCompany,
  });

  // Pre-fill form when company data loads
  useState(() => {
    if (company) {
      setFormData({
        company_name: company.name || "",
        company_ice: company.ice || "",
        company_rc: company.rc || "",
      });
    }
  });

  const createMutation = useMutation({
    mutationFn: batchAPI.create,
    onSuccess: (batch) => {
      toast({
        title: "Lot créé",
        description: "Vous pouvez maintenant télécharger vos documents.",
      });
      navigate(`/batches/${batch.batch_id}/upload`);
    },
    onError: (error: any) => {
      toast({
        title: "Erreur",
        description: error.response?.data?.detail || "Impossible de créer le lot",
        variant: "destructive",
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.company_name || !formData.company_ice) {
      toast({
        title: "Champs requis",
        description: "Veuillez remplir le nom et l'ICE de l'entreprise.",
        variant: "destructive",
      });
      return;
    }

    createMutation.mutate({
      company_name: formData.company_name,
      company_ice: formData.company_ice,
      company_rc: formData.company_rc || undefined,
    });
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/dashboard")}>
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold text-foreground">Nouveau Lot</h1>
          <p className="text-muted-foreground">Créer un nouveau lot de factures à traiter</p>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="h-5 w-5" />
            Informations de l'entreprise
          </CardTitle>
          <CardDescription>
            Ces informations seront utilisées pour la déclaration DGI
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="company_name">
                Nom de l'entreprise <span className="text-destructive">*</span>
              </Label>
              <Input
                id="company_name"
                value={formData.company_name}
                onChange={(e) => setFormData(prev => ({ ...prev, company_name: e.target.value }))}
                placeholder="Votre Entreprise SARL"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="company_ice">
                  ICE <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="company_ice"
                  value={formData.company_ice}
                  onChange={(e) => setFormData(prev => ({ ...prev, company_ice: e.target.value }))}
                  placeholder="000000000000000"
                  maxLength={15}
                />
                <p className="text-xs text-muted-foreground">15 caractères</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="company_rc">RC</Label>
                <Input
                  id="company_rc"
                  value={formData.company_rc}
                  onChange={(e) => setFormData(prev => ({ ...prev, company_rc: e.target.value }))}
                  placeholder="RC12345"
                />
              </div>
            </div>

            <div className="pt-4 flex gap-3">
              <Button
                type="submit"
                disabled={createMutation.isPending}
                className="flex-1"
              >
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <FolderPlus className="h-4 w-4 mr-2" />
                )}
                Créer le lot
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => navigate("/dashboard")}
              >
                Annuler
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-info/5 border-info/20">
        <CardContent className="pt-6">
          <h4 className="font-medium text-foreground mb-2">Processus de traitement</h4>
          <ol className="list-decimal list-inside space-y-1 text-sm text-muted-foreground">
            <li>Créez un lot avec les informations de votre entreprise</li>
            <li>Téléchargez vos factures et relevés de paiement (PDF)</li>
            <li>Le système effectue l'OCR et l'extraction automatique</li>
            <li>Validez les données et corrigez si nécessaire</li>
            <li>Exportez le fichier CSV pour la déclaration DGI</li>
          </ol>
        </CardContent>
      </Card>
    </div>
  );
}
