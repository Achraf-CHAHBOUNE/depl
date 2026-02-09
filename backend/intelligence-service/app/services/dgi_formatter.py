from typing import List
import logging

from ..schemas.invoice import InvoiceStruct
from ..schemas.matching import MatchingResult
from ..schemas.legal_result import LegalResult
from ..schemas.dgi_output import DGIDeclaration, DGIInvoiceLine

logger = logging.getLogger(__name__)


class DGIFormatter:
    """
    Format extracted, matched, and legally computed data into DGI declaration structure.
    
    This matches the official Moroccan DGI payment delay declaration form
    with complete legal calculations.
    """
    
    def format_declaration(
        self,
        invoices: List[InvoiceStruct],
        matching_results: List[MatchingResult],
        legal_results: List[LegalResult],
        company_ice: str,
        company_name: str,
        company_rc: str,
        declaration_year: int,
        declaration_month: int = None,
        activity_sector: str = None
    ) -> DGIDeclaration:
        """
        Create complete DGI declaration from all computation results.
        
        Args:
            invoices: Extracted invoice structures
            matching_results: Matching results
            legal_results: Legal computation results
            company_ice: Company ICE
            company_name: Company name
            company_rc: Company RC
            declaration_year: Declaration year
            declaration_month: Declaration month (optional)
            activity_sector: Activity sector (optional)
        
        Returns:
            Complete DGI declaration
        """
        
        if not (len(invoices) == len(matching_results) == len(legal_results)):
            raise ValueError("Invoices, matching_results, and legal_results must have same length")

        
        invoice_lines = []
        
        # Financial totals
        total_invoiced = 0.0
        total_paid = 0.0
        total_unpaid = 0.0
        
        # Penalty totals
        total_penalty = 0.0
        total_penalty_suspended = 0.0
        
        # Quality metrics
        total_alerts = 0
        invoices_requiring_review = 0
        
        # Compliance counts
        invoices_on_time = 0
        invoices_delayed = 0
        invoices_unpaid = 0
        
        for invoice, matching, legal in zip(invoices, matching_results, legal_results):
            line = self._create_invoice_line(invoice, matching, legal)
            invoice_lines.append(line)
            
            # Update totals
            total_invoiced += line.invoice_amount_ttc or 0
            total_paid += line.payment_amount or 0
            total_unpaid += (line.invoice_amount_ttc or 0) - (line.payment_amount or 0)
            
            if legal.penalty_suspended:
                total_penalty_suspended += legal.penalty_amount
            else:
                total_penalty += legal.penalty_amount
            
            total_alerts += len(legal.alerts)
            if legal.requires_manual_review:
                invoices_requiring_review += 1
            
            # Compliance status - FIXED: Safe enum/string handling
            payment_status = matching.payment_status.value if hasattr(matching.payment_status, 'value') else str(matching.payment_status)
            if payment_status == "PAID":
                if legal.days_overdue == 0:
                    invoices_on_time += 1
                else:
                    invoices_delayed += 1
            else:
                invoices_unpaid += 1
        
        declaration = DGIDeclaration(
            company_ice=company_ice,
            company_name=company_name,
            company_rc=company_rc,
            declaration_year=declaration_year,
            declaration_month=declaration_month,
            activity_sector=activity_sector,
            invoices=invoice_lines,
            total_invoices=len(invoice_lines),
            total_amount_invoiced=round(total_invoiced, 2),
            total_amount_paid=round(total_paid, 2),
            total_amount_unpaid=round(total_unpaid, 2),
            total_penalty_amount=round(total_penalty, 2),
            total_penalty_suspended=round(total_penalty_suspended, 2),
            invoices_requiring_review=invoices_requiring_review,
            total_alerts=total_alerts,
            invoices_on_time=invoices_on_time,
            invoices_delayed=invoices_delayed,
            invoices_unpaid=invoices_unpaid
        )
        
        logger.info(
            f"DGI declaration formatted: {len(invoice_lines)} invoices, "
            f"Total penalties: {total_penalty:.2f} MAD, "
            f"Alerts: {total_alerts}, "
            f"Requiring review: {invoices_requiring_review}"
        )
        
        return declaration
    
    def _create_invoice_line(
        self,
        invoice: InvoiceStruct,
        matching: MatchingResult,
        legal: LegalResult
    ) -> DGIInvoiceLine:
        """
        Create a single DGI invoice line with all legal computations.
        """
        # Get first (best) payment if exists
        payment_date = legal.actual_payment_date
        payment_amount = legal.paid_amount
        
        # Build remarks
        remarks = self._generate_remarks(invoice, matching, legal)
        
        # Safe string conversion for enums
        payment_status_str = (
            matching.payment_status.value 
            if hasattr(matching.payment_status, 'value') 
            else str(matching.payment_status)
        )
        
        legal_status_str = (
            legal.legal_status.value 
            if hasattr(legal.legal_status, 'value') 
            else str(legal.legal_status)
        )
        
        return DGIInvoiceLine(
            supplier_name=invoice.supplier.name,
            supplier_ice=invoice.supplier.ice,
            invoice_number=invoice.invoice.number,
            invoice_date=invoice.invoice.issue_date,
            invoice_amount_ttc=legal.invoice_amount_ttc,
            legal_start_date=legal.legal_start_date,
            legal_due_date=legal.legal_due_date,
            payment_date=payment_date,
            payment_amount=payment_amount,
            contractual_payment_delay=legal.contractual_delay_days,
            applied_legal_delay=legal.applied_legal_delay_days,
            actual_payment_delay=legal.days_overdue,
            months_of_delay=legal.months_of_delay,
            penalty_rate=legal.penalty_rate,
            penalty_amount=legal.penalty_amount,
            penalty_suspended=legal.penalty_suspended,
            payment_status=payment_status_str,  # ← FIXED
            legal_status=legal_status_str,       # ← FIXED
            remarks=remarks,
            requires_manual_review=legal.requires_manual_review,
            alert_count=len(legal.alerts)
        )
    
    def _generate_remarks(
        self,
        invoice: InvoiceStruct,
        matching: MatchingResult,
        legal: LegalResult
    ) -> str:
        """
        Generate comprehensive remarks for audit trail.
        """
        remarks = []
        
        # Matching confidence
        if matching.matches:
            best_match = matching.matches[0]
            remarks.append(f"Confiance matching: {best_match.confidence_score:.0f}%")
            
            if best_match.confidence_score < 80:
                remarks.append("⚠ Validation manuelle recommandée")
        
        # Payment status - FIXED: Safe enum/string handling
        payment_status = matching.payment_status.value if hasattr(matching.payment_status, 'value') else str(matching.payment_status)
        if payment_status == "PARTIALLY_PAID":
            remarks.append(
                f"Paiement partiel: {legal.paid_amount:.2f} / "
                f"{legal.invoice_amount_ttc:.2f} MAD"
            )
        
        # Legal status - FIXED: Safe enum/string handling
        legal_status = legal.legal_status.value if hasattr(legal.legal_status, 'value') else str(legal.legal_status)
        if legal_status != "NORMAL":
            remarks.append(f"Statut: {legal_status}")
        
        # Penalty info
        if legal.penalty_suspended:
            remarks.append(
                f"Pénalité suspendue: {legal.penalty_amount:.2f} MAD"
            )
        elif legal.penalty_amount > 0:
            remarks.append(
                f"Pénalité: {legal.penalty_amount:.2f} MAD ({legal.penalty_rate:.2f}%)"
            )
        
        # Critical alerts
        critical_alerts = [
            alert for alert in legal.alerts 
            if alert.severity in ("ERROR", "CRITICAL")
        ]
        if critical_alerts:
            remarks.append(f"⚠ {len(critical_alerts)} alerte(s) critique(s)")
        
        # Missing fields
        if invoice.missing_fields:
            remarks.append(
                f"Champs manquants: {len(invoice.missing_fields)}"
            )
        
        return " | ".join(remarks) if remarks else None