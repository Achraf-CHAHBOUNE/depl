from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date
import uuid


class SupplierInfo(BaseModel):
    name: Optional[str] = None
    ice: Optional[str] = None  # Identifiant Commun de l'Entreprise
    rc: Optional[str] = None   # Registre de Commerce
    address: Optional[str] = None


class CustomerInfo(BaseModel):
    name: Optional[str] = None
    ice: Optional[str] = None


class InvoiceDetails(BaseModel):
    number: Optional[str] = None
    issue_date: Optional[date] = None
    delivery_date: Optional[date] = None
    due_date: Optional[date] = None
    contract_reference: Optional[str] = None
    bl_reference: Optional[str] = None  # Bon de Livraison


class AmountsInfo(BaseModel):
    total_ht: Optional[float] = None   # Hors Taxe
    total_tva: Optional[float] = None  # TVA
    total_ttc: Optional[float] = None  # Toutes Taxes Comprises
    currency: Optional[str] = None


class LineItem(BaseModel):
    description: str
    quantity: Optional[float] = None
    unit_price_ht: Optional[float] = None
    total_ht: Optional[float] = None
    tva_rate: Optional[float] = None


class InvoiceStruct(BaseModel):
    invoice_id: Optional[str] = None
    supplier: SupplierInfo
    customer: CustomerInfo
    invoice: InvoiceDetails
    amounts: AmountsInfo
    line_items: List[LineItem] = []
    missing_fields: List[str] = []
