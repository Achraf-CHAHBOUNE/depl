import httpx
import logging
from typing import List, Dict, Tuple
from datetime import datetime
import asyncio
from ..models.batch import Batch, Document, BatchStatus, DocumentType, DocumentStatus
from ..models.validation import InvoiceValidationUpdate

logger = logging.getLogger(__name__)

class WorkflowOrchestrator:
    """
    Complete workflow orchestration for DGI compliance processing.
    
    Workflow Steps:
    1. Upload → Store files
    2. OCR → Extract text from PDFs
    3. Extraction → Get structured data (invoices/payments)
    4. Matching → Link invoices to payments
    5. Rules → Calculate delays and penalties
    6. Validation → Human review (CRITICAL for delivery dates)
    7. Export → Generate DGI-ready files
    """
    
    def __init__(
        self,
        ocr_service_url: str = "http://localhost:8001",
        intelligence_service_url: str = "http://localhost:8004"
    ):
        self.ocr_url = ocr_service_url
        self.intelligence_url = intelligence_service_url
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def process_complete_workflow(self, batch: Batch) -> Batch:
        """
        Execute the complete workflow from upload to DGI calculation.
        This is the main entry point that orchestrates everything.
        """
        try:
            logger.info(f"Starting complete workflow for batch {batch.batch_id}")
            
            # Step 1: OCR Processing
            batch = await self.step_ocr_processing(batch)
            
            # Step 2: Structured Extraction
            batch = await self.step_extraction(batch)
            
            # Step 3: Matching
            batch = await self.step_matching(batch)
            
            # Step 4: Legal Rules Calculation
            batch = await self.step_rules_calculation(batch)
            
            # Step 5: Check if validation required
            batch = await self.check_validation_requirements(batch)
            
            logger.info(f"Workflow completed for batch {batch.batch_id}")
            return batch
            
        except Exception as e:
            logger.error(f"Workflow failed for batch {batch.batch_id}: {str(e)}")
            batch.status = BatchStatus.FAILED
            batch.error_message = str(e)
            batch.updated_at = datetime.now()
            return batch
    
    async def step_ocr_processing(self, batch: Batch) -> Batch:
        """
        Step 1: OCR Processing
        Process all uploaded documents through OCR service
        """
        logger.info(f"Step 1: OCR Processing for batch {batch.batch_id}")
        batch.status = BatchStatus.OCR_PROCESSING
        batch.current_step = "OCR - Extraction de texte"
        batch.progress_percentage = 10.0
        batch.updated_at = datetime.now()
        
        all_documents = batch.invoice_documents + batch.payment_documents
        total_docs = len(all_documents)
        
        for idx, document in enumerate(all_documents):
            try:
                document.status = DocumentStatus.OCR_PROCESSING
                
                # Call OCR service
                ocr_text = await self._call_ocr_service(document.file_path, document.filename)
                
                document.ocr_text = ocr_text
                document.status = DocumentStatus.OCR_DONE
                document.processed_at = datetime.now()
                
                # Update progress
                batch.progress_percentage = 10.0 + (40.0 * (idx + 1) / total_docs)
                
                logger.info(f"OCR completed for {document.filename}")
                
            except Exception as e:
                logger.error(f"OCR failed for {document.filename}: {str(e)}")
                document.status = DocumentStatus.FAILED
                document.error_message = str(e)
                batch.failed_documents.append(document.document_id)
        
        batch.status = BatchStatus.EXTRACTION_DONE if not batch.failed_documents else BatchStatus.FAILED
        batch.updated_at = datetime.now()
        return batch
    
    async def step_extraction(self, batch: Batch) -> Batch:
        """
        Step 2: Structured Data Extraction
        Extract invoices and payments using Intelligence Service
        """
        logger.info(f"Step 2: Extraction for batch {batch.batch_id}")
        batch.current_step = "Extraction - Lecture des données"
        batch.progress_percentage = 50.0
        batch.updated_at = datetime.now()
        
        # Extract invoices
        invoices_data = []
        for doc in batch.invoice_documents:
            if doc.status == DocumentStatus.OCR_DONE and doc.ocr_text:
                try:
                    extracted = await self._call_intelligence_extraction(
                        doc.ocr_text,
                        DocumentType.INVOICE
                    )
                    doc.extracted_data = extracted
                    invoices_data.append(extracted)
                    doc.status = DocumentStatus.EXTRACTION_DONE
                except Exception as e:
                    logger.error(f"Extraction failed for invoice {doc.filename}: {str(e)}")
                    batch.failed_documents.append(doc.document_id)
        
        # Extract payments
        payments_data = []
        for doc in batch.payment_documents:
            if doc.status == DocumentStatus.OCR_DONE and doc.ocr_text:
                try:
                    extracted = await self._call_intelligence_extraction(
                        doc.ocr_text,
                        DocumentType.PAYMENT
                    )
                    doc.extracted_data = extracted
                    payments_data.append(extracted)
                    doc.status = DocumentStatus.EXTRACTION_DONE
                except Exception as e:
                    logger.error(f"Extraction failed for payment {doc.filename}: {str(e)}")
                    batch.failed_documents.append(doc.document_id)
        
        batch.invoices_data = invoices_data
        batch.payments_data = payments_data
        batch.total_invoices = len(invoices_data)
        batch.total_payments = len(payments_data)
        batch.progress_percentage = 60.0
        batch.updated_at = datetime.now()
        
        logger.info(f"Extracted {len(invoices_data)} invoices and {len(payments_data)} payments")
        return batch
    
    async def step_matching(self, batch: Batch) -> Batch:
        """
        Step 3: Invoice-Payment Matching
        """
        logger.info(f"Step 3: Matching for batch {batch.batch_id}")
        batch.status = BatchStatus.MATCHING_DONE
        batch.current_step = "Rapprochement - Factures ↔ Paiements"
        batch.progress_percentage = 70.0
        batch.updated_at = datetime.now()
        
        try:
            matching_results = await self._call_intelligence_matching(
                batch.invoices_data,
                batch.payments_data
            )
            
            batch.matching_results = matching_results
            logger.info(f"Matching completed: {len(matching_results)} results")
            
        except Exception as e:
            logger.error(f"Matching failed: {str(e)}")
            batch.status = BatchStatus.FAILED
            batch.error_message = f"Matching error: {str(e)}"
        
        batch.progress_percentage = 75.0
        batch.updated_at = datetime.now()
        return batch
    
    async def step_rules_calculation(self, batch: Batch) -> Batch:
        """
        Step 4: Legal Rules Calculation (DGI Compliance)
        """
        logger.info(f"Step 4: Rules calculation for batch {batch.batch_id}")
        batch.status = BatchStatus.RULES_CALCULATED
        batch.current_step = "Calcul - Délais et Pénalités DGI"
        batch.progress_percentage = 80.0
        batch.updated_at = datetime.now()
        
        try:
            legal_results = await self._call_intelligence_rules(
                batch.invoices_data,
                batch.matching_results
            )
            
            batch.legal_results = legal_results
            
            # Count alerts
            total_alerts = 0
            critical_alerts = 0
            for result in legal_results:
                alerts = result.get('alerts', [])
                total_alerts += len(alerts)
                critical_alerts += sum(1 for a in alerts if a.get('severity') in ['ERROR', 'CRITICAL'])
            
            batch.alerts_count = total_alerts
            batch.critical_alerts_count = critical_alerts
            
            logger.info(f"Rules calculated: {total_alerts} alerts ({critical_alerts} critical)")
            
        except Exception as e:
            logger.error(f"Rules calculation failed: {str(e)}")
            batch.status = BatchStatus.FAILED
            batch.error_message = f"Rules error: {str(e)}"
        
        batch.progress_percentage = 90.0
        batch.updated_at = datetime.now()
        return batch
    
    async def check_validation_requirements(self, batch: Batch) -> Batch:
        """
        Step 5: Check if human validation is required
        
        Validation required if:
        - Any critical alerts
        - Missing delivery dates
        - Low confidence matches
        """
        logger.info(f"Step 5: Checking validation requirements for batch {batch.batch_id}")
        
        requires_validation = False
        reasons = []
        
        # Check for critical alerts
        if batch.critical_alerts_count > 0:
            requires_validation = True
            reasons.append(f"{batch.critical_alerts_count} alertes critiques")
        
        # Check for missing delivery dates
        missing_delivery_dates = sum(
            1 for inv in batch.invoices_data
            if not inv.get('invoice', {}).get('delivery_date')
        )
        if missing_delivery_dates > 0:
            requires_validation = True
            reasons.append(f"{missing_delivery_dates} dates de livraison manquantes")
        
        # Check for low confidence matches
        low_confidence = sum(
            1 for match in batch.matching_results
            if match.get('matches') and match['matches'][0].get('confidence_score', 100) < 70
        )
        if low_confidence > 0:
            requires_validation = True
            reasons.append(f"{low_confidence} rapprochements à vérifier")
        
        batch.requires_validation = requires_validation
        
        if requires_validation:
            batch.status = BatchStatus.VALIDATION_PENDING
            batch.current_step = f"Validation requise: {', '.join(reasons)}"
            logger.warning(f"Batch {batch.batch_id} requires validation: {reasons}")
        else:
            batch.status = BatchStatus.VALIDATED
            batch.current_step = "Traitement terminé - Prêt pour export"
            batch.progress_percentage = 100.0
            logger.info(f"Batch {batch.batch_id} validated automatically")
        
        batch.updated_at = datetime.now()
        return batch
    
    async def apply_user_validation(
        self, 
        batch: Batch, 
        updates: List[InvoiceValidationUpdate]
    ) -> Batch:
        """
        Step 6: Apply user validation corrections
        
        This implements the "Human-in-the-Loop" workflow from Cahier des Charges Section 5.5
        """
        logger.info(f"Applying user validation for batch {batch.batch_id}")
        
        # Apply updates to invoices
        for update in updates:
            for idx, invoice in enumerate(batch.invoices_data):
                if invoice.get('invoice_id') == update.invoice_id:
                    # Update delivery date if provided
                    if update.delivery_date:
                        if 'invoice' not in invoice:
                            invoice['invoice'] = {}
                        invoice['invoice']['delivery_date'] = update.delivery_date.isoformat()
                    
                    # Update other fields
                    if update.supplier_name:
                        if 'supplier' not in invoice:
                            invoice['supplier'] = {}
                        invoice['supplier']['name'] = update.supplier_name
                    
                    if update.amount_ttc:
                        if 'amounts' not in invoice:
                            invoice['amounts'] = {}
                        invoice['amounts']['total_ttc'] = update.amount_ttc
                    
                    batch.invoices_data[idx] = invoice
                    break
        
        # Recalculate rules with updated data
        batch = await self.step_matching(batch)
        batch = await self.step_rules_calculation(batch)
        
        batch.status = BatchStatus.VALIDATED
        batch.validated_at = datetime.now()
        batch.current_step = "Validé - Prêt pour export"
        batch.progress_percentage = 100.0
        batch.updated_at = datetime.now()
        
        logger.info(f"Validation completed for batch {batch.batch_id}")
        return batch
    
    async def generate_dgi_declaration(self, batch: Batch) -> Dict:
        """
        Step 7: Generate final DGI declaration
        """
        logger.info(f"Generating DGI declaration for batch {batch.batch_id}")
        
        try:
            response = await self.client.post(
                f"{self.intelligence_url}/dgi/format",
                json={
                    "invoices": batch.invoices_data,
                    "matching_results": batch.matching_results,
                    "legal_results": batch.legal_results,
                    "company_ice": batch.company_ice,
                    "company_name": batch.company_name,
                    "company_rc": batch.company_rc or "",
                    "declaration_year": datetime.now().year,
                    "declaration_month": datetime.now().month
                }
            )
            response.raise_for_status()
            
            dgi_declaration = response.json()
            batch.dgi_declaration = dgi_declaration
            batch.status = BatchStatus.EXPORTED
            batch.exported_at = datetime.now()
            batch.updated_at = datetime.now()
            
            logger.info(f"DGI declaration generated for batch {batch.batch_id}")
            return dgi_declaration
            
        except Exception as e:
            logger.error(f"DGI declaration generation failed: {str(e)}")
            raise
    
    # ========================================================================
    # Private helper methods for calling external services
    # ========================================================================
    
    async def _call_ocr_service(self, file_path: str, filename: str) -> str:
        """Call OCR service to extract text"""
        with open(file_path, 'rb') as f:
            files = {'file': (filename, f, 'application/pdf')}
            response = await self.client.post(
                f"{self.ocr_url}/ocr/extract",
                files=files
            )
            response.raise_for_status()
            return response.json().get('raw_text', '')
    
    async def _call_intelligence_extraction(self, ocr_text: str, doc_type: DocumentType) -> Dict:
        """Call Intelligence Service for structured extraction"""
        endpoint = (
            f"{self.intelligence_url}/extract/invoice"
            if doc_type == DocumentType.INVOICE
            else f"{self.intelligence_url}/extract/payment"
        )
        
        response = await self.client.post(
            endpoint,
            json={"ocr_text": ocr_text, "document_type": doc_type.value}
        )
        response.raise_for_status()
        return response.json()
    
    async def _call_intelligence_matching(self, invoices: List[Dict], payments: List[Dict]) -> List[Dict]:
        """Call Intelligence Service for matching"""
        response = await self.client.post(
            f"{self.intelligence_url}/match",
            json={"invoices": invoices, "payments": payments}
        )
        response.raise_for_status()
        return response.json()
    
    async def _call_intelligence_rules(self, invoices: List[Dict], matching_results: List[Dict]) -> List[Dict]:
        """Call Intelligence Service for legal rules calculation"""
        response = await self.client.post(
            f"{self.intelligence_url}/rules/compute/batch",
            json={
                "invoices": invoices,
                "matching_results": matching_results,
                "contractual_delays": None,
                "disputed_invoices": [],
                "credit_notes": [],
                "procedure_690_suppliers": []
            }
        )
        response.raise_for_status()
        return response.json()