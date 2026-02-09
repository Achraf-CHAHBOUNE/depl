import uuid
from anthropic import Anthropic
from typing import Any, Dict, List
import uuid
import re
from tenacity import retry, stop_after_attempt, wait_exponential
from ..utils.helper import compute_missing_fields
import json
import logging
from ..schemas.invoice import InvoiceStruct
from ..schemas.payment import PaymentStruct

logger = logging.getLogger(__name__)

from typing import Any, Dict, List


class StructuredExtractor:
    """
    Module A: LLM-based extraction of invoices and payments from OCR text.
    
    CRITICAL RULES:
    - Extract ONLY information explicitly present in the text
    - NEVER infer, calculate, or deduce missing values
    - For missing fields, return null
    - Preserve original wording and values exactly as written
    """
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
    )
    def extract_invoice(self, ocr_text: str) -> InvoiceStruct:
        """
        Extract invoice data from OCR text.
        Returns strictly factual JSON matching invoice_struct schema.
        """
        
        system_prompt = """You are a financial document extraction system for Moroccan invoices.

CRITICAL RULES:
- Extract ONLY information explicitly present in the text
- NEVER infer, calculate, or deduce missing values
- For missing fields, return null
- Preserve original wording and values exactly as written
- Dates must be in YYYY-MM-DD format
- Amounts must be numeric (float)
- Currency is "MAD" only if explicitly mentioned, otherwise null

MOROCCAN INVOICE TERMINOLOGY:
- ICE = Identifiant Commun de l'Entreprise (company ID)
- RC = Registre de Commerce (commercial registry)
- HT = Hors Taxe (excluding tax)
- TVA = Taxe sur la Valeur Ajoutée (VAT)
- TTC = Toutes Taxes Comprises (including all taxes)
- BL = Bon de Livraison (delivery note)

You must return valid JSON matching this exact schema:
{
  "supplier": {
    "name": string | null,
    "ice": string | null,
    "rc": string | null,
    "address": string | null
  },
  "customer": {
    "name": string | null,
    "ice": string | null
  },
  "invoice": {
    "number": string | null,
    "issue_date": "YYYY-MM-DD" | null,
    "delivery_date": "YYYY-MM-DD" | null,
    "due_date": "YYYY-MM-DD" | null,
    "contract_reference": string | null,
    "bl_reference": string | null
  },
  "amounts": {
    "total_ht": number | null,
    "total_tva": number | null,
    "total_ttc": number | null,
    "currency": "MAD" | null
  },
  "line_items": [
    {
      "description": string,
      "quantity": number | null,
      "unit_price_ht": number | null,
      "total_ht": number | null,
      "tva_rate": number | null
    }
  ],
  "missing_fields": [string]
}

Return ONLY the JSON object, no explanations."""

        user_prompt = f"""Extract invoice information from this OCR text:

{ocr_text}

Return the structured JSON."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.content[0].text

            # Robust JSON extraction
            content = content.strip()
            # Remove markdown code fences if present
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            # Extract JSON object
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                logger.error(f"No valid JSON found in response: {content[:200]}")
                raise ValueError("LLM did not return valid JSON")

            invoice_data = json.loads(json_match.group())
            
            # Generate UUID for invoice
            invoice_data['invoice_id'] = str(uuid.uuid4())
            
            # Validate and return as Pydantic model
            
            invoice_data["missing_fields"] = compute_missing_fields(invoice_data)
            result = InvoiceStruct(**invoice_data)


            # Audit logging
            logger.info(
                f"Invoice extracted: ID={result.invoice_id}, "
                f"Supplier={result.supplier.name}, "
                f"Number={result.invoice.number}, "
                f"Amount={result.amounts.total_ttc} {result.amounts.currency}, "
                f"Missing fields={len(result.missing_fields)}"
            )

            return result
            
        except json.JSONDecodeError as e:
          logger.error(f"Invoice extraction - Invalid JSON: {str(e)}")
          logger.error(f"LLM Response: {content[:500]}")
          raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        
        except Exception as e:
          logger.error(f"Invoice extraction failed: {str(e)}", exc_info=True)
          raise RuntimeError(f"Invoice extraction error: {str(e)}")    
        
        
    @retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True
    )    
    def extract_payment(self, ocr_text: str) -> PaymentStruct:
        """
        Extract payment data from OCR text (bank statement, payment proof).
        Returns strictly factual JSON matching payment_struct schema.
        
        IMPROVED: Better handling of Moroccan bank statements with multiple transactions.
        """
        
        system_prompt = """You are a financial document extraction system for Moroccan payment documents.

CRITICAL RULES:
- Extract ONLY information explicitly present in the text
- NEVER infer, calculate, or deduce missing values
- For missing fields, return null
- Preserve original wording and values exactly as written
- Dates must be in YYYY-MM-DD format
- Amounts must be numeric (float)

MOROCCAN BANK STATEMENT SPECIFICS:
- Look for "VIR.EMIS WEB VERS" (outgoing transfer) or "VIREMENT" entries
- The payee name appears AFTER "VERS" keyword
- Amount appears in the DEBIT column (money going out)
- Date format: DD MM YYYY or DD/MM/YYYY or DD/MM/YY
- Look for specific supplier names like "ARIHA SERVICE"
- Multiple transactions may be present - find the one matching expected context

PAYMENT METHODS:
- bank_transfer: virement bancaire, VIR.WEB, VIR.EMIS, VIREMENT
- cheque: chèque
- cash: espèces
- unknown: if not specified

EXTRACTION STRATEGY FOR BANK STATEMENTS:
1. First identify if this is a bank statement (look for "RELEVE DE COMPTE")
2. Scan all transaction lines for outgoing payments (VIR.EMIS, VIREMENT EMIS)
3. For each payment line, extract:
   - Date (look for pattern like "27 08 2025" or "27/08/2025")
   - Payee name (after VERS or recipient indicator)
   - Amount (in DEBIT column, look for numbers with comma like "6 300,00")
4. If multiple payments exist to different suppliers, extract the LARGEST or MOST RECENT one
5. The payer is usually the account holder shown at top of statement

EXAMPLE TRANSACTION LINE PATTERNS:
"0016BK 28 08 VIR.EMIS WEB VERS ARIHA SERVICE SAR 27 08 2025 ... 6 300,00"
Should extract:
- operation_date: "2025-08-28" (first date, when bank processed)
- value_date: "2025-08-27" (second date, value date)
- payee.name: "ARIHA SERVICE SAR" (or "ARIHA SERVICE SARL")
- amount.value: 6300.00 (convert "6 300,00" to 6300.00)
- payment.method: "bank_transfer"

AMOUNT PARSING RULES:
- "6 300,00" → 6300.00
- "6300,00" → 6300.00  
- "6.300,00" → 6300.00
- "6,300.00" → 6300.00
- Remove spaces and convert comma to dot for decimal

DATE PARSING RULES:
- "28 08 2025" → "2025-08-28"
- "27/08/2025" → "2025-08-27"
- "27/08/25" → "2025-08-27" (assume 20XX for YY format)
- Operation date is usually first, value date is second

You must return valid JSON matching this exact schema:
{
  "payer": {
    "name": string | null,
    "ice": string | null
  },
  "payee": {
    "name": string | null
  },
  "payment": {
    "method": "bank_transfer" | "cheque" | "cash" | "unknown",
    "reference": string | null,
    "bank": string | null,
    "account": string | null
  },
  "amount": {
    "value": number | null,
    "currency": "MAD" | null
  },
  "dates": {
    "operation_date": "YYYY-MM-DD" | null,
    "value_date": "YYYY-MM-DD" | null
  }
}

IMPORTANT FOCUS:
- For bank statements, prioritize OUTGOING transfers to SUPPLIERS
- Look for company names in "VIR.EMIS WEB VERS [Company Name]" patterns
- Extract the amount from the DEBIT column
- Convert French number format (space thousands, comma decimal) to standard float

Return ONLY the JSON object, no explanations."""

        user_prompt = f"""Extract payment information from this OCR text.

This appears to be a bank statement. Focus on finding OUTGOING payments (VIR.EMIS, VIREMENT) to suppliers.
Look for patterns like "VIR.EMIS WEB VERS [Company]" and extract the payee, amount, and dates.

OCR Text:
{ocr_text}

Return the structured JSON for the most relevant payment transaction."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            content = response.content[0].text

            # Robust JSON extraction
            content = content.strip()
            if content.startswith('```'):
                content = re.sub(r'^```(?:json)?\s*', '', content)
                content = re.sub(r'\s*```$', '', content)

            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if not json_match:
                logger.error(f"No valid JSON found in response: {content[:200]}")
                raise ValueError("LLM did not return valid JSON")

            payment_data = json.loads(json_match.group())
            
            # Generate UUID for payment
            payment_data['payment_id'] = str(uuid.uuid4())
            
            # Validate and return as Pydantic model
            result = PaymentStruct(**payment_data)

            # Audit logging
            logger.info(
                f"Payment extracted: ID={result.payment_id}, "
                f"Payee={result.payee.name}, "
                f"Amount={result.amount.value} {result.amount.currency}, "
                f"Date={result.dates.operation_date}"
            )

            return result
            
        except Exception as e:
            logger.error(f"Payment extraction failed: {str(e)}")
            raise RuntimeError(f"Payment extraction error: {str(e)}")
          