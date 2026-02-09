from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class BatchStatus(str, Enum):
    """Workflow states for a processing batch"""
    CREATED = "created"
    UPLOADING = "uploading"
    OCR_PROCESSING = "ocr_processing"
    INVOICES_OCR_PROCESSING = "invoices_ocr_processing"
    INVOICES_EXTRACTED = "invoices_extracted"
    EXTRACTION_DONE = "extraction_done"
    MATCHING_DONE = "matching_done"
    RULES_CALCULATED = "rules_calculated"
    VALIDATION_PENDING = "validation_pending"  # Human-in-the-loop
    VALIDATED = "validated"
    EXPORTED = "exported"
    FAILED = "failed"

class DocumentType(str, Enum):
    INVOICE = "invoice"
    PAYMENT = "payment"

class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    OCR_PROCESSING = "ocr_processing"
    OCR_DONE = "ocr_done"
    EXTRACTION_DONE = "extraction_done"
    FAILED = "failed"

class Document(BaseModel):
    """Represents an uploaded document"""
    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    batch_id: str
    filename: str
    file_path: str
    document_type: DocumentType
    status: DocumentStatus = DocumentStatus.UPLOADED
    
    # Processing results
    ocr_text: Optional[str] = None
    extracted_data: Optional[Dict[str, Any]] = None
    
    # Metadata
    file_size: int = 0
    uploaded_at: datetime = Field(default_factory=datetime.now)
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None

class Batch(BaseModel):
    """Processing batch containing invoices and payments"""
    batch_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None
    
    # Status tracking
    status: BatchStatus = BatchStatus.CREATED
    current_step: str = "Upload"
    progress_percentage: float = 0.0
    
    # Documents
    invoice_documents: List[Document] = []
    payment_documents: List[Document] = []
    
    # Counts
    total_invoices: int = 0
    total_payments: int = 0
    
    # Processing results (stored as JSON)
    invoices_data: List[Dict[str, Any]] = []
    payments_data: List[Dict[str, Any]] = []
    matching_results: List[Dict[str, Any]] = []
    legal_results: List[Dict[str, Any]] = []
    dgi_declaration: Optional[Dict[str, Any]] = None
    
    # Alerts and validation
    alerts_count: int = 0
    critical_alerts_count: int = 0
    requires_validation: bool = False
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    validated_at: Optional[datetime] = None
    validated_by: Optional[str] = None
    exported_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    failed_documents: List[str] = []

class BatchCreateRequest(BaseModel):
    """Request to create a new batch"""
    user_id: str
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None

class BatchResponse(BaseModel):
    """Response with batch information"""
    batch_id: str
    status: BatchStatus
    current_step: str
    progress_percentage: float
    total_invoices: int
    total_payments: int
    alerts_count: int
    created_at: datetime
    updated_at: datetime