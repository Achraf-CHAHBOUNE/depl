from typing import List, Tuple
from datetime import date, timedelta
import re
from ..schemas.invoice import InvoiceStruct
from ..schemas.payment import PaymentStruct
from ..schemas.matching import MatchingResult, Match, PaymentStatus
import logging
from ..utils.config import config


logger = logging.getLogger(__name__)


class IntelligentMatcher:
    """
    Module B: Intelligent matching between invoices and payments.
    
    Uses deterministic rules with confidence scoring.
    All decisions must be explainable and auditable.
    """
    
    def __init__(self, amount_tolerance: float = 0.01):
        """
        Args:
            amount_tolerance: Maximum allowed difference (1% default)
        """
        self.amount_tolerance = amount_tolerance
    
    def match_invoices_to_payments(
        self,
        invoices: List[InvoiceStruct],
        payments: List[PaymentStruct]
    ) -> List[MatchingResult]:
        """
        Match each invoice to its corresponding payment(s).
        
        Returns:
            List of MatchingResult, one per invoice
        """
        if not invoices:
            logger.warning("No invoices provided for matching")
            return []
        
        if not payments:
            logger.warning("No payments provided for matching")
            # Return unpaid status for all invoices
            return [
                self._create_unpaid_result(invoice) 
                for invoice in invoices
            ]
        
        results = []
        
        for invoice in invoices:
            result = self._match_single_invoice(invoice, payments)
            results.append(result)
        
        return results
    
    def _match_single_invoice(
        self,
        invoice: InvoiceStruct,
        payments: List[PaymentStruct]
    ) -> MatchingResult:
        """
        Find all matching payments for a single invoice.
        """
        matches = []
        
        for payment in payments:
            score, reasons, matched_amount = self._calculate_match_score(
                invoice, payment
            )
            
            # Only include matches with sufficient confidence
            if score >= config.MIN_CONFIDENCE_SCORE:
                matches.append(Match(
                    payment_id=payment.payment_id,
                    matched_amount=matched_amount,
                    confidence_score=score,
                    matching_reasons=reasons
                ))
        
        # Sort by confidence score (highest first)
        matches.sort(key=lambda x: x.confidence_score, reverse=True)
        
        # Calculate payment status
        total_paid = sum(m.matched_amount for m in matches)
        invoice_total = invoice.amounts.total_ttc or 0
        remaining = max(0, invoice_total - total_paid)
        
        if total_paid == 0:
            status = PaymentStatus.UNPAID
        elif remaining > 0.01:  # Allow 1 cent rounding
            status = PaymentStatus.PARTIALLY_PAID
        else:
            status = PaymentStatus.PAID
        
        # Extract payment dates
        payment_dates = []
        for match in matches:
            payment = next(
                (p for p in payments if p.payment_id == match.payment_id),
                None
            )
            if payment and payment.dates.operation_date:
                payment_dates.append(payment.dates.operation_date)
                
                
        # Audit logging
        logger.info(
            f"Invoice {invoice.invoice_id} matched: "
            f"Status={status.value}, "
            f"Matches={len(matches)}, "
            f"Total paid={total_paid:.2f}, "
            f"Remaining={remaining:.2f}"
        )

        if matches:
            best_match = matches[0]
            logger.info(
                f"  Best match: Payment {best_match.payment_id}, "
                f"Confidence={best_match.confidence_score:.0f}%, "
                f"Reasons: {'; '.join(best_match.matching_reasons)}"
            )
        
        return MatchingResult(
            invoice_id=invoice.invoice_id,
            matches=matches,
            payment_status=status,
            total_paid=total_paid,
            remaining_amount=remaining,
            payment_dates=sorted(payment_dates)
        )
    
    def _calculate_match_score(
        self,
        invoice: InvoiceStruct,
        payment: PaymentStruct
    ) -> Tuple[float, List[str], float]:
        """
        Calculate confidence score for invoice-payment matching.
        
        Returns:
            (score, reasons, matched_amount)
        """
        score = 0.0
        reasons = []
        matched_amount = min(
            payment.amount.value or 0,
            invoice.amounts.total_ttc or 0
        )

        
        invoice_amount = invoice.amounts.total_ttc or 0
        payment_amount = payment.amount.value or 0
        
        # Rule 1: Amount matching (40 points)
        if invoice_amount > 0 and payment_amount > 0:
            amount_diff = abs(invoice_amount - payment_amount) / invoice_amount
            
            if amount_diff <= self.amount_tolerance:
                score += 40
                reasons.append(
                    f"Montant exact: facture {invoice_amount:.2f}, "
                    f"paiement {payment_amount:.2f}"
                )
            elif amount_diff <= 0.05:  # Within 5%
                score += 30
                reasons.append(
                    f"Montant proche: différence de {amount_diff*100:.1f}%"
                )
            elif payment_amount < invoice_amount:
                # Partial payment
                score += 20
                matched_amount = payment_amount
                reasons.append(
                    f"Paiement partiel: {payment_amount:.2f} / "
                    f"{invoice_amount:.2f}"
                )
        
        # Rule 2: Date validation (20 points)
      
        if (invoice.invoice.issue_date and payment.dates.operation_date):
            
            try:
                # Ensure dates are date objects
                inv_date = invoice.invoice.issue_date
                pay_date = payment.dates.operation_date
                
                if isinstance(inv_date, str):
                    from datetime import datetime
                    inv_date = datetime.fromisoformat(inv_date).date()
                if isinstance(pay_date, str):
                    pay_date = datetime.fromisoformat(pay_date).date()
                
                if pay_date >= inv_date:
                    score += 20
                    reasons.append(
                        f"Date cohérente: paiement après facture "
                        f"({pay_date})"
                    )
                else:
                    reasons.append(
                        f"ATTENTION: Paiement avant émission de facture "
                        f"(facture: {inv_date}, paiement: {pay_date})"
                    )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Date validation failed: {e}")
                reasons.append("Dates invalides - validation impossible")
                
                
        # Rule 3: Supplier/Payee name matching (25 points)
        supplier_name = (invoice.supplier.name or "").lower()
        payee_name = (payment.payee.name or "").lower()
        
        if supplier_name and payee_name:
            similarity = self._calculate_name_similarity(
                supplier_name, payee_name
            )
            
            if similarity > 0.9:
                score += 25
                reasons.append(
                    f"Bénéficiaire identique: {payment.payee.name}"
                )
            elif similarity > 0.7:
                score += 15
                reasons.append(
                    f"Bénéficiaire similaire: {payment.payee.name}"
                )
        
        # Rule 4: Reference matching (15 points)
        if invoice.invoice.number and payment.payment.reference:
            inv_num = str(invoice.invoice.number).upper()
            pay_ref = str(payment.payment.reference).upper()
            
            if inv_num in pay_ref:
                score += 15
                reasons.append(
                    f"Référence trouvée: {invoice.invoice.number} "
                    f"dans {payment.payment.reference}"
                )
            elif self._fuzzy_reference_match(inv_num, pay_ref):
                score += 10
                reasons.append(
                    f"Référence partielle: similitude avec "
                    f"{payment.payment.reference}"
                )
        
        # Rule 5: Reasonable payment window (10 points)
        if invoice.invoice.issue_date and payment.dates.operation_date:
            max_delay = timedelta(days=180)
            if payment.dates.operation_date <= invoice.invoice.issue_date + max_delay:
                score += 10
                reasons.append("Paiement dans un délai raisonnable (≤180j)")
 
        
        return (score, reasons, matched_amount)
    
    
    
    
    
    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two company names.
        Handles common variations in Moroccan company names.
        """
        # Normalize
        name1 = self._normalize_company_name(name1)
        name2 = self._normalize_company_name(name2)
        
        # Exact match
        if name1 == name2:
            return 1.0
        
        # Token-based similarity
        tokens1 = set(name1.split())
        tokens2 = set(name2.split())
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
    
    def _normalize_company_name(self, name: str) -> str:
        """
        Normalize company name for comparison.
        """
        name = name.lower().strip()
        
        # Remove common legal forms
        legal_forms = [
            'sarl', 'sa', 'sas', 'eurl', 'snc', 'scs',
            'societe', 'société', 'ste', 'ets', 'etablissement'
        ]
        
        for form in legal_forms:
            name = re.sub(rf'\b{form}\b', '', name)
        
        # Remove special characters
        name = re.sub(r'[^\w\s]', ' ', name)
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        return name
    
    def _fuzzy_reference_match(self, ref1: str, ref2: str) -> bool:
        """
        Check if references match with tolerance for truncation/noise.
        """
        # Extract digits
        digits1 = re.findall(r'\d+', ref1)
        digits2 = re.findall(r'\d+', ref2)
        
        # Check if main numeric part matches
        if digits1 and digits2:
            # Find longest common digit sequence
            for d1 in digits1:
                for d2 in digits2:
                    if d1 in d2 or d2 in d1:
                        if len(d1) >= 4 or len(d2) >= 4:
                            return True
        
        return False
    
    def _create_unpaid_result(self, invoice: InvoiceStruct) -> MatchingResult:
        """
        Create a MatchingResult for an unpaid invoice (no payments available).
        """
        return MatchingResult(
            invoice_id=invoice.invoice_id,
            matches=[],
            payment_status=PaymentStatus.UNPAID,
            total_paid=0.0,
            remaining_amount=invoice.amounts.total_ttc or 0.0,
            payment_dates=[]
        )
