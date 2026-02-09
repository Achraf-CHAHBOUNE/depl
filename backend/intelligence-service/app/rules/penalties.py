from typing import Optional, Tuple, List
import logging
from datetime import date

logger = logging.getLogger(__name__)


class PenaltyEngine:
    """
    Calculate penalties (amende pécuniaire) according to Article 78-3.

    Legal framework:
    - Base rate: 1st month of delay (configurable, default 3%)
    - Increment: +0.85% per additional month
    - Any started month counts as a full month
    - Applied only to unpaid amount (TTC)
    
    CRITICAL DGI RULE: "Tout mois entamé est décompté entièrement"
    - 1 day late = 1 month of delay
    - Crossing into next calendar month = may trigger additional month
    - Uses calendar month boundaries, NOT 30-day periods
    """

    def __init__(
        self, base_rate_percent: float = 2.25, monthly_increment_percent: float = 0.85
    ):
        """
        Args:
            base_rate_percent: Base penalty rate for 1st month (default 2.25%)
            monthly_increment_percent: Additional rate per month (default 0.85%)
        """
        self.base_rate = base_rate_percent
        self.monthly_increment = monthly_increment_percent

        logger.info(
            f"PenaltyEngine initialized: base={base_rate_percent}%, "
            f"increment={monthly_increment_percent}%"
        )

    def compute_months_of_delay(self, due_date: date, payment_date: Optional[date]) -> Tuple[int, List[str]]:
        """
        ✅ CORRECTED DGI-COMPLIANT MONTH CALCULATION
        
        Rule: "Tout mois entamé est décompté entièrement"
        (Any started month is counted entirely)
        
        Formula:
        1. Calculate calendar month transitions (how many month boundaries crossed)
        2. If payment_day > due_day: add 1 (entered that month's delay period)
        3. Minimum 1 month if any delay exists (even 1 day = 1 month)
        
        Examples from Official DGI Cases:
        - Due: Sept 18, Pay: Sept 19 → 1 month (any delay in same month)
        - Due: Sept 18, Pay: Sept 25 → 1 month (same month, same calculation)
        - Due: Sept 18, Pay: Oct 18  → 1 month (1 transition, day 18 = day 18)
        - Due: Sept 18, Pay: Oct 19  → 2 months (1 transition + day 19 > 18)
        - Due: Sept 18, Pay: Nov 15  → 2 months (2 transitions, day 15 < 18)
        - Due: Sept 18, Pay: Nov 20  → 3 months (2 transitions + day 20 > 18)
        
        Args:
            due_date: Legal due date
            payment_date: Actual payment date (None if unpaid)
        
        Returns:
            (months_of_delay, computation_notes)
        """
        if not payment_date or payment_date <= due_date:
            return 0, ["No delay - paid on time or before due date"]
        
        # Step 1: Calculate calendar month transitions
        # How many full month boundaries did we cross?
        year_diff = payment_date.year - due_date.year
        month_diff = payment_date.month - due_date.month
        month_transitions = year_diff * 12 + month_diff
        
        # Step 2: Day comparison - have we "started" that month's delay period?
        # If payment_day > due_day, we've entered the additional month period
        # This is the "tout mois entamé" rule
        day_penalty = 1 if payment_date.day > due_date.day else 0
        
        # Step 3: Total months = transitions + day penalty
        total_months = month_transitions + day_penalty
        
        # Step 4: CRITICAL - Any delay at all is at least 1 month
        # Even 1 day late in same month = 1 full month penalty
        months = max(1, total_months)
        
        # Calculate calendar days for audit trail
        calendar_days = (payment_date - due_date).days
        
        # Detailed computation notes for transparency
        notes = [
            f"DGI calendar calculation: {calendar_days} calendar days late",
            f"Month transitions: {month_transitions} (from {due_date.strftime('%Y-%m')} to {payment_date.strftime('%Y-%m')})",
            f"Day comparison: payment day {payment_date.day} {'>' if day_penalty else '<='} due day {due_date.day}",
            f"Day penalty: {'+1 month' if day_penalty else 'no additional month'}",
            f"Calculation: {month_transitions} transitions + {day_penalty} day penalty = {total_months}",
            f"Final (min 1): {months} month(s) of delay"
        ]
        
        logger.info(
            f"DGI month calculation: {due_date} → {payment_date} = "
            f"{calendar_days} days → {months} months "
            f"(transitions: {month_transitions}, day_penalty: {day_penalty})"
        )
        
        return months, notes

    def compute_penalty_rate(self, months_of_delay: int) -> Tuple[float, List[str]]:
        """
        Compute penalty rate based on months of delay.

        Formula (Article 78-3):
        - 1 month: base_rate (3%)
        - 2 months: base_rate + 1 x increment (3.85%)
        - 3 months: base_rate + 2 x increment (4.70%)
        - N months: base_rate + (N-1) x increment

        Args:
            months_of_delay: Number of months of delay

        Returns:
            (penalty_rate_percent, computation_notes)
        """
        notes = []

        if months_of_delay <= 0:
            notes.append("Aucun retard. Taux de pénalité = 0%.")
            return 0.0, notes

        # Calculate rate: base + (months - 1) × increment
        rate = self.base_rate + (months_of_delay - 1) * self.monthly_increment

        notes.append(
            f"Taux de pénalité: {self.base_rate}% (1er mois) "
            f"+ {months_of_delay - 1} × {self.monthly_increment}% "
            f"= {rate}%"
        )

        logger.info(f"Penalty rate for {months_of_delay} months: {rate}%")

        return rate, notes

    def compute_penalty_amount(
        self, unpaid_amount: float, penalty_rate: float, invoice_amount: float = 0.0, months_of_delay: int = 0
    ) -> Tuple[float, List[str]]:
        """
        Compute penalty amount according to DGI rules.

        DGI Rule: Penalties are calculated on the amount that WAS unpaid during the delay period.
        If payment is late (months_of_delay > 0), penalties apply to the invoice amount
        even if paid in full later.

        Formula: 
        - If late payment (months > 0) and currently paid in full (unpaid = 0):
          penalty = invoice_amount × (penalty_rate / 100)
        - Otherwise:
          penalty = unpaid_amount × (penalty_rate / 100)

        Args:
            unpaid_amount: Current unpaid amount in MAD (TTC)
            penalty_rate: Penalty rate in percent
            invoice_amount: Total invoice amount (for late full payments)
            months_of_delay: Number of months of delay

        Returns:
            (penalty_amount, computation_notes)
        """
        notes = []

        if penalty_rate <= 0:
            notes.append("Taux de pénalité = 0%. Pas de pénalité.")
            return 0.0, notes

        # DGI Rule: Penalties apply to the amount that WAS unpaid during the delay period
        # - If late and fully paid now (unpaid = 0): penalties on full invoice amount
        # - If late and partially paid (unpaid > 0): penalties on current unpaid amount
        # - If late and still unpaid (unpaid = invoice): penalties on full invoice amount
        
        is_late_full_payment = (months_of_delay > 0 and unpaid_amount == 0 and invoice_amount > 0)
        is_late_partial_payment = (months_of_delay > 0 and 0 < unpaid_amount < invoice_amount)
        
        if is_late_full_payment:
            # Late but paid in full: penalties on full invoice amount
            penalty_base_amount = invoice_amount
            notes.append(
                f"⚠️ Paiement tardif mais complet: pénalités calculées sur montant facture "
                f"({invoice_amount:.2f} MAD) pour {months_of_delay} mois de retard"
            )
        elif is_late_partial_payment:
            # Late and partially paid: penalties on unpaid portion
            penalty_base_amount = unpaid_amount
            paid_amount = invoice_amount - unpaid_amount
            notes.append(
                f"⚠️ Paiement partiel tardif: pénalités calculées sur montant impayé "
                f"({unpaid_amount:.2f} MAD) pour {months_of_delay} mois de retard. "
                f"Montant payé: {paid_amount:.2f} MAD"
            )
        else:
            # Not paid or no delay: penalties on unpaid amount
            penalty_base_amount = unpaid_amount

        if penalty_base_amount <= 0:
            notes.append("Montant de base = 0. Pas de pénalité.")
            return 0.0, notes

        # Calculate penalty
        penalty = penalty_base_amount * (penalty_rate / 100.0)
        penalty = round(penalty, 2)

        if is_late_full_payment:
            notes.append(
                f"Montant de la pénalité: {penalty_base_amount:.2f} MAD (facture) "
                f"× {penalty_rate}% = {penalty:.2f} MAD (paiement tardif complet)"
            )
        elif is_late_partial_payment:
            notes.append(
                f"Montant de la pénalité: {penalty_base_amount:.2f} MAD (impayé) "
                f"× {penalty_rate}% = {penalty:.2f} MAD (paiement partiel tardif)"
            )
        else:
            notes.append(
                f"Montant de la pénalité: {penalty_base_amount:.2f} MAD "
                f"× {penalty_rate}% = {penalty:.2f} MAD"
            )

        logger.info(
            f"Penalty calculated: {penalty_base_amount} × {penalty_rate}% = {penalty} MAD "
            f"{'(late full payment)' if is_late_full_payment else ''}"
        )

        return penalty, notes

    def compute_full_penalty(
        self,
        due_date: date,
        payment_date: Optional[date],
        unpaid_amount: float,
        invoice_amount: float
    ) -> Tuple[int, float, float, List[str]]:
        """
        Complete penalty calculation pipeline.
        
        Executes all steps:
        1. Calculate months of delay (DGI calendar method)
        2. Calculate penalty rate
        3. Calculate penalty amount
        
        Args:
            due_date: Legal due date
            payment_date: Actual payment date (None if unpaid)
            unpaid_amount: Current unpaid amount (TTC)
            invoice_amount: Total invoice amount (for late full payments)
        
        Returns:
            (months_of_delay, penalty_rate, penalty_amount, all_notes)
        """
        all_notes = []

        # Step 1: Months of delay
        months, notes1 = self.compute_months_of_delay(due_date, payment_date)
        all_notes.extend(notes1)

        # Step 2: Penalty rate
        rate, notes2 = self.compute_penalty_rate(months)
        all_notes.extend(notes2)

        # Step 3: Penalty amount (with invoice amount for late full payments)
        amount, notes3 = self.compute_penalty_amount(unpaid_amount, rate, invoice_amount, months)
        all_notes.extend(notes3)

        return months, rate, amount, all_notes