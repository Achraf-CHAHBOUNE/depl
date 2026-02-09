from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from typing import List, Optional
from datetime import datetime
from .models import BatchDB, DocumentDB, AuditLogDB
from ..models.batch import Batch, Document

class BatchRepository:
    """Data access layer for batches"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, batch: Batch) -> BatchDB:
        """Create a new batch"""
        batch_db = BatchDB(
            batch_id=batch.batch_id,
            user_id=batch.user_id,
            company_name=batch.company_name,
            company_ice=batch.company_ice,
            company_rc=batch.company_rc,
            status=batch.status,
            current_step=batch.current_step,
            progress_percentage=batch.progress_percentage,
            created_at=batch.created_at,
            updated_at=batch.updated_at
        )
        
        self.db.add(batch_db)
        self.db.commit()
        self.db.refresh(batch_db)
        return batch_db
    
    def get_by_id(self, batch_id: str) -> Optional[BatchDB]:
        """Get batch by ID"""
        return self.db.query(BatchDB).filter(BatchDB.batch_id == batch_id).first()
    
    def get_by_user(self, user_id: str, limit: int = 50) -> List[BatchDB]:
        """Get all batches for a user"""
        return (
            self.db.query(BatchDB)
            .filter(BatchDB.user_id == user_id)
            .order_by(BatchDB.created_at.desc())
            .limit(limit)
            .all()
        )
    
    def update(self, batch: Batch) -> BatchDB:
        """Update existing batch"""
        batch_db = self.get_by_id(batch.batch_id)
        if not batch_db:
            raise ValueError(f"Batch {batch.batch_id} not found")
        
        # Update fields
        batch_db.status = batch.status
        batch_db.current_step = batch.current_step
        batch_db.progress_percentage = batch.progress_percentage
        batch_db.total_invoices = batch.total_invoices
        batch_db.total_payments = batch.total_payments
        batch_db.alerts_count = batch.alerts_count
        batch_db.critical_alerts_count = batch.critical_alerts_count
        batch_db.invoices_data = batch.invoices_data
        batch_db.payments_data = batch.payments_data
        batch_db.matching_results = batch.matching_results
        batch_db.legal_results = batch.legal_results
        batch_db.dgi_declaration = batch.dgi_declaration
        batch_db.requires_validation = batch.requires_validation
        batch_db.validated_by = batch.validated_by
        batch_db.validated_at = batch.validated_at
        batch_db.exported_at = batch.exported_at
        batch_db.error_message = batch.error_message
        batch_db.failed_documents = batch.failed_documents
        batch_db.updated_at = datetime.now()
        
        # CRITICAL: Mark JSON fields as modified so SQLAlchemy persists changes
        flag_modified(batch_db, "invoices_data")
        flag_modified(batch_db, "payments_data")
        flag_modified(batch_db, "matching_results")
        flag_modified(batch_db, "legal_results")
        flag_modified(batch_db, "dgi_declaration")
        flag_modified(batch_db, "failed_documents")
        
        self.db.commit()
        self.db.refresh(batch_db)
        return batch_db
    
    def delete(self, batch_id: str):
        """Delete batch"""
        batch_db = self.get_by_id(batch_id)
        if batch_db:
            self.db.delete(batch_db)
            self.db.commit()

class DocumentRepository:
    """Data access layer for documents"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create(self, document: Document) -> DocumentDB:
        """Create a new document"""
        doc_db = DocumentDB(
            document_id=document.document_id,
            batch_id=document.batch_id,
            filename=document.filename,
            file_path=document.file_path,
            file_size=document.file_size,
            document_type=document.document_type,
            status=document.status,
            uploaded_at=document.uploaded_at
        )
        
        self.db.add(doc_db)
        self.db.commit()
        self.db.refresh(doc_db)
        return doc_db
    
    def get_by_batch(self, batch_id: str) -> List[DocumentDB]:
        """Get all documents for a batch"""
        return self.db.query(DocumentDB).filter(DocumentDB.batch_id == batch_id).all()
    
    def update(self, document: Document) -> DocumentDB:
        """Update document"""
        doc_db = self.db.query(DocumentDB).filter(
            DocumentDB.document_id == document.document_id
        ).first()
        
        if not doc_db:
            raise ValueError(f"Document {document.document_id} not found")
        
        doc_db.status = document.status
        doc_db.ocr_text = document.ocr_text
        doc_db.extracted_data = document.extracted_data
        doc_db.processed_at = document.processed_at
        doc_db.error_message = document.error_message
        
        self.db.commit()
        self.db.refresh(doc_db)
        return doc_db

class AuditLogRepository:
    """Data access layer for audit logs (Section 10 - Security)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def log_action(
        self,
        batch_id: str,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str = None,
        field_name: str = None,
        old_value: str = None,
        new_value: str = None
    ):
        """Create audit log entry"""
        log = AuditLogDB(
            batch_id=batch_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            timestamp=datetime.now()
        )
        
        self.db.add(log)
        self.db.commit()
    
    def get_batch_logs(self, batch_id: str) -> List[AuditLogDB]:
        """Get all logs for a batch"""
        return (
            self.db.query(AuditLogDB)
            .filter(AuditLogDB.batch_id == batch_id)
            .order_by(AuditLogDB.timestamp.desc())
            .all()
        )