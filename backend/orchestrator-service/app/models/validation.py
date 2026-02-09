from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date

class InvoiceValidationUpdate(BaseModel):
    """User updates to an invoice during validation"""
    invoice_id: str
    
    # Fields that can be manually corrected
    delivery_date: Optional[date] = None
    issue_date: Optional[date] = None
    supplier_name: Optional[str] = None
    supplier_ice: Optional[str] = None
    invoice_number: Optional[str] = None
    amount_ttc: Optional[float] = None
    
    # Special statuses
    is_disputed: bool = False
    is_credit_note: bool = False
    dispute_reason: Optional[str] = None
    
    # Contractual delay override
    contractual_delay_days: Optional[int] = None

class BatchValidationRequest(BaseModel):
    """Validation submission from user"""
    batch_id: str
    user_id: str
    invoice_updates: List[InvoiceValidationUpdate] = []
    
    # Global settings
    disputed_invoice_ids: List[str] = []
    credit_note_ids: List[str] = []
    
    # User confirmation
    delivery_dates_confirmed: bool = False
    amounts_confirmed: bool = False

class ValidationAlert(BaseModel):
    """Alert that requires user attention"""
    alert_id: str
    invoice_id: str
    severity: str  # "INFO", "WARNING", "ERROR", "CRITICAL"
    code: str
    message: str
    field: Optional[str] = None
    suggested_action: Optional[str] = None