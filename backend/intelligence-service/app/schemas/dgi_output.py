from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date


class DGIInvoiceLine(BaseModel):
    """
    Represents one line in the DGI payment delay declaration.
    Matches the official Moroccan DGI form structure with legal computations.
    """
    # Supplier info
    supplier_name: Optional[str] = None
    supplier_ice: Optional[str] = None
    
    # Invoice details
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    invoice_amount_ttc: Optional[float] = None
    
    # Legal dates (NEW)
    legal_start_date: Optional[date] = Field(
        None,
        description="Date de référence légale (livraison ou facture)"
    )
    legal_due_date: Optional[date] = Field(
        None,
        description="Date limite de paiement légale"
    )
    
    # Payment info
    payment_date: Optional[date] = None
    payment_amount: Optional[float] = None
    
    # Delays (NEW - now computed)
    contractual_payment_delay: Optional[int] = Field(
        None,
        description="Délai contractuel en jours"
    )
    applied_legal_delay: int = Field(
        60,
        description="Délai légal appliqué en jours"
    )
    actual_payment_delay: int = Field(
        0,
        description="Retard réel en jours"
    )
    months_of_delay: int = Field(
        0,
        description="Nombre de mois de retard"
    )
    
    # Penalty (NEW - Article 78-3)
    penalty_rate: float = Field(
        0.0,
        description="Taux de pénalité (%)"
    )
    penalty_amount: float = Field(
        0.0,
        description="Montant de l'amende pécuniaire (MAD)"
    )
    penalty_suspended: bool = Field(
        False,
        description="Pénalité suspendue (litige/procédure)"
    )
    
    # Status
    payment_status: str = "UNPAID"
    legal_status: str = "NORMAL"
    remarks: Optional[str] = None
    
    # Quality flags (NEW)
    requires_manual_review: bool = Field(
        False,
        description="Nécessite validation manuelle"
    )
    alert_count: int = Field(
        0,
        description="Nombre d'alertes"
    )


class DGIDeclaration(BaseModel):
    """
    Complete DGI declaration output with legal computations.
    """
    # Company identification
    company_ice: Optional[str] = None
    company_name: Optional[str] = None
    company_rc: Optional[str] = None
    
    # Declaration period
    declaration_year: int
    declaration_month: Optional[int] = None
    
    # Activity sector
    activity_sector: Optional[str] = None
    
    # Invoice lines
    invoices: List[DGIInvoiceLine] = []
    
    # Totals - Financial
    total_invoices: int = 0
    total_amount_invoiced: float = 0.0
    total_amount_paid: float = 0.0
    total_amount_unpaid: float = 0.0
    
    # Totals - Penalties (NEW)
    total_penalty_amount: float = Field(
        0.0,
        description="Montant total des pénalités (MAD)"
    )
    total_penalty_suspended: float = Field(
        0.0,
        description="Montant total des pénalités suspendues (MAD)"
    )
    
    # Quality metrics (NEW)
    invoices_requiring_review: int = Field(
        0,
        description="Nombre de factures nécessitant validation"
    )
    total_alerts: int = Field(
        0,
        description="Nombre total d'alertes"
    )
    
    # Compliance summary (NEW)
    invoices_on_time: int = Field(
        0,
        description="Nombre de factures payées dans les délais"
    )
    invoices_delayed: int = Field(
        0,
        description="Nombre de factures payées en retard"
    )
    invoices_unpaid: int = Field(
        0,
        description="Nombre de factures impayées"
    )