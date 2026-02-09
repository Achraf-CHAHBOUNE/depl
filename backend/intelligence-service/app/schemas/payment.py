from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from enum import Enum
import uuid


class PaymentMethod(str, Enum):
    BANK_TRANSFER = "bank_transfer"
    CHEQUE = "cheque"
    CASH = "cash"
    UNKNOWN = "unknown"


class PayerInfo(BaseModel):
    name: Optional[str] = None
    ice: Optional[str] = None


class PayeeInfo(BaseModel):
    name: Optional[str] = None


class PaymentDetails(BaseModel):
    method: PaymentMethod = PaymentMethod.UNKNOWN
    reference: Optional[str] = None
    bank: Optional[str] = None
    account: Optional[str] = None


class PaymentAmount(BaseModel):
    value: Optional[float] = None
    currency: Optional[str] = None


class PaymentDates(BaseModel):
    operation_date: Optional[date] = None
    value_date: Optional[date] = None


class PaymentStruct(BaseModel):
    payment_id: Optional[str] = None
    payer: PayerInfo
    payee: PayeeInfo
    payment: PaymentDetails
    amount: PaymentAmount
    dates: PaymentDates

