from typing import Optional, List
from datetime import date
import logging

from ..schemas.invoice import InvoiceStruct
from ..schemas.matching import MatchingResult
from ..schemas.legal_result import LegalResult, LegalStatus
from ..schemas.alerts import Alert, AlertCode, AlertSeverity
from ..rules.payment_terms import PaymentTermsEngine
from ..rules.penalties import PenaltyEngine
from ..rules.status import StatusEngine
from ..rules.holiday_calendar import MoroccanHolidayCalendar

logger = logging.getLogger(__name__)


class RulesComputationService:
    """
    Complete DGI rules engine orchestration.
    
    Combines:
    - Payment terms calculation (Article 78-2)
    - Penalty calculation (Article 78-3)
    - Legal status handling
    - Alert generation
    
    CRITICAL: Uses DGI-compliant calendar month calculation for penalties.
    """
    
    def __init__(
        self,
        calendar: MoroccanHolidayCalendar = None,
        penalty_base_rate: float = 2.25,
        penalty_monthly_increment: float = 0.85
    ):
        """
        Initialize rules computation service.
        
        Args:
            calendar: Holiday calendar for business day calculations
            penalty_base_rate: Base penalty rate (%) for 1st month (default: 2.25%)
            penalty_monthly_increment: Additional rate (%) per month (default: 0.85%)
        """
        self.calendar = calendar or MoroccanHolidayCalendar()
        self.payment_terms_engine = PaymentTermsEngine(calendar=self.calendar)
        self.penalty_engine = PenaltyEngine(
            base_rate_percent=penalty_base_rate,
            monthly_increment_percent=penalty_monthly_increment
        )
        self.status_engine = StatusEngine()
        
        logger.info(
            f"RulesComputationService initialized: "
            f"base_rate={penalty_base_rate}%, increment={penalty_monthly_increment}%"
        )
    
    def compute_legal_result(
        self,
        invoice: InvoiceStruct,
        matching_result: MatchingResult,
        contractual_delay_days: Optional[int] = None,
        is_disputed: bool = False,
        is_credit_note: bool = False,
        is_procedure_690: bool = False
    ) -> LegalResult:
        """
        Complete legal computation for a single invoice.
        
        This is the main entry point for DGI compliance calculation.
        
        COMPUTATION PIPELINE:
        1. Determine legal status (normal/disputed/credit/procedure 690)
        2. Compute legal start date (delivery_date or issue_date)
        3. Compute applied legal delay (60 days default, max 120 contractual)
        4. Compute legal due date (start + delay, adjusted for weekends)
        5. Get payment information from matching
        6. Compute days overdue (calendar days)
        7. Compute months of delay (DGI calendar month logic)
        8. Compute penalty rate and amount
        9. Apply legal status adjustments (suspend if disputed/procedure 690)
        10. Generate alerts and validation flags
        
        Args:
            invoice: Invoice structure from extraction
            matching_result: Matching result from intelligent matcher
            contractual_delay_days: Contractual payment delay if specified
            is_disputed: Invoice under legal dispute (Article 78-3)
            is_credit_note: Invoice is a credit note (avoir)
            is_procedure_690: Supplier under Article 690 procedure
        
        Returns:
            Complete LegalResult with all DGI-required fields
        """
        all_alerts = []
        all_notes = []
        
        logger.info(f"Computing legal result for invoice {invoice.invoice_id}")
        
        # ========================================================================
        # STEP 1: Determine legal status
        # ========================================================================
        legal_status, status_alerts, status_notes = self.status_engine.determine_legal_status(
            invoice=invoice,
            is_disputed=is_disputed,
            is_credit_note=is_credit_note,
            is_procedure_690=is_procedure_690
        )
        all_alerts.extend(status_alerts)
        all_notes.extend(status_notes)
        
        logger.info(f"Invoice {invoice.invoice_id}: Legal status = {legal_status.value}")
        
        # ========================================================================
        # STEP 2: Compute legal start date (Article 78-2)
        # ========================================================================
        legal_start_date, date_alerts = self.payment_terms_engine.compute_legal_start_date(
            invoice=invoice
        )
        all_alerts.extend(date_alerts)
        
        # If no legal start date, cannot continue computation
        if legal_start_date is None:
            logger.error(
                f"Invoice {invoice.invoice_id}: No legal start date available, "
                "cannot compute payment terms"
            )
            return self._create_incomplete_result(
                invoice=invoice,
                matching_result=matching_result,
                legal_status=legal_status,
                contractual_delay_days=contractual_delay_days,
                alerts=all_alerts,
                notes=all_notes
            )

        
        logger.info(f"Invoice {invoice.invoice_id}: Legal start date = {legal_start_date}")
        
        # ========================================================================
        # STEP 3: Compute applied legal delay
        # ========================================================================
        applied_delay, delay_alerts, delay_notes = self.payment_terms_engine.compute_applied_delay(
            contractual_delay_days=contractual_delay_days
        )
        all_alerts.extend(delay_alerts)
        all_notes.extend(delay_notes)
        
        logger.info(f"Invoice {invoice.invoice_id}: Applied legal delay = {applied_delay} days")
        
        # ========================================================================
        # STEP 4: Compute legal due date
        # ========================================================================
        legal_due_date, due_notes = self.payment_terms_engine.compute_due_date(
            legal_start_date=legal_start_date,
            delay_days=applied_delay
        )
        all_notes.extend(due_notes)
        
        logger.info(f"Invoice {invoice.invoice_id}: Legal due date = {legal_due_date}")
        
        # ========================================================================
        # STEP 5: Get payment information from matching
        # ========================================================================
        payment_date = (
            matching_result.payment_dates[0] 
            if matching_result.payment_dates 
            else None
        )
        
        if payment_date:
            logger.info(f"Invoice {invoice.invoice_id}: Payment date = {payment_date}")
        else:
            logger.info(f"Invoice {invoice.invoice_id}: UNPAID")
        
        # Validate payment coherence
        payment_alerts = self.status_engine.check_payment_validity(
            invoice=invoice,
            payment_date=payment_date
        )
        all_alerts.extend(payment_alerts)
        
        # ========================================================================
        # STEP 6: Compute days overdue (calendar days)
        # ========================================================================
        days_overdue, overdue_alerts = self.payment_terms_engine.compute_days_overdue(
            due_date=legal_due_date,
            payment_date=payment_date
        )
        all_alerts.extend(overdue_alerts)
        
        logger.info(f"Invoice {invoice.invoice_id}: Days overdue = {days_overdue}")
        
        # ========================================================================
        # STEP 7: Compute amounts
        # ========================================================================
        invoice_amount = invoice.amounts.total_ttc or 0.0
        paid_amount = matching_result.total_paid
        unpaid_amount = max(0, invoice_amount - paid_amount)
        
        logger.info(
            f"Invoice {invoice.invoice_id}: "
            f"Amount={invoice_amount:.2f}, Paid={paid_amount:.2f}, "
            f"Unpaid={unpaid_amount:.2f} MAD"
        )
        
        # Add alert for partial payment
        if 0 < unpaid_amount < invoice_amount:
            all_alerts.append(Alert(
                code=AlertCode.PARTIAL_PAYMENT_DETECTED,
                severity=AlertSeverity.INFO,
                message=(
                    f"Paiement partiel détecté: "
                ),
                field="matching"
            ))
        
        # ========================================================================
        # STEP 8: Compute penalty (CRITICAL - DGI calendar month logic)
        # ========================================================================
        
        # CRITICAL: For any unpaid amount (partial or full), penalties accrue until TODAY
        # For fully paid invoices, use the actual payment date
        from datetime import date as date_type
        effective_date = date_type.today() if unpaid_amount > 0 else payment_date
        
        # Flag for logging purposes
        has_partial_payment = (paid_amount > 0 and unpaid_amount > 0)
        is_fully_unpaid = (paid_amount == 0 and unpaid_amount > 0)
        
        # 8.1: Compute months of delay using DGI calendar logic
        months_of_delay, months_notes = self.penalty_engine.compute_months_of_delay(
            due_date=legal_due_date,
            payment_date=effective_date
        )
        all_notes.extend(months_notes)
        
        if has_partial_payment:
            all_notes.append(
                f"⚠️ Paiement partiel détecté: pénalités calculées jusqu'à aujourd'hui "
                f"({date_type.today().isoformat()}) pour le montant impayé ({unpaid_amount:.2f} MAD)"
            )
        elif is_fully_unpaid:
            all_notes.append(
                f"⚠️ Facture non payée: pénalités calculées jusqu'à aujourd'hui "
                f"({date_type.today().isoformat()}) pour le montant total ({unpaid_amount:.2f} MAD)"
            )
        
        logger.info(
            f"Invoice {invoice.invoice_id}: "
            f"Months of delay = {months_of_delay} (DGI calendar method)"
        )
        
        # 8.2: Compute penalty rate
        penalty_rate, rate_notes = self.penalty_engine.compute_penalty_rate(months_of_delay)
        all_notes.extend(rate_notes)
        
        # 8.3: Compute penalty amount (DGI rule: penalties on invoice amount for late full payments)
        penalty_amount, amount_notes = self.penalty_engine.compute_penalty_amount(
            unpaid_amount=unpaid_amount,
            penalty_rate=penalty_rate,
            invoice_amount=invoice_amount,
            months_of_delay=months_of_delay
        )
        all_notes.extend(amount_notes)
        
        base_penalty_amount = penalty_amount
        
        logger.info(
            f"Invoice {invoice.invoice_id}: "
            f"Base penalty = {base_penalty_amount:.2f} MAD ({penalty_rate:.2f}%)"
        )
        
        # ========================================================================
        # STEP 9: Apply legal status rules to penalty
        # ========================================================================
        final_penalty_amount, penalty_suspended, status_penalty_notes = \
            self.status_engine.apply_status_rules(
                legal_status=legal_status,
                base_penalty_amount=base_penalty_amount
            )
        all_notes.extend(status_penalty_notes)
        
        if penalty_suspended:
            logger.warning(
                f"Invoice {invoice.invoice_id}: "
                f"Penalty SUSPENDED ({legal_status.value}), "
                f"calculated amount: {base_penalty_amount:.2f} MAD"
            )
        
        # ========================================================================
        # STEP 10: Add matching confidence alerts
        # ========================================================================
        if matching_result.matches:
            best_match = matching_result.matches[0]
            if best_match.confidence_score < 80:
                all_alerts.append(Alert(
                    code=AlertCode.LOW_CONFIDENCE_MATCH,
                    severity=AlertSeverity.WARNING,
                    message=(
                        f"Confiance de matching faible: {best_match.confidence_score:.0f}%. "
                        "Validation manuelle recommandée."
                    ),
                    field="matching"
                ))
                logger.warning(
                    f"Invoice {invoice.invoice_id}: "
                    f"Low matching confidence: {best_match.confidence_score:.0f}%"
                )
        
        # ========================================================================
        # STEP 11: Determine if manual review is required
        # ========================================================================
        requires_manual_review = any(
            alert.severity in (AlertSeverity.WARNING, AlertSeverity.ERROR, AlertSeverity.CRITICAL)
            for alert in all_alerts
        )
        
        if requires_manual_review:
            logger.warning(
                f"Invoice {invoice.invoice_id}: "
                f"REQUIRES MANUAL REVIEW ({len(all_alerts)} alerts)"
            )
        
        # ========================================================================
        # STEP 12: Build calculation breakdown for frontend display
        # ========================================================================
        calculation_breakdown = {
            "base_rate_percent": self.penalty_engine.base_rate,
            "monthly_increment_percent": self.penalty_engine.monthly_increment,
            "months_breakdown": [
                {
                    "month": i + 1,
                    "rate": self.penalty_engine.base_rate + (i * self.penalty_engine.monthly_increment),
                    "is_applied": i < months_of_delay
                }
                for i in range(max(months_of_delay, 1))
            ],
            "calculation_steps": {
                "step1_delay": {
                    "label": "Calcul du retard",
                    "due_date": legal_due_date.isoformat() if legal_due_date else None,
                    "payment_date": payment_date.isoformat() if payment_date else None,
                    "days_overdue": days_overdue,
                    "months_of_delay": months_of_delay,
                    "formula": f"{days_overdue} jours → {months_of_delay} mois (tout mois entamé compte)"
                },
                "step2_rate": {
                    "label": "Calcul du taux",
                    "base_rate": self.penalty_engine.base_rate,
                    "months": months_of_delay,
                    "increment": self.penalty_engine.monthly_increment,
                    "penalty_rate": penalty_rate,
                    "formula": f"{self.penalty_engine.base_rate}% + ({months_of_delay - 1} × {self.penalty_engine.monthly_increment}%) = {penalty_rate}%"
                },
                "step3_amount": {
                    "label": "Calcul du montant",
                    "unpaid_amount": unpaid_amount,
                    "penalty_rate": penalty_rate,
                    "base_penalty": base_penalty_amount,
                    "formula": f"{unpaid_amount:.2f} MAD × {penalty_rate}% = {base_penalty_amount:.2f} MAD"
                },
                "step4_status": {
                    "label": "Application du statut",
                    "legal_status": legal_status.value,
                    "penalty_suspended": penalty_suspended,
                    "final_penalty": final_penalty_amount,
                    "formula": f"Statut {legal_status.value}: {'Pénalité suspendue' if penalty_suspended else f'{final_penalty_amount:.2f} MAD'}"
                }
            }
        }
        
        # ========================================================================
        # STEP 13: Build final result
        # ========================================================================
        result = LegalResult(
            invoice_id=invoice.invoice_id,
            legal_start_date=legal_start_date,
            legal_due_date=legal_due_date,
            contractual_delay_days=contractual_delay_days,
            applied_legal_delay_days=applied_delay,
            actual_payment_date=payment_date,
            days_overdue=days_overdue,
            months_of_delay=months_of_delay,
            penalty_rate=penalty_rate,
            penalty_amount=final_penalty_amount,
            penalty_suspended=penalty_suspended,
            legal_status=legal_status,
            invoice_amount_ttc=invoice_amount,
            paid_amount=paid_amount,
            unpaid_amount=unpaid_amount,
            alerts=all_alerts,
            computation_notes=all_notes,
            calculation_breakdown=calculation_breakdown,
            requires_manual_review=requires_manual_review
        )
        
        # Final summary log
        logger.info(
            f"✓ Invoice {invoice.invoice_id} computation complete: "
            f"Status={legal_status.value}, "
            f"Delay={days_overdue}d ({months_of_delay}m), "
            f"Penalty={final_penalty_amount:.2f} MAD, "
            f"Alerts={len(all_alerts)}, "
            f"Review={'YES' if requires_manual_review else 'NO'}"
        )
        
        return result
    
    def _create_incomplete_result(
        self,
        invoice: InvoiceStruct,
        matching_result: MatchingResult,
        legal_status: LegalStatus,
        contractual_delay_days: Optional[int],
        alerts: List[Alert],
        notes: List[str]
    ) -> LegalResult:
        """
        Create a result when computation cannot be completed.
        Used when critical data is missing (no dates available).
        
        This still returns a valid LegalResult object but with:
        - Zero penalty
        - Zero delays
        - Manual review flag set to True
        - Critical alerts preserved
        
        Args:
            invoice: Invoice structure
            matching_result: Matching result
            legal_status: Determined legal status
            alerts: Accumulated alerts (including critical ones)
            notes: Computation notes
        
        Returns:
            Incomplete LegalResult with error state
        """
        invoice_amount = invoice.amounts.total_ttc or 0.0
        paid_amount = matching_result.total_paid
        unpaid_amount = max(0, invoice_amount - paid_amount)
        
        notes.append(
            "⚠ CALCUL INCOMPLET: Dates manquantes (livraison et facture). "
            "Calcul de délai et pénalités impossible. "
            "Correction des données requise avant soumission DGI."
        )
        
        logger.error(
            f"Invoice {invoice.invoice_id}: "
            "INCOMPLETE COMPUTATION - missing critical dates"
        )
        
        return LegalResult(
            invoice_id=invoice.invoice_id,
            legal_start_date=None,
            legal_due_date=None,
            contractual_delay_days=contractual_delay_days,
            applied_legal_delay_days=60,  # Default legal delay
            actual_payment_date=None,
            days_overdue=0,
            months_of_delay=0,
            penalty_rate=0.0,
            penalty_amount=0.0,
            penalty_suspended=False,
            legal_status=legal_status,
            invoice_amount_ttc=invoice_amount,
            paid_amount=paid_amount,
            unpaid_amount=unpaid_amount,
            alerts=alerts,
            computation_notes=notes,
            requires_manual_review=True  # CRITICAL: Always requires review
        )