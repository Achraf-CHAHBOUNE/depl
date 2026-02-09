from typing import Optional
from datetime import date
import re


def validate_ice(ice: Optional[str]) -> bool:
    """
    Validate Moroccan ICE (Identifiant Commun de l'Entreprise).
    ICE is 15 digits.
    """
    if not ice:
        return False
    
    # Remove spaces
    ice = ice.replace(" ", "")
    
    # Check if 15 digits
    return bool(re.match(r'^\d{15}$', ice))


def validate_rc(rc: Optional[str]) -> bool:
    """
    Validate Moroccan RC (Registre de Commerce).
    """
    if not rc:
        return False
    
    # Basic validation - RC format varies
    return len(rc.strip()) > 0


def validate_amount(amount: Optional[float]) -> bool:
    """
    Validate amount is positive.
    """
    if amount is None:
        return False
    
    return amount >= 0


def validate_date_order(
    invoice_date: Optional[date],
    payment_date: Optional[date]
) -> bool:
    """
    Validate that payment date is after invoice date.
    """
    if not invoice_date or not payment_date:
        return True  # Cannot validate if dates missing
    
    return payment_date >= invoice_date
