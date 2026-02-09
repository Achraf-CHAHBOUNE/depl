from typing import List
import csv
import io
import logging
from datetime import datetime

from ..schemas.dgi_output import DGIDeclaration, DGIInvoiceLine

logger = logging.getLogger(__name__)


class ExportService:
    """
    Export DGI declarations to CSV/Excel formats.
    """
    
    def export_to_csv(self, declaration: DGIDeclaration) -> bytes:
        """
        Export DGI declaration to CSV format.
        
        Args:
            declaration: DGI declaration to export
        
        Returns:
            CSV file content as bytes
        """
        output = io.StringIO()
        
        # Write header information
        output.write(f"DÉCLARATION DES DÉLAIS DE PAIEMENT\n")
        output.write(f"Entreprise: {declaration.company_name}\n")
        output.write(f"ICE: {declaration.company_ice}\n")
        output.write(f"RC: {declaration.company_rc}\n")
        output.write(f"Année: {declaration.declaration_year}\n")
        if declaration.declaration_month:
            output.write(f"Mois: {declaration.declaration_month}\n")
        if declaration.activity_sector:
            output.write(f"Secteur: {declaration.activity_sector}\n")
        output.write(f"Date d'export: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        output.write("\n")
        
        # Write summary
        output.write("RÉSUMÉ\n")
        output.write(f"Nombre total de factures,{declaration.total_invoices}\n")
        output.write(f"Montant total facturé (MAD),{declaration.total_amount_invoiced:.2f}\n")
        output.write(f"Montant total payé (MAD),{declaration.total_amount_paid:.2f}\n")
        output.write(f"Montant total impayé (MAD),{declaration.total_amount_unpaid:.2f}\n")
        output.write(f"Total pénalités (MAD),{declaration.total_penalty_amount:.2f}\n")
        output.write(f"Total pénalités suspendues (MAD),{declaration.total_penalty_suspended:.2f}\n")
        output.write(f"Factures payées à temps,{declaration.invoices_on_time}\n")
        output.write(f"Factures payées en retard,{declaration.invoices_delayed}\n")
        output.write(f"Factures impayées,{declaration.invoices_unpaid}\n")
        output.write(f"Factures nécessitant validation,{declaration.invoices_requiring_review}\n")
        output.write(f"Nombre total d'alertes,{declaration.total_alerts}\n")
        output.write("\n")
        
        # Write invoice details
        output.write("DÉTAIL DES FACTURES\n")
        
        writer = csv.writer(output)
        
        # Column headers
        headers = [
            "Fournisseur",
            "ICE Fournisseur",
            "N° Facture",
            "Date Facture",
            "Date Référence Légale",
            "Date Échéance Légale",
            "Montant TTC (MAD)",
            "Date Paiement",
            "Montant Payé (MAD)",
            "Délai Contractuel (jours)",
            "Délai Légal Appliqué (jours)",
            "Retard Réel (jours)",
            "Mois de Retard",
            "Taux Pénalité (%)",
            "Montant Pénalité (MAD)",
            "Pénalité Suspendue",
            "Statut Paiement",
            "Statut Juridique",
            "Validation Requise",
            "Nombre Alertes",
            "Remarques"
        ]
        writer.writerow(headers)
        
        # Data rows
        for inv in declaration.invoices:
            row = [
                inv.supplier_name or "",
                inv.supplier_ice or "",
                inv.invoice_number or "",
                inv.invoice_date.isoformat() if inv.invoice_date else "",
                inv.legal_start_date.isoformat() if inv.legal_start_date else "",
                inv.legal_due_date.isoformat() if inv.legal_due_date else "",
                f"{inv.invoice_amount_ttc:.2f}" if inv.invoice_amount_ttc else "",
                inv.payment_date.isoformat() if inv.payment_date else "",
                f"{inv.payment_amount:.2f}" if inv.payment_amount else "",
                str(inv.contractual_payment_delay) if inv.contractual_payment_delay else "",
                str(inv.applied_legal_delay),
                str(inv.actual_payment_delay),
                str(inv.months_of_delay),
                f"{inv.penalty_rate:.2f}",
                f"{inv.penalty_amount:.2f}",
                "OUI" if inv.penalty_suspended else "NON",
                inv.payment_status,
                inv.legal_status,
                "OUI" if inv.requires_manual_review else "NON",
                str(inv.alert_count),
                inv.remarks or ""
            ]
            writer.writerow(row)
        
        # Get CSV content
        csv_content = output.getvalue()
        output.close()
        
        logger.info(
            f"Exported DGI declaration to CSV: "
            f"{declaration.total_invoices} invoices"
        )
        
        return csv_content.encode('utf-8-sig')  # BOM for Excel compatibility
    
    def export_alerts_summary(self, declaration: DGIDeclaration) -> str:
        """
        Generate a human-readable alerts summary report.
        
        Args:
            declaration: DGI declaration
        
        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("RAPPORT D'ALERTES - DÉCLARATION DES DÉLAIS DE PAIEMENT")
        lines.append("=" * 80)
        lines.append("")
        lines.append(f"Entreprise: {declaration.company_name}")
        lines.append(f"ICE: {declaration.company_ice}")
        lines.append(f"Période: {declaration.declaration_year}")
        if declaration.declaration_month:
            lines.append(f"Mois: {declaration.declaration_month}")
        lines.append("")
        lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        # Summary
        lines.append("-" * 80)
        lines.append("RÉSUMÉ")
        lines.append("-" * 80)
        lines.append(f"Total factures: {declaration.total_invoices}")
        lines.append(f"Factures nécessitant validation: {declaration.invoices_requiring_review}")
        lines.append(f"Total alertes: {declaration.total_alerts}")
        lines.append("")
        
        # Invoices requiring review
        review_invoices = [
            inv for inv in declaration.invoices 
            if inv.requires_manual_review
        ]
        
        if review_invoices:
            lines.append("-" * 80)
            lines.append(f"FACTURES NÉCESSITANT VALIDATION ({len(review_invoices)})")
            lines.append("-" * 80)
            lines.append("")
            
            for inv in review_invoices:
                lines.append(f"Facture: {inv.invoice_number or 'N/A'}")
                lines.append(f"  Fournisseur: {inv.supplier_name or 'N/A'}")
                lines.append(f"  Montant: {inv.invoice_amount_ttc:.2f} MAD")
                lines.append(f"  Statut: {inv.payment_status}")
                lines.append(f"  Alertes: {inv.alert_count}")
                if inv.remarks:
                    lines.append(f"  Remarques: {inv.remarks}")
                lines.append("")
        
        # High penalty cases
        high_penalty_invoices = [
            inv for inv in declaration.invoices
            if inv.penalty_amount > 1000  # More than 1000 MAD
        ]
        
        if high_penalty_invoices:
            lines.append("-" * 80)
            lines.append(f"PÉNALITÉS ÉLEVÉES (> 1000 MAD) - {len(high_penalty_invoices)} cas")
            lines.append("-" * 80)
            lines.append("")
            
            for inv in high_penalty_invoices:
                lines.append(f"Facture: {inv.invoice_number or 'N/A'}")
                lines.append(f"  Fournisseur: {inv.supplier_name or 'N/A'}")
                lines.append(f"  Montant facture: {inv.invoice_amount_ttc:.2f} MAD")
                lines.append(f"  Retard: {inv.actual_payment_delay} jours ({inv.months_of_delay} mois)")
                lines.append(f"  Pénalité: {inv.penalty_amount:.2f} MAD ({inv.penalty_rate:.2f}%)")
                if inv.penalty_suspended:
                    lines.append(f"  ⚠ Pénalité SUSPENDUE")
                lines.append("")
        
        lines.append("=" * 80)
        lines.append("FIN DU RAPPORT")
        lines.append("=" * 80)
        
        return "\n".join(lines)