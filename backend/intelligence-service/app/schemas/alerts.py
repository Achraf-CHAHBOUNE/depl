from pydantic import BaseModel
from typing import Optional
from enum import Enum


class AlertSeverity(str, Enum):
    """Alert severity levels for DGI compliance"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class AlertCode(str, Enum):
    """Standardized alert codes for DGI compliance"""
    # Missing data alerts
    MISSING_DELIVERY_DATE = "MISSING_DELIVERY_DATE"
    MISSING_ISSUE_DATE = "MISSING_ISSUE_DATE"
    MISSING_PAYMENT_DATE = "MISSING_PAYMENT_DATE"
    MISSING_INVOICE_AMOUNT = "MISSING_INVOICE_AMOUNT"
    MISSING_CONTRACTUAL_DELAY = "MISSING_CONTRACTUAL_DELAY"
    
    # Legal compliance alerts
    CONTRACTUAL_DELAY_EXCEEDS_MAX = "CONTRACTUAL_DELAY_EXCEEDS_MAX"
    PAYMENT_BEFORE_INVOICE = "PAYMENT_BEFORE_INVOICE"
    EXCESSIVE_DELAY = "EXCESSIVE_DELAY"
    
    # Status alerts
    DISPUTED_INVOICE = "DISPUTED_INVOICE"
    CREDIT_NOTE = "CREDIT_NOTE"
    PROCEDURE_690 = "PROCEDURE_690"
    
    # Data quality
    LOW_CONFIDENCE_MATCH = "LOW_CONFIDENCE_MATCH"
    PARTIAL_PAYMENT_DETECTED = "PARTIAL_PAYMENT_DETECTED"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"


class Alert(BaseModel):
    """
    Alert for DGI compliance issues and data quality.
    All alerts are logged for audit trail.
    """
    code: AlertCode
    severity: AlertSeverity
    message: str
    field: Optional[str] = None
    
    class Config:
        use_enum_values = True