from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from enum import Enum


class PaymentStatus(str, Enum):
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"
    UNPAID = "UNPAID"


class Match(BaseModel):
    payment_id: str
    matched_amount: float
    confidence_score: float  # 0-100
    matching_reasons: List[str]


class MatchingResult(BaseModel):
    invoice_id: str
    matches: List[Match]
    payment_status: PaymentStatus
    total_paid: float
    remaining_amount: float
    payment_dates: List[date]
