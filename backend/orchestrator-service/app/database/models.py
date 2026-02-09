from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, Text, JSON, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from .connection import Base
import enum

class BatchStatusEnum(str, enum.Enum):
    CREATED = "created"
    UPLOADING = "uploading"
    OCR_PROCESSING = "ocr_processing"
    INVOICES_OCR_PROCESSING = "invoices_ocr_processing"
    INVOICES_EXTRACTED = "invoices_extracted"
    EXTRACTION_DONE = "extraction_done"
    MATCHING_DONE = "matching_done"
    RULES_CALCULATED = "rules_calculated"
    VALIDATION_PENDING = "validation_pending"
    VALIDATED = "validated"
    EXPORTED = "exported"
    FAILED = "failed"

class DocumentTypeEnum(str, enum.Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"

class BatchDB(Base):
    """Database model for processing batches"""
    __tablename__ = "batches"
    
    batch_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    company_ice = Column(String, nullable=False)
    company_rc = Column(String, nullable=True)
    
    # Status
    status = Column(Enum(BatchStatusEnum), default=BatchStatusEnum.CREATED)
    current_step = Column(String, default="Upload")
    progress_percentage = Column(Float, default=0.0)
    
    # Counts
    total_invoices = Column(Integer, default=0)
    total_payments = Column(Integer, default=0)
    alerts_count = Column(Integer, default=0)
    critical_alerts_count = Column(Integer, default=0)
    
    # Processing results (stored as JSON)
    invoices_data = Column(JSON, default=list)
    payments_data = Column(JSON, default=list)
    matching_results = Column(JSON, default=list)
    legal_results = Column(JSON, default=list)
    dgi_declaration = Column(JSON, nullable=True)
    
    # Validation
    requires_validation = Column(Boolean, default=False)
    validated_by = Column(String, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    exported_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    failed_documents = Column(JSON, default=list)
    
    # Two-phase upload mode
    invoice_only_mode = Column(Boolean, default=False)
    
    # Relationships
    documents = relationship("DocumentDB", back_populates="batch", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLogDB", back_populates="batch", cascade="all, delete-orphan")

class DocumentDB(Base):
    """Database model for uploaded documents"""
    __tablename__ = "documents"
    
    document_id = Column(String, primary_key=True, index=True)
    batch_id = Column(String, ForeignKey("batches.batch_id"), nullable=False)
    
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size = Column(Integer, default=0)
    document_type = Column(Enum(DocumentTypeEnum), nullable=False)
    
    # Processing status
    status = Column(String, default="uploaded")
    ocr_text = Column(Text, nullable=True)
    extracted_data = Column(JSON, nullable=True)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.now)
    processed_at = Column(DateTime, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    # Relationships
    batch = relationship("BatchDB", back_populates="documents")

class AuditLogDB(Base):
    """Audit trail for user actions (Section 10 - Security)"""
    __tablename__ = "audit_logs"
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    batch_id = Column(String, ForeignKey("batches.batch_id"), nullable=False)
    user_id = Column(String, nullable=False)
    
    action = Column(String, nullable=False)  # "created", "updated", "validated", "exported"
    entity_type = Column(String, nullable=False)  # "batch", "invoice", "payment"
    entity_id = Column(String, nullable=True)
    
    # Change tracking
    field_name = Column(String, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    
    timestamp = Column(DateTime, default=datetime.now)
    
    # Relationships
    batch = relationship("BatchDB", back_populates="audit_logs")