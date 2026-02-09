from urllib import request
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import List, Optional, Set
from datetime import date
import logging
from .modules.extraction import StructuredExtractor
from .modules.matching import IntelligentMatcher
from .services.dgi_formatter import DGIFormatter
from .services.rules_service import RulesComputationService
from .services.export_service import ExportService
from .schemas.invoice import InvoiceStruct
from .schemas.payment import PaymentStruct
from .schemas.matching import MatchingResult
from .schemas.legal_result import LegalResult
from .schemas.dgi_output import DGIDeclaration
from .utils.config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Intelligence Service - DGI Compliance",
    version="1.0.0",
    description="Complete LLM-based extraction, matching, and legal computation for DGI declarations"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize modules
extractor = StructuredExtractor(api_key=config.ANTHROPIC_API_KEY)
matcher = IntelligentMatcher(amount_tolerance=config.AMOUNT_TOLERANCE)
rules_service = RulesComputationService(
    penalty_base_rate=config.PENALTY_BASE_RATE,
    penalty_monthly_increment=config.PENALTY_MONTHLY_INCREMENT
)
formatter = DGIFormatter()
export_service = ExportService()


# Request/Response models
class ExtractionRequest(BaseModel):
    ocr_text: str
    document_type: str  # "invoice" or "payment"


class MatchingRequest(BaseModel):
    invoices: List[InvoiceStruct]
    payments: List[PaymentStruct]


class RulesComputationRequest(BaseModel):
    """Request for legal rules computation"""
    invoice: InvoiceStruct
    matching_result: MatchingResult
    contractual_delay_days: Optional[int] = None
    is_disputed: bool = False
    is_credit_note: bool = False
    is_procedure_690: bool = False


class BatchRulesComputationRequest(BaseModel):
    """Batch computation for multiple invoices"""
    invoices: List[InvoiceStruct]
    matching_results: List[MatchingResult]
    contractual_delays: Optional[List[Optional[int]]] = None
    disputed_invoices: Optional[List[str]] = None  # Invoice IDs
    credit_notes: Optional[List[str]] = None  # Invoice IDs
    procedure_690_suppliers: Optional[List[str]] = None  # Supplier ICEs


class CompleteDGIRequest(BaseModel):
    """Complete DGI declaration generation"""
    invoices: List[InvoiceStruct]
    matching_results: List[MatchingResult]
    legal_results: List[LegalResult]
    company_ice: str
    company_name: str
    company_rc: str
    declaration_year: int
    declaration_month: Optional[int] = None
    activity_sector: Optional[str] = None


class HolidayConfigRequest(BaseModel):
    """Configure Islamic holidays for a year"""
    islamic_holidays: List[date]


# Endpoints
@app.post("/extract/invoice", response_model=InvoiceStruct)
async def extract_invoice(request: ExtractionRequest):
    """Extract invoice data from OCR text"""
    
    if request.document_type != "invoice":
        raise HTTPException(status_code=400, detail="document_type must be 'invoice'")

    if not request.ocr_text or len(request.ocr_text.strip()) == 0:
        raise HTTPException(status_code=400, detail="OCR text cannot be empty")
    
    if len(request.ocr_text) > 100000:
        raise HTTPException(status_code=400, detail="OCR text too large (max 100KB)")
    
    try:
        result = extractor.extract_invoice(request.ocr_text)
        return result
    except Exception as e:
        logger.error(f"Invoice extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/extract/payment", response_model=PaymentStruct)
async def extract_payment(request: ExtractionRequest):
    """Extract payment data from OCR text"""
    
    if request.document_type != "payment":
        raise HTTPException(status_code=400, detail="document_type must be 'payment'")

    try:
        result = extractor.extract_payment(request.ocr_text)
        return result
    except Exception as e:
        logger.error(f"Payment extraction failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/match", response_model=List[MatchingResult])
async def match_invoices_payments(request: MatchingRequest):
    """Match invoices to payments with confidence scoring"""
    if not request.invoices:
        raise HTTPException(status_code=400, detail="At least one invoice is required")
    
    if len(request.invoices) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 invoices per request")
    
    if len(request.payments) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 payments per request")
    
    try:
        results = matcher.match_invoices_to_payments(
            request.invoices,
            request.payments
        )
        return results
    except Exception as e:
        logger.error(f"Matching failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules/compute", response_model=LegalResult)
async def compute_legal_rules(request: RulesComputationRequest):
    """
    Compute complete legal result for a single invoice.
    
    This applies all DGI rules:
    - Payment terms (Article 78-2)
    - Penalties (Article 78-3)
    - Legal status handling
    """
    try:
        result = rules_service.compute_legal_result(
            invoice=request.invoice,
            matching_result=request.matching_result,
            contractual_delay_days=request.contractual_delay_days,
            is_disputed=request.is_disputed,
            is_credit_note=request.is_credit_note,
            is_procedure_690=request.is_procedure_690
        )
        return result
    except Exception as e:
        logger.error(f"Legal computation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules/compute/batch", response_model=List[LegalResult])
async def compute_legal_rules_batch(request: BatchRulesComputationRequest):
    """
    Batch computation of legal rules for multiple invoices.
    More efficient than calling /rules/compute repeatedly.
    """
    if len(request.invoices) != len(request.matching_results):
        raise HTTPException(
            status_code=400,
            detail="Invoices and matching_results must have same length"
        )
    
    if len(request.invoices) > 1000:
        raise HTTPException(status_code=400, detail="Maximum 1000 invoices per batch")
    
    # Prepare helper sets
    disputed_set = set(request.disputed_invoices or [])
    credit_note_set = set(request.credit_notes or [])
    procedure_690_set = set(request.procedure_690_suppliers or [])
    
    # Prepare contractual delays
    contractual_delays = request.contractual_delays or [None] * len(request.invoices)
    
    if len(contractual_delays) != len(request.invoices):
        raise HTTPException(
            status_code=400,
            detail="contractual_delays must have same length as invoices"
        )
    
    try:
        results = []
        
        for i, (invoice, matching, contractual_delay) in enumerate(
            zip(request.invoices, request.matching_results, contractual_delays)
        ):
            is_disputed = invoice.invoice_id in disputed_set
            is_credit_note = invoice.invoice_id in credit_note_set
            is_procedure_690 = (invoice.supplier.ice or "") in procedure_690_set
            
            result = rules_service.compute_legal_result(
                invoice=invoice,
                matching_result=matching,
                contractual_delay_days=contractual_delay,
                is_disputed=is_disputed,
                is_credit_note=is_credit_note,
                is_procedure_690=is_procedure_690
            )
            results.append(result)
        
        logger.info(f"Batch computation completed: {len(results)} invoices")
        return results
        
    except Exception as e:
        logger.error(f"Batch legal computation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dgi/format", response_model=DGIDeclaration)
async def format_dgi_declaration(request: CompleteDGIRequest):
    """
    Format complete DGI declaration with all legal computations.
    """
    if not (len(request.invoices) == len(request.matching_results) == len(request.legal_results)):
        raise HTTPException(
            status_code=400,
            detail="Invoices, matching_results, and legal_results must have same length"
        )
    
    try:
        declaration = formatter.format_declaration(
            invoices=request.invoices,
            matching_results=request.matching_results,
            legal_results=request.legal_results,
            company_ice=request.company_ice,
            company_name=request.company_name,
            company_rc=request.company_rc,
            declaration_year=request.declaration_year,
            declaration_month=request.declaration_month,
            activity_sector=request.activity_sector
        )
        return declaration
    except Exception as e:
        logger.error(f"DGI formatting failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dgi/export/csv")
async def export_dgi_csv(declaration: DGIDeclaration):
    """
    Export DGI declaration to CSV format.
    """
    try:
        csv_content = export_service.export_to_csv(declaration)
        
        filename = f"DGI_Declaration_{declaration.company_ice}_{declaration.declaration_year}"
        if declaration.declaration_month:
            filename += f"_{declaration.declaration_month:02d}"
        filename += ".csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"CSV export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/dgi/export/alerts-report")
async def export_alerts_report(declaration: DGIDeclaration):
    """
    Export alerts summary report.
    """
    try:
        report = export_service.export_alerts_summary(declaration)
        
        filename = f"DGI_Alerts_{declaration.company_ice}_{declaration.declaration_year}.txt"
        
        return Response(
            content=report.encode('utf-8'),
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        logger.error(f"Alerts report export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "intelligence-service",
        "version": "2.0.0",
        "features": [
            "invoice_extraction",
            "payment_extraction",
            "intelligent_matching",
            "legal_rules_computation",
            "dgi_formatting",
            "csv_export",
            "alerts_reporting"
        ]
    }


@app.get("/config")
async def get_config():
    """Return current configuration (without sensitive data)"""
    return {
        "model": config.ANTHROPIC_MODEL,
        "amount_tolerance": config.AMOUNT_TOLERANCE,
        "min_confidence_score": config.MIN_CONFIDENCE_SCORE,
        "penalty_base_rate": config.PENALTY_BASE_RATE,
        "penalty_monthly_increment": config.PENALTY_MONTHLY_INCREMENT,
        "legal_constants": {
            "default_legal_delay_days": 60,
            "max_contractual_delay_days": 120
        }
    }