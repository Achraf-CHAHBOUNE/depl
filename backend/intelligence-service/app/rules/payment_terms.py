from datetime import date, timedelta
from typing import Optional, Tuple, List
import logging

from ..schemas.invoice import InvoiceStruct
from ..schemas.alerts import Alert, AlertCode, AlertSeverity
from .holiday_calendar import MoroccanHolidayCalendar

logger = logging.getLogger(__name__)


class PaymentTermsEngine:
    """
    Compute legal payment terms according to Moroccan DGI regulations.
    
    Legal framework:
    - Article 78-2, Loi 15-95 (modified by Loi 69-21)
    - Default legal delay: 60 days
    - Maximum contractual delay: 120 days
    - Start date: delivery_date OR issue_date (with alert)
    """
    
    # Legal constants
    DEFAULT_LEGAL_DELAY_DAYS = 60
    MAX_CONTRACTUAL_DELAY_DAYS = 120
    
    def __init__(self, calendar: MoroccanHolidayCalendar = None):
        """
        Args:
            calendar: Holiday calendar for business day calculations
        """
        self.calendar = calendar or MoroccanHolidayCalendar()
    
    def compute_legal_start_date(
        self,
        invoice: InvoiceStruct
    ) -> Tuple[Optional[date], List[Alert]]:
        """
        Determine legal start date for payment delay calculation.
        
        Hierarchy (Article 78-2):
        1. delivery_date (preferred)
        2. issue_date (fallback with WARNING)
        
        Args:
            invoice: Invoice structure
        
        Returns:
            (legal_start_date, alerts)
        """
        alerts = []
        
        # Priority 1: Delivery date
        if invoice.invoice.delivery_date:
            logger.info(
                f"Invoice {invoice.invoice_id}: Using delivery_date "
                f"as legal start: {invoice.invoice.delivery_date}"
            )
            return invoice.invoice.delivery_date, alerts
        
        # Priority 2: Issue date (with alert)
        if invoice.invoice.issue_date:
            alerts.append(Alert(
                code=AlertCode.MISSING_DELIVERY_DATE,
                severity=AlertSeverity.WARNING,
                message=(
                    "Date de livraison manquante. "
                    "Utilisation de la date de facture par défaut. "
                    "Vérification manuelle recommandée."
                ),
                field="invoice.delivery_date"
            ))
            
            logger.warning(
                f"Invoice {invoice.invoice_id}: Missing delivery_date, "
                f"using issue_date: {invoice.invoice.issue_date}"
            )
            
            return invoice.invoice.issue_date, alerts
        
        # No date available - CRITICAL
        alerts.append(Alert(
            code=AlertCode.MISSING_ISSUE_DATE,
            severity=AlertSeverity.CRITICAL,
            message=(
                "Aucune date disponible (livraison ni facture). "
                "Calcul de délai impossible. Correction requise."
            ),
            field="invoice.issue_date"
        ))
        
        logger.error(
            f"Invoice {invoice.invoice_id}: No date available for delay calculation"
        )
        
        return None, alerts
    
    def compute_applied_delay(
        self,
        contractual_delay_days: Optional[int] = None
    ) -> Tuple[int, List[Alert], List[str]]:
        """
        Compute the legal delay to apply.
        
        Rules:
        - No contractual delay → 60 days (default)
        - Contractual delay ≤ 120 → use contractual
        - Contractual delay > 120 → cap to 120 (with alert)
        
        Args:
            contractual_delay_days: Contractual delay if specified
        
        Returns:
            (applied_delay_days, alerts, computation_notes)
        """
        alerts = []
        notes = []
        
        # No contractual agreement (None or 0 means use default legal delay)
        if contractual_delay_days is None or contractual_delay_days == 0:
            notes.append(
                f"Aucun délai contractuel stipulé. "
                f"Application du délai légal par défaut: {self.DEFAULT_LEGAL_DELAY_DAYS} jours."
            )
            return self.DEFAULT_LEGAL_DELAY_DAYS, alerts, notes
        
        # Contractual delay within legal limit
        if contractual_delay_days <= self.MAX_CONTRACTUAL_DELAY_DAYS:
            notes.append(
                f"Délai contractuel appliqué: {contractual_delay_days} jours "
                f"(≤ maximum légal de {self.MAX_CONTRACTUAL_DELAY_DAYS} jours)."
            )
            return contractual_delay_days, alerts, notes
        
        # Contractual delay exceeds maximum - cap it
        alerts.append(Alert(
            code=AlertCode.CONTRACTUAL_DELAY_EXCEEDS_MAX,
            severity=AlertSeverity.WARNING,
            message=(
                f"Délai contractuel ({contractual_delay_days} jours) "
                f"dépasse le maximum légal ({self.MAX_CONTRACTUAL_DELAY_DAYS} jours). "
                f"Application du plafond légal."
            ),
            field="contractual_delay_days"
        ))
        
        notes.append(
            f"Délai contractuel demandé: {contractual_delay_days} jours. "
            f"Plafonné au maximum légal: {self.MAX_CONTRACTUAL_DELAY_DAYS} jours."
        )
        
        logger.warning(
            f"Contractual delay {contractual_delay_days} exceeds max, "
            f"capped to {self.MAX_CONTRACTUAL_DELAY_DAYS}"
        )
        
        return self.MAX_CONTRACTUAL_DELAY_DAYS, alerts, notes
    
    def compute_due_date(
        self,
        legal_start_date: date,
        delay_days: int
    ) -> Tuple[date, List[str]]:
        """
        Compute legal due date.
        
        Rules:
        - due_date = legal_start_date + delay_days
        - If falls on weekend/holiday → shift to next business day
        
        Args:
            legal_start_date: Legal reference date
            delay_days: Number of days delay
        
        Returns:
            (due_date, computation_notes)
        """
        notes = []
        
        # Calculate raw due date
        raw_due_date = legal_start_date + timedelta(days=delay_days)
        
        # Adjust for business days
        adjusted_due_date = self.calendar.next_business_day(raw_due_date)
        
        if adjusted_due_date != raw_due_date:
            notes.append(
                f"Date d'échéance ajustée: {raw_due_date} (weekend/férié) "
                f"→ {adjusted_due_date} (jour ouvrable suivant)."
            )
            logger.info(
                f"Due date adjusted from {raw_due_date} to {adjusted_due_date} "
                "(weekend/holiday)"
            )
        else:
            notes.append(
                f"Date d'échéance calculée: {adjusted_due_date} "
                f"({legal_start_date} + {delay_days} jours)."
            )
        
        return adjusted_due_date, notes
    
    def compute_days_overdue(
        self,
        due_date: date,
        payment_date: Optional[date]
    ) -> Tuple[int, List[Alert]]:
        """
        Compute number of days overdue.
        
        Args:
            due_date: Legal due date
            payment_date: Actual payment date (None if unpaid)
        
        Returns:
            (days_overdue, alerts)
        """
        alerts = []
        
        # Not yet paid
        if payment_date is None:
            # Calculate delay from today
            today = date.today()
            if today > due_date:
                days_overdue = (today - due_date).days
                
                if days_overdue > 180:
                    alerts.append(Alert(
                        code=AlertCode.EXCESSIVE_DELAY,
                        severity=AlertSeverity.ERROR,
                        message=(
                            f"Retard excessif: {days_overdue} jours. "
                            "Vérification urgente recommandée."
                        ),
                        field="payment_date"
                    ))
                
                return days_overdue, alerts
            else:
                return 0, alerts
        
        # Paid - check if late
        if payment_date <= due_date:
            return 0, alerts
        
        days_overdue = (payment_date - due_date).days
        
        if days_overdue > 180:
            alerts.append(Alert(
                code=AlertCode.EXCESSIVE_DELAY,
                severity=AlertSeverity.WARNING,
                message=f"Retard de paiement important: {days_overdue} jours.",
                field="payment_date"
            ))
        
        return days_overdue, alerts