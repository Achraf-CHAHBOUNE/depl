from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date
from enum import Enum
from .alerts import Alert


class LegalStatus(str, Enum):
    """Legal status affecting penalty calculation"""
    NORMAL = "NORMAL"
    DISPUTED = "DISPUTED"  # Litige judiciaire
    CREDIT_NOTE = "CREDIT_NOTE"  # Avoir
    PROCEDURE_690 = "PROCEDURE_690"  # Sauvegarde/redressement/liquidation
    

class LegalResult(BaseModel):
    """
    Complete legal computation result for a single invoice.
    
    This schema contains all DGI-required calculations:
    - Legal dates and delays
    - Penalty amounts
    - Compliance status
    - Audit trail
    """
    
    # Reference
    invoice_id: str
    
    # Legal dates (Article 78-2)
    legal_start_date: Optional[date] = Field(
        None,
        description="Date de référence légale (livraison ou facture)"
    )
    legal_due_date: Optional[date] = Field(
        None,
        description="Date limite de paiement calculée"
    )
    
    # Delays
    contractual_delay_days: Optional[int] = Field(
        None,
        description="Délai contractuel en jours (si stipulé)"
    )
    applied_legal_delay_days: int = Field(
        60,
        description="Délai légal appliqué (60 par défaut, ou min(contractuel, 120))"
    )
    
    # Payment tracking
    actual_payment_date: Optional[date] = Field(
        None,
        description="Date de paiement effectif"
    )
    days_overdue: int = Field(
        0,
        description="Nombre de jours de retard"
    )
    months_of_delay: int = Field(
        0,
        description="Nombre de mois de retard (tout mois entamé compte)"
    )
    
    # Penalty calculation (Article 78-3)
    penalty_rate: float = Field(
        0.0,
        description="Taux de pénalité applicable (%)"
    )
    penalty_amount: float = Field(
        0.0,
        description="Montant de l'amende pécuniaire (MAD)"
    )
    penalty_suspended: bool = Field(
        False,
        description="Pénalité suspendue (litige ou procédure 690)"
    )
    
    # Legal status
    legal_status: LegalStatus = Field(
        LegalStatus.NORMAL,
        description="Statut juridique de la facture"
    )
    
    # Amounts
    invoice_amount_ttc: float = Field(
        0.0,
        description="Montant TTC de la facture"
    )
    paid_amount: float = Field(
        0.0,
        description="Montant payé"
    )
    unpaid_amount: float = Field(
        0.0,
        description="Montant impayé (base de calcul des pénalités)"
    )
    
    # Alerts and audit
    alerts: List[Alert] = Field(
        default_factory=list,
        description="Alertes de conformité et qualité"
    )
    computation_notes: List[str] = Field(
        default_factory=list,
        description="Notes explicatives des calculs"
    )
    calculation_breakdown: Optional[Dict[str, Any]] = Field(
        None,
        description="Détails structurés du calcul des pénalités pour affichage frontend"
    )
    
    # Validation
    requires_manual_review: bool = Field(
        False,
        description="Nécessite une validation manuelle"
    )
    
    class Config:
        use_enum_values = True