from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.services.preprocessing import preprocess_image
from app.services.google_ocr import extract_with_google_pdf
from app.utils.config import config
import uuid
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title=config.SERVICE_NAME,
    version=config.VERSION,
    description="OCR extraction service for invoices (Google Cloud Vision)"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/ocr/extract")
async def extract_text(
    file: UploadFile = File(...)
):
    start_time = datetime.now()
    document_id = str(uuid.uuid4())

    try:
        contents = await file.read()

        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are supported for Google OCR"
            )

        logger.info("Running Google OCR on full PDF (all pages)")
        ocr_result = extract_with_google_pdf(contents)

        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "document_id": document_id,
            "raw_text": ocr_result["text"],
            "confidence": None,
            "processing_time": round(processing_time, 2),
            "ocr_method": "google",
            "pages": "ALL"
        }

    except Exception as e:
        logger.error(str(e))
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": config.SERVICE_NAME,
        "version": config.VERSION
    }
