from typing import Tuple, List, Optional
import logging

from ..schemas.invoice import InvoiceStruct
from ..schemas.legal_result import LegalStatus
from ..schemas.alerts import Alert, AlertCode, AlertSeverity

logger = logging.getLogger(__name__)


class StatusEngine:
    """
    Determine legal status and apply special rules.
    
    Legal special cases:
    1. DISPUTED: Invoice under legal dispute (litige judiciaire)
       → Penalty calculation SUSPENDED
    2. CREDIT_NOTE: Negative invoice (avoir)
       → No penalty
    3. PROCEDURE_690: Company under safeguard/recovery/liquidation
       → Payment forbidden, penalty blocked
    """
    
    def __init__(self):
        """Initialize status engine"""
        pass
    
    def determine_legal_status(
        self,
        invoice: InvoiceStruct,
        is_disputed: bool = False,
        is_credit_note: bool = False,
        is_procedure_690: bool = False
    ) -> Tuple[LegalStatus, List[Alert], List[str]]:
        """
        Determine the legal status of an invoice.
        
        Args:
            invoice: Invoice structure
            is_disputed: Invoice is under legal dispute
            is_credit_note: Invoice is a credit note (avoir)
            is_procedure_690: Supplier is under Article 690 procedure
        
        Returns:
            (legal_status, alerts, computation_notes)
        """
        alerts = []
        notes = []
        
        # Check for credit note (negative amount)
        invoice_amount = invoice.amounts.total_ttc or 0
        if invoice_amount < 0 or is_credit_note:
            alerts.append(Alert(
                code=AlertCode.CREDIT_NOTE,
                severity=AlertSeverity.INFO,
                message="Avoir (credit note). Pas de pénalité applicable.",
                field="amounts.total_ttc"
            ))
            notes.append(
                "Statut: AVOIR - Montant négatif. "
                "Aucune pénalité de retard applicable."
            )
            logger.info(f"Invoice {invoice.invoice_id}: CREDIT_NOTE detected")
            return LegalStatus.CREDIT_NOTE, alerts, notes
        
        # Check for procedure 690
        if is_procedure_690:
            alerts.append(Alert(
                code=AlertCode.PROCEDURE_690,
                severity=AlertSeverity.WARNING,
                message=(
                    "Fournisseur sous procédure Article 690 "
                    "(sauvegarde/redressement/liquidation). "
                    "Paiement interdit. Pénalité bloquée."
                ),
                field="legal_status"
            ))
            notes.append(
                "Statut: PROCÉDURE 690 - "
                "Paiement interdit selon procédure collective. "
                "Calcul de pénalité suspendu."
            )
            logger.warning(
                f"Invoice {invoice.invoice_id}: PROCEDURE_690 status applied"
            )
            return LegalStatus.PROCEDURE_690, alerts, notes
        
        # Check for disputed invoice
        if is_disputed:
            alerts.append(Alert(
                code=AlertCode.DISPUTED_INVOICE,
                severity=AlertSeverity.WARNING,
                message=(
                    "Facture contestée (litige judiciaire). "
                    "Calcul de pénalité suspendu jusqu'à décision de justice."
                ),
                field="legal_status"
            ))
            notes.append(
                "Statut: LITIGE - "
                "Facture sous contentieux juridique. "
                "Pénalité suspendue jusqu'à jugement définitif."
            )
            logger.warning(
                f"Invoice {invoice.invoice_id}: DISPUTED status applied"
            )
            return LegalStatus.DISPUTED, alerts, notes
        
        # Normal status
        notes.append("Statut: NORMAL - Facture standard sans statut juridique particulier.")
        return LegalStatus.NORMAL, alerts, notes
    
    def apply_status_rules(
        self,
        legal_status: LegalStatus,
        base_penalty_amount: float
    ) -> Tuple[float, bool, List[str]]:
        """
        Apply penalty adjustments based on legal status.
        
        Args:
            legal_status: Legal status of invoice
            base_penalty_amount: Calculated penalty before status adjustments
        
        Returns:
            (final_penalty_amount, penalty_suspended, notes)
        """
        notes = []
        
        # Credit note: no penalty
        if legal_status == LegalStatus.CREDIT_NOTE:
            notes.append(
                "Application statut AVOIR: "
                "Pénalité annulée (0.00 MAD). "
                "Les avoirs ne sont pas soumis aux pénalités de retard."
            )
            return 0.0, False, notes
        
        # Procedure 690: penalty blocked
        if legal_status == LegalStatus.PROCEDURE_690:
            notes.append(
                "Application statut PROCÉDURE 690: "
                f"Pénalité suspendue ({base_penalty_amount:.2f} MAD calculée mais non appliquée). "
                "Pénalité bloquée pendant toute la durée de la procédure collective."
            )
            return 0.0, True, notes
        
        # Disputed: penalty suspended
        if legal_status == LegalStatus.DISPUTED:
            notes.append(
                "Application statut LITIGE: "
                f"Pénalité suspendue ({base_penalty_amount:.2f} MAD calculée mais non appliquée). "
                "Application rétroactive après décision de justice définitive."
            )
            return 0.0, True, notes
        
        # Normal: apply penalty as calculated
        notes.append(
            f"Application statut NORMAL: "
            f"Pénalité applicable = {base_penalty_amount:.2f} MAD."
        )
        return base_penalty_amount, False, notes
    
    def check_payment_validity(
        self,
        invoice: InvoiceStruct,
        payment_date: Optional[object]
    ) -> List[Alert]:
        """
        Validate payment coherence.
        
        Checks:
        - Payment date should be after invoice date
        
        Args:
            invoice: Invoice structure
            payment_date: Payment date (or None)
        
        Returns:
            List of validation alerts
        """
        alerts = []
        
        if not payment_date:
            return alerts
        
        # Import here to avoid circular dependency
        from datetime import datetime
        
        # Convert if needed
        if isinstance(payment_date, str):
            payment_date = datetime.fromisoformat(payment_date).date()
        
        invoice_date = invoice.invoice.issue_date
        if isinstance(invoice_date, str):
            invoice_date = datetime.fromisoformat(invoice_date).date()
        
        # Check if payment is before invoice
        if invoice_date and payment_date < invoice_date:
            alerts.append(Alert(
                code=AlertCode.PAYMENT_BEFORE_INVOICE,
                severity=AlertSeverity.ERROR,
                message=(
                    f"Incohérence temporelle: "
                    f"Paiement ({payment_date}) avant émission de facture ({invoice_date}). "
                    "Vérification manuelle requise."
                ),
                field="payment_date"
            ))
            logger.error(
                f"Invoice {invoice.invoice_id}: "
                f"Payment date {payment_date} before invoice date {invoice_date}"
            )
        
        return alerts