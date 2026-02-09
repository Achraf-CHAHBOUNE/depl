from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
import logging
from datetime import datetime
import io
import httpx

from .models.batch import (
    Batch,
    BatchCreateRequest,
    BatchResponse,
    Document,
    DocumentType,
    BatchStatus,
)
from .models.validation import (
    InvoiceValidationUpdate,
    BatchValidationRequest,
    ValidationAlert,
)
from .services.workflow_orchestrator import WorkflowOrchestrator
from .services.file_manager import FileManager
from .database.connection import get_db, init_db, SessionLocal
from .database.repositories import (
    BatchRepository,
    DocumentRepository,
    AuditLogRepository,
)
from .database.models import BatchDB
from .utils.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Orchestrator Service - DGI Compliance",
    version="1.0.0",
    description="Complete workflow orchestration for DGI payment delay declarations",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
orchestrator = WorkflowOrchestrator(
    ocr_service_url=config.OCR_SERVICE_URL,
    intelligence_service_url=config.INTELLIGENCE_SERVICE_URL,
)
file_manager = FileManager(storage_path=config.STORAGE_PATH)


# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    logger.info("Database initialized")


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.post("/batches", response_model=BatchResponse)
async def create_batch(request: BatchCreateRequest, db: Session = Depends(get_db)):
    """Create a new processing batch"""
    try:
        batch = Batch(
            user_id=request.user_id,
            company_name=request.company_name,
            company_ice=request.company_ice,
            company_rc=request.company_rc,
            status=BatchStatus.CREATED,
            current_step="En attente de documents",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        batch_repo = BatchRepository(db)
        batch_db = batch_repo.create(batch)
        
        # CRITICAL: Commit to database
        db.commit()
        db.refresh(batch_db)

        # Audit log
        audit_repo = AuditLogRepository(db)
        audit_repo.log_action(
            batch_id=batch.batch_id,
            user_id=request.user_id,
            action="created",
            entity_type="batch",
        )
        db.commit()  # Commit audit log

        logger.info(f"✅ Batch {batch.batch_id} saved to database")

        return BatchResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            current_step=batch.current_step,
            progress_percentage=batch.progress_percentage,
            total_invoices=batch.total_invoices,
            total_payments=batch.total_payments,
            alerts_count=batch.alerts_count,
            created_at=batch.created_at,
            updated_at=batch.updated_at,
        )

    except Exception as e:
        logger.error(f"❌ Failed to create batch: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batches/{batch_id}/upload/invoices")
async def upload_invoices(
    batch_id: str, files: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    """
    Upload invoice files to a batch.
    Supports multiple file upload.
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Convert to Pydantic model
        batch = db_to_pydantic_batch(batch_db)

        # Save files and create document records
        doc_repo = DocumentRepository(db)
        uploaded_docs = []

        for file in files:
            # Save file
            file_path, file_size = await file_manager.save_upload(
                file, batch_id, "invoices"
            )

            # Create document record
            document = Document(
                batch_id=batch_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                document_type=DocumentType.INVOICE,
                uploaded_at=datetime.now(),
            )

            doc_db = doc_repo.create(document)
            batch.invoice_documents.append(document)
            uploaded_docs.append(document)

        batch.status = BatchStatus.UPLOADING
        batch.updated_at = datetime.now()
        batch_repo.update(batch)
        db.commit()  

        logger.info(f"Uploaded {len(files)} invoices to batch {batch_id}")

        return {
            "batch_id": batch_id,
            "uploaded_count": len(files),
            "documents": [
                {
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                }
                for doc in uploaded_docs
            ],
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batches/{batch_id}/upload/payments")
async def upload_payments(
    batch_id: str, files: List[UploadFile] = File(...), db: Session = Depends(get_db)
):
    """
    Upload payment files to a batch.
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        batch = db_to_pydantic_batch(batch_db)

        doc_repo = DocumentRepository(db)
        uploaded_docs = []

        for file in files:
            file_path, file_size = await file_manager.save_upload(
                file, batch_id, "payments"
            )

            document = Document(
                batch_id=batch_id,
                filename=file.filename,
                file_path=file_path,
                file_size=file_size,
                document_type=DocumentType.PAYMENT,
                uploaded_at=datetime.now(),
            )

            doc_db = doc_repo.create(document)
            batch.payment_documents.append(document)
            uploaded_docs.append(document)

        batch.updated_at = datetime.now()
        batch_repo.update(batch)
        db.commit()  

        logger.info(f"Uploaded {len(files)} payments to batch {batch_id}")

        return {
            "batch_id": batch_id,
            "uploaded_count": len(files),
            "documents": [
                {
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "file_size": doc.file_size,
                }
                for doc in uploaded_docs
            ],
        }

    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batches/{batch_id}/process")
async def process_batch(
    batch_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Start processing a batch through the complete workflow.
    This runs in the background to avoid timeouts.

    Workflow:
    1. OCR → Extract text
    2. Extraction → Get structured data
    3. Matching → Link invoices to payments
    4. Rules → Calculate delays and penalties
    5. Validation check → Determine if human review needed
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Convert to Pydantic
        batch = db_to_pydantic_batch(batch_db)

        # Load documents
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)

        for doc_db in documents:
            doc = Document(
                document_id=doc_db.document_id,
                batch_id=doc_db.batch_id,
                filename=doc_db.filename,
                file_path=doc_db.file_path,
                file_size=doc_db.file_size,
                document_type=DocumentType(doc_db.document_type),
                status=doc_db.status,
                uploaded_at=doc_db.uploaded_at,
            )

            if doc.document_type == DocumentType.INVOICE:
                batch.invoice_documents.append(doc)
            else:
                batch.payment_documents.append(doc)

        # Start background processing (pass batch_id instead of db session)
        background_tasks.add_task(process_workflow_background, batch)

        return {
            "batch_id": batch_id,
            "status": "processing_started",
            "message": "Le traitement a démarré en arrière-plan",
        }

    except Exception as e:
        logger.error(f"Failed to start processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batches/{batch_id}/process/invoices")
async def process_invoices_only(
    batch_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Phase 1: Process invoices only.
    Upload invoices → OCR → Extract → Wait for payment
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Convert to Pydantic
        batch = db_to_pydantic_batch(batch_db)

        # Load documents
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)

        for doc_db in documents:
            doc = Document(
                document_id=doc_db.document_id,
                batch_id=doc_db.batch_id,
                filename=doc_db.filename,
                file_path=doc_db.file_path,
                file_size=doc_db.file_size,
                document_type=DocumentType(doc_db.document_type),
                status=doc_db.status,
                uploaded_at=doc_db.uploaded_at,
            )

            if doc.document_type == DocumentType.INVOICE:
                batch.invoice_documents.append(doc)
            else:
                batch.payment_documents.append(doc)

        # Verify batch has invoices uploaded
        if not batch.invoice_documents:
            raise HTTPException(status_code=400, detail="No invoice documents uploaded")

        # Start background task
        background_tasks.add_task(process_invoices_only_background, batch, db)

        return {
            "batch_id": batch_id,
            "status": "processing",
            "message": "Invoice processing started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start invoice processing: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/batches/{batch_id}/process/complete")
async def complete_with_payments(
    batch_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """
    Phase 2: Add payments and complete processing.
    Requires: batch.status == INVOICES_EXTRACTED
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Verify batch is in correct state
        if batch_db.status != "invoices_extracted":
            raise HTTPException(
                status_code=400,
                detail=f"Invalid batch status: {batch_db.status}. Expected: invoices_extracted",
            )

        # Convert to Pydantic
        batch = db_to_pydantic_batch(batch_db)

        # Load documents
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)

        for doc_db in documents:
            doc = Document(
                document_id=doc_db.document_id,
                batch_id=doc_db.batch_id,
                filename=doc_db.filename,
                file_path=doc_db.file_path,
                file_size=doc_db.file_size,
                document_type=DocumentType(doc_db.document_type),
                status=doc_db.status,
                uploaded_at=doc_db.uploaded_at,
            )

            if doc.document_type == DocumentType.INVOICE:
                batch.invoice_documents.append(doc)
            else:
                batch.payment_documents.append(doc)

        # Verify payments uploaded
        if not batch.payment_documents:
            raise HTTPException(status_code=400, detail="No payment documents uploaded")

        # Start background task
        background_tasks.add_task(process_payments_complete_background, batch, db)

        return {
            "batch_id": batch_id,
            "status": "processing",
            "message": "Payment processing and completion started",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start payment completion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batches/{batch_id}")
async def get_batch(batch_id: str, db: Session = Depends(get_db)):
    """
    Get batch status and details.
    Used by frontend to poll progress.
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # CRITICAL: Force fresh data from database
        db.refresh(batch_db)
        db.expire_all()
        batch_db = batch_repo.get_by_id(batch_id)

        # Get documents
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)

        return {
            "batch_id": batch_db.batch_id,
            "user_id": batch_db.user_id,
            "company_name": batch_db.company_name,
            "company_ice": batch_db.company_ice,
            "status": batch_db.status,
            "current_step": batch_db.current_step,
            "progress_percentage": batch_db.progress_percentage,
            "total_invoices": batch_db.total_invoices,
            "total_payments": batch_db.total_payments,
            "alerts_count": batch_db.alerts_count,
            "critical_alerts_count": batch_db.critical_alerts_count,
            "requires_validation": batch_db.requires_validation,
            "documents": [
                {
                    "document_id": doc.document_id,
                    "filename": doc.filename,
                    "document_type": doc.document_type,
                    "status": doc.status,
                }
                for doc in documents
            ],
            "created_at": batch_db.created_at,
            "updated_at": batch_db.updated_at,
        }

    except Exception as e:
        logger.error(f"Failed to get batch: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batches/{batch_id}/results")
async def get_batch_results(batch_id: str, db: Session = Depends(get_db)):
    """
    Get complete processing results for validation screen.

    Returns:
    - Extracted invoices
    - Extracted payments
    - Matching results
    - Legal calculations
    - Alerts
    - Documents (for PDF viewing)
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # CRITICAL: Force refresh to ensure we get the latest data from database
        # This prevents stale reads when background tasks update the batch
        db.refresh(batch_db)
        
        # Also expire all to be safe with JSON field caching
        db.expire_all()
        
        # Re-fetch after expire to get fresh data
        batch_db = batch_repo.get_by_id(batch_id)

        # Get documents for PDF viewing
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)
        
        documents_list = [
            {
                "document_id": doc.document_id,
                "filename": doc.filename,
                "document_type": doc.document_type,
                "status": doc.status,
            }
            for doc in documents
        ]

        return {
            "batch_id": batch_db.batch_id,
            "status": batch_db.status,
            "invoices": batch_db.invoices_data,
            "payments": batch_db.payments_data,
            "matching_results": batch_db.matching_results,
            "legal_results": batch_db.legal_results,
            "alerts_count": batch_db.alerts_count,
            "critical_alerts_count": batch_db.critical_alerts_count,
            "requires_validation": batch_db.requires_validation,
            "documents": documents_list,
        }

    except Exception as e:
        logger.error(f"Failed to get results: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.patch("/batches/{batch_id}")
async def update_batch(
    batch_id: str,
    update_data: dict,
    db: Session = Depends(get_db)
):
    """
    Update batch data (invoices/payments) before validation.
    Allows users to correct extracted data.
    """
    try:
        logger.info(f"📝 PATCH /batches/{batch_id} - Payload: {update_data}")
        
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Prevent updates to validated batches
        if batch_db.status in ["validated", "exported"]:
            raise HTTPException(
                status_code=400, 
                detail="Cannot update a validated or exported batch"
            )

        # Track if any updates were actually made
        updates_made = False
        invoices_modified = False
        payments_modified = False
        
        # Update invoice data if provided
        invoice_updates = update_data.get("invoice_updates")
        if invoice_updates and len(invoice_updates) > 0:
            logger.info(f"Processing {len(invoice_updates)} invoice updates")
            for update in invoice_updates:
                invoice_id = update.get("invoice_id")
                if not invoice_id:
                    logger.warning("Invoice update missing invoice_id, skipping")
                    continue
                
                # Find and update the invoice
                found = False
                for idx, invoice in enumerate(batch_db.invoices_data or []):
                    if invoice.get("invoice_id") == invoice_id:
                        logger.info(f"Updating invoice {invoice_id} with fields: {list(update.keys())}")
                        
                        # Initialize nested structures if they don't exist
                        if "supplier" not in invoice:
                            invoice["supplier"] = {}
                        if "invoice" not in invoice:
                            invoice["invoice"] = {}
                        if "amounts" not in invoice:
                            invoice["amounts"] = {}
                        
                        # Map flat fields to nested structure - Supplier
                        if "supplier_name" in update:
                            invoice["supplier"]["name"] = update["supplier_name"]
                        if "supplier_ice" in update:
                            invoice["supplier"]["ice"] = update["supplier_ice"]
                        if "supplier_if" in update:
                            invoice["supplier"]["if"] = update["supplier_if"]
                        if "supplier_rc" in update:
                            invoice["supplier"]["rc"] = update["supplier_rc"]
                        if "supplier_address" in update:
                            invoice["supplier"]["address"] = update["supplier_address"]
                        
                        # Invoice fields
                        if "invoice_number" in update:
                            invoice["invoice"]["number"] = update["invoice_number"]
                        if "invoice_issue_date" in update:
                            invoice["invoice"]["issue_date"] = update["invoice_issue_date"]
                        if "invoice_delivery_date" in update:
                            invoice["invoice"]["delivery_date"] = update["invoice_delivery_date"]
                        
                        # Amounts
                        if "invoice_amount_ttc" in update:
                            invoice["amounts"]["total_ttc"] = update["invoice_amount_ttc"]
                        
                        # Line items
                        if "nature_of_goods" in update:
                            if "line_items" not in invoice or not invoice["line_items"]:
                                invoice["line_items"] = [{}]
                            invoice["line_items"][0]["description"] = update["nature_of_goods"]
                        
                        # Delay configuration (store at invoice root level)
                        if "contractual_delay_days" in update:
                            invoice["contractual_delay_days"] = update["contractual_delay_days"]
                        if "sector_delay_days" in update:
                            invoice["sector_delay_days"] = update["sector_delay_days"]
                        if "agreed_payment_date" in update:
                            invoice["agreed_payment_date"] = update["agreed_payment_date"]
                        
                        # Periodic transactions
                        if "is_periodic_transaction" in update:
                            invoice["is_periodic_transaction"] = update["is_periodic_transaction"]
                        if "transaction_month" in update:
                            invoice["transaction_month"] = update["transaction_month"]
                        if "transaction_year" in update:
                            invoice["transaction_year"] = update["transaction_year"]
                        
                        # Public establishment
                        if "service_completion_date" in update:
                            invoice["service_completion_date"] = update["service_completion_date"]
                        
                        # Litigation
                        if "is_disputed" in update:
                            invoice["is_disputed"] = update["is_disputed"]
                        if "litigation_amount" in update:
                            invoice["litigation_amount"] = update["litigation_amount"]
                        if "judicial_recourse_date" in update:
                            invoice["judicial_recourse_date"] = update["judicial_recourse_date"]
                        if "judgment_date" in update:
                            invoice["judgment_date"] = update["judgment_date"]
                        if "penalty_suspension_months" in update:
                            invoice["penalty_suspension_months"] = update["penalty_suspension_months"]
                        
                        # Update the invoice in the array
                        batch_db.invoices_data[idx] = invoice
                        updates_made = True
                        invoices_modified = True
                        found = True
                        logger.info(f"✓ Updated invoice {invoice_id} nested structure")
                        break
                
                if not found:
                    logger.warning(f"Invoice {invoice_id} not found in batch data")

        # Update payment data if provided
        payment_updates = update_data.get("payment_updates")
        if payment_updates and len(payment_updates) > 0:
            logger.info(f"Processing {len(payment_updates)} payment updates")
            for update in payment_updates:
                payment_id = update.get("payment_id")
                if not payment_id:
                    logger.warning("Payment update missing payment_id, skipping")
                    continue
                
                # Find and update the payment
                found = False
                for idx, payment in enumerate(batch_db.payments_data or []):
                    if payment.get("payment_id") == payment_id:
                        logger.info(f"Updating payment {payment_id} with fields: {list(update.keys())}")
                        
                        # Map flat fields to payment structure
                        if "payment_date" in update:
                            payment["date"] = str(update["payment_date"])
                        if "payment_amount_paid" in update:
                            # Ensure numeric value is preserved (use float for precision)
                            payment["amount"] = float(update["payment_amount_paid"])
                            logger.info(f"  - Setting payment amount to: {payment['amount']} (type: {type(payment['amount'])})")
                        if "payment_amount_unpaid" in update:
                            payment["amount_unpaid"] = float(update["payment_amount_unpaid"])
                            logger.info(f"  - Setting unpaid amount to: {payment['amount_unpaid']}")
                        if "payment_reference" in update:
                            payment["reference"] = str(update["payment_reference"])
                        if "payment_mode" in update:
                            payment["payment_mode"] = str(update["payment_mode"])
                        
                        # Update the payment in the array
                        batch_db.payments_data[idx] = payment
                        updates_made = True
                        payments_modified = True
                        found = True
                        logger.info(f"✓ Updated payment {payment_id}")
                        break
                
                if not found:
                    logger.warning(f"Payment {payment_id} not found in batch data")

        # Only commit if updates were actually made
        if updates_made:
            # CRITICAL: Mark JSON fields as modified so SQLAlchemy knows to save them
            if invoices_modified:
                flag_modified(batch_db, "invoices_data")
                logger.info("Marked invoices_data as modified")
            if payments_modified:
                flag_modified(batch_db, "payments_data")
                logger.info("Marked payments_data as modified")
                
                # Also update matching_results to reflect new payment amounts/dates
                logger.info(f"Checking matching_results: {batch_db.matching_results is not None}")
                if batch_db.matching_results and len(batch_db.matching_results) > 0:
                    logger.info(f"Found {len(batch_db.matching_results)} matching results to update")
                    for match_result in batch_db.matching_results:
                        # matching_results has structure: {matches: [{payment_id: ...}], total_paid: ..., payment_dates: [...]}
                        # Find the payment ID from the nested matches array
                        if "matches" in match_result and len(match_result["matches"]) > 0:
                            matched_payment_id = match_result["matches"][0].get("payment_id")
                            logger.info(f"Looking for payment {matched_payment_id} in payments_data")
                            
                            # Find the updated payment
                            for payment in batch_db.payments_data:
                                if payment.get("payment_id") == matched_payment_id:
                                    # Update matching result with new payment data
                                    logger.info(f"✓ Syncing payment {payment.get('payment_id')} to matching_results")
                                    if "date" in payment:
                                        match_result["payment_dates"] = [str(payment["date"])]
                                        logger.info(f"  - Updated payment_dates to {payment['date']}")
                                    if "amount" in payment:
                                        # Ensure float precision is maintained
                                        match_result["total_paid"] = float(payment["amount"])
                                        logger.info(f"  - Updated total_paid to {match_result['total_paid']} (type: {type(match_result['total_paid'])})")
                                    if "reference" in payment:
                                        match_result["payment_reference"] = str(payment["reference"])
                                        logger.info(f"  - Updated payment_reference to {payment['reference']}")
                                    break
                    flag_modified(batch_db, "matching_results")
                    logger.info("Marked matching_results as modified")
                else:
                    logger.warning("No matching_results found to update - payment changes may not be visible in frontend")
            
            batch_db.updated_at = datetime.now()
            db.commit()
            db.refresh(batch_db)
            logger.info(f"✅ Batch {batch_id} updated and committed to database")
            
            # CRITICAL: Recalculate legal results if invoice dates were modified
            # This ensures legal_due_date is updated when delivery_date changes
            if invoices_modified:
                logger.info(f"🔄 Auto-recalculating legal results due to invoice date changes")
                try:
                    # Get fresh data after commit
                    invoices = batch_db.invoices_data or []
                    matching_results = batch_db.matching_results or []
                    
                    if invoices:
                        import httpx
                        intelligence_url = "http://intelligence-service:8004"
                        legal_results = []
                        
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            for invoice in invoices:
                                invoice_id = invoice.get("invoice_id")
                                
                                # Find matching result or create default empty one for invoice-only drafts
                                match_result = next(
                                    (m for m in matching_results if m.get("invoice_id") == invoice_id),
                                    None
                                )
                                
                                # If no matching result, create a default one for legal calculation
                                if not match_result:
                                    match_result = {
                                        "invoice_id": invoice_id,
                                        "matches": [],
                                        "total_paid": 0.0,
                                        "payment_dates": [],
                                        "confidence": 0.0,
                                        "status": "unpaid"
                                    }
                                    logger.info(f"Created default matching result for invoice-only draft {invoice_id}")
                                
                                try:
                                    response = await client.post(
                                        f"{intelligence_url}/rules/compute",
                                        json={
                                            "invoice": invoice,
                                            "matching_result": match_result,
                                            "contractual_delay_days": invoice.get("contractual_delay_days", 0) or 0,
                                            "is_disputed": invoice.get("is_disputed", False) or False,
                                            "is_credit_note": False,
                                            "is_procedure_690": False
                                        }
                                    )
                                    response.raise_for_status()
                                    legal_result = response.json()
                                    legal_results.append(legal_result)
                                    logger.info(f"✓ Recalculated legal for invoice {invoice_id}: due_date={legal_result.get('legal_due_date')}")
                                except Exception as e:
                                    logger.error(f"Failed to recalculate for invoice {invoice_id}: {e}")
                        
                        # Update legal results in database
                        if legal_results:
                            batch_db.legal_results = legal_results
                            flag_modified(batch_db, "legal_results")
                            
                            # Recalculate alerts
                            all_alerts = []
                            critical_count = 0
                            for legal in legal_results:
                                alerts = legal.get("alerts", [])
                                all_alerts.extend(alerts)
                                critical_count += sum(1 for a in alerts if a.get("severity") == "CRITICAL")
                            
                            batch_db.alerts_count = len(all_alerts)
                            batch_db.critical_alerts_count = critical_count
                            batch_db.requires_validation = critical_count > 0 or any(
                                legal.get("requires_manual_review", False) for legal in legal_results
                            )
                            
                            db.commit()
                            db.refresh(batch_db)
                            logger.info(f"✅ Auto-recalculated legal results saved for batch {batch_id}")
                except Exception as e:
                    logger.error(f"⚠️ Auto-recalculation failed (non-critical): {e}")
                    # Don't fail the update if recalculation fails
                    import traceback
                    logger.error(traceback.format_exc())
        else:
            logger.info(f"ℹ️ No updates applied to batch {batch_id} (empty or invalid updates)")

        # Log update action
        if update_data.get("user_id") and updates_made:
            audit_repo = AuditLogRepository(db)
            audit_repo.log_action(
                batch_id=batch_id,
                user_id=update_data["user_id"],
                action="updated",
                entity_type="batch",
            )
            db.commit()

        return {
            "batch_id": batch_id,
            "status": "updated" if updates_made else "no_changes",
            "message": "Batch data updated successfully" if updates_made else "No updates applied",
            "updates_made": updates_made
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ Update failed for batch {batch_id}:")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Traceback:\n{error_trace}")
        logger.error(f"Payload received: {update_data}")
        db.rollback()
        # Return detailed error in development, generic in production
        detail = f"Update failed: {str(e)}" if logger.level <= 20 else "Erreur lors de la mise à jour"
        raise HTTPException(status_code=500, detail=detail)

@app.post("/batches/{batch_id}/recalculate")
async def recalculate_legal_results(
    batch_id: str,
    db: Session = Depends(get_db),
):
    """
    Recalculate legal results (penalties, delays) after payment updates.
    This is a lightweight operation that only recalculates legal compliance
    without reprocessing OCR or extraction.
    """
    try:
        import httpx
        
        logger.info(f"🔄 Recalculating legal results for batch {batch_id}")
        
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Get current data
        invoices = batch_db.invoices_data or []
        payments = batch_db.payments_data or []
        matching_results = batch_db.matching_results or []
        
        if not invoices or not matching_results:
            raise HTTPException(status_code=400, detail="Batch must have invoices and matching results")

        # Recalculate legal results using intelligence service via HTTP
        intelligence_url = "http://intelligence-service:8004"
        legal_results = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for invoice in invoices:
                invoice_id = invoice.get("invoice_id")
                
                # Find matching result for this invoice
                match_result = next(
                    (m for m in matching_results if m.get("invoice_id") == invoice_id),
                    None
                )
                
                if not match_result:
                    logger.warning(f"No matching result for invoice {invoice_id}")
                    continue
                
                # Calculate legal compliance via HTTP call to /rules/compute
                try:
                    response = await client.post(
                        f"{intelligence_url}/rules/compute",
                        json={
                            "invoice": invoice,
                            "matching_result": match_result,
                            "contractual_delay_days": invoice.get("contractual_delay_days", 0) or 0,
                            "is_disputed": invoice.get("is_disputed", False) or False,
                            "is_credit_note": False,
                            "is_procedure_690": False
                        }
                    )
                    response.raise_for_status()
                    legal_result = response.json()
                    legal_results.append(legal_result)
                except Exception as e:
                    logger.error(f"Failed to calculate legal compliance for invoice {invoice_id}: {e}")
                    raise
        
        # Update batch with new legal results
        batch_db.legal_results = legal_results
        flag_modified(batch_db, "legal_results")
        
        # Recalculate alerts and validation requirements
        all_alerts = []
        critical_count = 0
        for legal in legal_results:
            alerts = legal.get("alerts", [])
            all_alerts.extend(alerts)
            critical_count += sum(1 for a in alerts if a.get("severity") == "CRITICAL")
        
        batch_db.alerts_count = len(all_alerts)
        batch_db.critical_alerts_count = critical_count
        batch_db.requires_validation = critical_count > 0 or any(
            legal.get("requires_manual_review", False) for legal in legal_results
        )
        
        db.commit()
        db.refresh(batch_db)
        
        logger.info(f"✅ Legal results recalculated for batch {batch_id}")
        
        return {
            "batch_id": batch_id,
            "status": "recalculated",
            "message": "Legal results recalculated successfully",
            "legal_results": legal_results
        }

    except Exception as e:
        logger.error(f"❌ Recalculation failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batches/{batch_id}/validate")
async def validate_batch(
    batch_id: str,
    validation: BatchValidationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Apply user validation corrections"""
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        batch = db_to_pydantic_batch(batch_db)

        # Log validation action
        audit_repo = AuditLogRepository(db)
        audit_repo.log_action(
            batch_id=batch_id,
            user_id=validation.user_id,
            action="validated",
            entity_type="batch",
        )
        db.commit()  # ADD THIS - Commit audit log

        # Apply validation in background
        background_tasks.add_task(
            apply_validation_background,
            batch,
            validation.invoice_updates,
            validation.user_id,
            db,
        )

        return {
            "batch_id": batch_id,
            "status": "validation_processing",
            "message": "Validation en cours de traitement",
        }

    except Exception as e:
        logger.error(f"Validation failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batches/{batch_id}/export/csv")
async def export_csv(batch_id: str, db: Session = Depends(get_db)):
    """
    Export DGI declaration as CSV.
    """
    try:
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        if not batch_db.dgi_declaration:
            raise HTTPException(
                status_code=400,
                detail="DGI declaration not ready. Complete validation first.",
            )

        # Call intelligence service to generate CSV
        

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.INTELLIGENCE_SERVICE_URL}/dgi/export/csv",
                json=batch_db.dgi_declaration,
            )
            response.raise_for_status()

            csv_content = response.content

        # Update export timestamp
        batch_db.exported_at = datetime.now()
        db.commit()

        # Log export action
        audit_repo = AuditLogRepository(db)
        audit_repo.log_action(
            batch_id=batch_id,
            user_id=batch_db.user_id,
            action="exported",
            entity_type="batch",
        )

        filename = f"DGI_Declaration_{batch_db.company_ice}_{datetime.now().strftime('%Y%m%d')}.csv"

        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/batches/{batch_id}/audit-log")
async def get_audit_log(batch_id: str, db: Session = Depends(get_db)):
    """
    Get audit trail for a batch (Section 10 - Security).
    Shows who modified what and when.
    """
    try:
        audit_repo = AuditLogRepository(db)
        logs = audit_repo.get_batch_logs(batch_id)

        return {
            "batch_id": batch_id,
            "logs": [
                {
                    "log_id": log.log_id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "entity_type": log.entity_type,
                    "entity_id": log.entity_id,
                    "field_name": log.field_name,
                    "old_value": log.old_value,
                    "new_value": log.new_value,
                    "timestamp": log.timestamp,
                }
                for log in logs
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get audit log: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/users/{user_id}/batches")
async def get_user_batches(
    user_id: str, limit: int = 50, db: Session = Depends(get_db)
):
    """Get all batches for a user - powers dashboard and list page"""
    try:
        batch_repo = BatchRepository(db)
        doc_repo = DocumentRepository(db)
        batches = batch_repo.get_by_user(user_id, limit)
        
        logger.info(f"📊 Found {len(batches)} batches for user {user_id}")
        
        # IMPORTANT: Frontend expects data in this exact structure
        batch_list = []
        for batch in batches:
            batch_data = {
                "batch_id": batch.batch_id,
                "user_id": batch.user_id,
                "company_name": batch.company_name,
                "company_ice": batch.company_ice,
                "company_rc": batch.company_rc,
                "status": batch.status,
                "current_step": batch.current_step,
                "progress_percentage": batch.progress_percentage,
                "total_invoices": batch.total_invoices,
                "total_payments": batch.total_payments,
                "alerts_count": batch.alerts_count,
                "critical_alerts_count": batch.critical_alerts_count,
                "requires_validation": batch.requires_validation,
                "created_at": batch.created_at.isoformat() if batch.created_at else None,
                "updated_at": batch.updated_at.isoformat() if batch.updated_at else None,
                "validated_at": batch.validated_at.isoformat() if batch.validated_at else None,
                "exported_at": batch.exported_at.isoformat() if batch.exported_at else None,
            }
            
            # Include full data for validated/exported batches (needed for Registre DGI)
            if batch.status in ["validated", "exported"]:
                batch_data["invoices_data"] = batch.invoices_data or []
                batch_data["payments_data"] = batch.payments_data or []
                batch_data["legal_results"] = batch.legal_results or []
                batch_data["matching_results"] = batch.matching_results or []
                
                # Include documents for PDF viewing
                documents = doc_repo.get_by_batch(batch.batch_id)
                batch_data["documents"] = [
                    {
                        "document_id": doc.document_id,
                        "filename": doc.filename,
                        "document_type": doc.document_type,
                        "status": doc.status,
                    }
                    for doc in documents
                ]
            
            batch_list.append(batch_data)
        
        return {
            "user_id": user_id,
            "total": len(batches),
            "batches": batch_list
        }

    except Exception as e:
        logger.error(f"❌ Failed to get user batches: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/batches/{batch_id}/documents/{document_id}/pdf")
async def get_document_pdf(
    batch_id: str,
    document_id: str,
    db: Session = Depends(get_db)
):
    """
    Serve PDF document for viewing.
    Used by frontend to display invoice and payment PDFs.
    """
    try:
        from fastapi.responses import FileResponse
        import os
        
        logger.info(f"📄 PDF request: batch={batch_id}, document={document_id}")
        
        doc_repo = DocumentRepository(db)
        documents = doc_repo.get_by_batch(batch_id)
        
        logger.info(f"📄 Found {len(documents)} documents for batch {batch_id}")
        
        # Find the document
        document = None
        for doc in documents:
            logger.info(f"📄 Checking document: {doc.document_id} (type: {doc.document_type})")
            if doc.document_id == document_id:
                document = doc
                break
        
        if not document:
            logger.error(f"❌ Document {document_id} not found in batch {batch_id}")
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
        
        logger.info(f"📄 Document found: {document.filename}, path: {document.file_path}")
        
        # Check if file exists
        if not os.path.exists(document.file_path):
            logger.error(f"❌ File not found at path: {document.file_path}")
            logger.info(f"📁 Checking if file exists in shared volume...")
            
            # Try to list directory contents for debugging
            import pathlib
            file_dir = pathlib.Path(document.file_path).parent
            if file_dir.exists():
                logger.info(f"📁 Directory exists: {file_dir}")
                logger.info(f"📁 Directory contents: {list(file_dir.iterdir())}")
            else:
                logger.error(f"❌ Directory does not exist: {file_dir}")
            
            raise HTTPException(status_code=404, detail=f"PDF file not found at {document.file_path}")
        
        logger.info(f"✅ Serving PDF: {document.filename}")
        
        # Return the PDF file
        return FileResponse(
            path=document.file_path,
            media_type="application/pdf",
            filename=document.filename
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error serving PDF: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    db: Session = Depends(get_db)
):
    """
    Delete a batch (only allowed for draft/pending batches, not validated ones).
    """
    try:
        logger.info(f"🗑️ DELETE /batches/{batch_id}")
        
        batch_repo = BatchRepository(db)
        batch_db = batch_repo.get_by_id(batch_id)

        if not batch_db:
            raise HTTPException(status_code=404, detail="Batch not found")

        # Prevent deletion of validated or exported batches
        if batch_db.status in ["validated", "exported"]:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a validated or exported batch"
            )

        # Delete the batch
        db.delete(batch_db)
        db.commit()
        
        logger.info(f"✅ Batch {batch_id} deleted successfully")

        return {
            "batch_id": batch_id,
            "status": "deleted",
            "message": "Batch deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "orchestrator-service", "version": "1.0.0"}


# =============================================================================
# BACKGROUND TASKS
# =============================================================================

async def process_workflow_background(batch: Batch):
    """Background task to process the complete workflow"""
    # Create fresh database session for background task
    db = SessionLocal()
    try:
        batch_repo = BatchRepository(db)

        # Execute workflow
        batch = await orchestrator.process_complete_workflow(batch)

        # CRITICAL: Commit results to database
        batch_repo.update(batch)
        db.commit()

        logger.info(f"✅ Workflow completed for batch {batch.batch_id}")

    except Exception as e:
        logger.error(f"Background processing failed: {str(e)}")
        batch.status = BatchStatus.FAILED
        batch.error_message = str(e)
        batch_repo = BatchRepository(db)
        batch_repo.update(batch)
        db.commit()
    finally:
        db.close()


async def apply_validation_background(
    batch: Batch,
    updates: List[InvoiceValidationUpdate],
    user_id: str,
    db: Session,
):
    """Background task to apply user validation"""
    try:
        batch_repo = BatchRepository(db)

        # Apply human validation
        batch = await orchestrator.apply_user_validation(batch, updates)

        # Generate DGI declaration
        await orchestrator.generate_dgi_declaration(batch)

        batch.validated_by = user_id
        batch.validated_at = datetime.now()

        # CRITICAL: Persist final state
        batch_repo.update(batch)
        db.commit()  # ADD THIS

        logger.info(f"✅ Validation completed for batch {batch.batch_id}")

    except Exception as e:
        logger.error(f"Validation processing failed: {str(e)}")
        batch.status = BatchStatus.FAILED
        batch.error_message = str(e)
        batch_repo = BatchRepository(db)
        batch_repo.update(batch)
        db.commit()  # ADD THIS - Even on failure


async def process_invoices_only_background(batch: Batch, db: Session):
    """Background task to process invoices only (Phase 1)"""
    try:
        batch_repo = BatchRepository(db)

        # Execute invoice-only workflow
        batch = await orchestrator.process_invoices_only(batch)

        # CRITICAL: Commit results to database
        batch_repo.update(batch)
        db.commit()

        logger.info(f"✅ Invoice-only processing completed for batch {batch.batch_id}")

    except Exception as e:
        logger.error(f"Invoice-only background processing failed: {str(e)}")
        batch.status = BatchStatus.FAILED
        batch.error_message = str(e)
        batch_repo = BatchRepository(db)
        batch_repo.update(batch)
        db.commit()


async def process_payments_complete_background(batch: Batch, db: Session):
    """Background task to complete workflow with payments (Phase 2)"""
    try:
        batch_repo = BatchRepository(db)

        # Execute payment completion workflow
        batch = await orchestrator.process_payments_and_complete(batch)

        # CRITICAL: Commit results to database
        batch_repo.update(batch)
        db.commit()

        logger.info(f"✅ Payment completion workflow finished for batch {batch.batch_id}")

    except Exception as e:
        logger.error(f"Payment completion background processing failed: {str(e)}")
        batch.status = BatchStatus.FAILED
        batch.error_message = str(e)
        batch_repo = BatchRepository(db)
        batch_repo.update(batch)
        db.commit()

        
# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def db_to_pydantic_batch(batch_db: BatchDB) -> Batch:
    """
    Convert SQLAlchemy BatchDB model to Pydantic Batch model.
    Used to decouple persistence from business logic.
    """
    return Batch(
        batch_id=batch_db.batch_id,
        user_id=batch_db.user_id,
        company_name=batch_db.company_name,
        company_ice=batch_db.company_ice,
        company_rc=batch_db.company_rc,
        status=BatchStatus(batch_db.status),
        current_step=batch_db.current_step,
        progress_percentage=batch_db.progress_percentage,
        total_invoices=batch_db.total_invoices,
        total_payments=batch_db.total_payments,
        invoices_data=batch_db.invoices_data or [],
        payments_data=batch_db.payments_data or [],
        matching_results=batch_db.matching_results or [],
        legal_results=batch_db.legal_results or [],
        dgi_declaration=batch_db.dgi_declaration,
        alerts_count=batch_db.alerts_count,
        critical_alerts_count=batch_db.critical_alerts_count,
        requires_validation=batch_db.requires_validation,
        validated_by=batch_db.validated_by,
        validated_at=batch_db.validated_at,
        created_at=batch_db.created_at,
        updated_at=batch_db.updated_at,
        exported_at=batch_db.exported_at,
        error_message=batch_db.error_message,
        failed_documents=batch_db.failed_documents or [],
    )
