from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import Response
from typing import List, Optional
import httpx
import logging
from jose import JWTError, jwt
from datetime import datetime, timedelta
import os

# NEW: Database imports
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP (NEW)
# ============================================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://dgi_user:dgi_password@postgres:5432/dgi_compliance"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# User Model (NEW)
class UserDB(Base):
    __tablename__ = "users"
    
    user_id = Column(String(50), primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    company_name = Column(String(255))
    company_ice = Column(String(20))
    company_rc = Column(String(50))
    last_login = Column(DateTime)

# Database dependency (NEW)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# CONFIGURATION
# ============================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://orchestrator-service:8005")

# ============================================================================
# APP SETUP
# ============================================================================

app = FastAPI(
    title="DGI API Gateway",
    version="1.0.0",
    description="Central API Gateway for DGI Compliance System"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ============================================================================
# AUTH UTILITIES
# ============================================================================

def create_access_token(data: dict):
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("email")
    }

# ============================================================================
# AUTH ENDPOINTS
# ============================================================================

from pydantic import BaseModel, EmailStr

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None

@app.post("/api/auth/login")
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    REAL DATABASE AUTHENTICATION
    Queries PostgreSQL and verifies bcrypt password
    """
    try:
        # Find user in database
        user = db.query(UserDB).filter(UserDB.email == request.email).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        # Verify password with bcrypt
        if not pwd_context.verify(request.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou mot de passe incorrect"
            )
        
        # Update last login timestamp
        user.last_login = datetime.now()
        db.commit()
        
        # Create JWT token
        token = create_access_token({
            "user_id": user.user_id,
            "email": user.email,
            "company_name": user.company_name,
            "company_ice": user.company_ice
        })
        
        logger.info(f"✅ User logged in from database: {user.email}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": user.user_id,
                "email": user.email,
                "name": user.name,
                "role": user.role,
                "company_name": user.company_name,
                "company_ice": user.company_ice,
                "company_rc": user.company_rc
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la connexion"
        )

@app.post("/api/auth/register")
async def register(request: RegisterRequest, db: Session = Depends(get_db)):
    """
    Register new user with database persistence
    """
    try:
        # Check if user exists
        existing_user = db.query(UserDB).filter(UserDB.email == request.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email déjà utilisé"
            )
        
        # Hash password
        password_hash = pwd_context.hash(request.password)
        
        # Create user
        import uuid
        new_user = UserDB(
            user_id=f"user-{str(uuid.uuid4())[:8]}",
            email=request.email,
            password_hash=password_hash,
            name=request.email.split('@')[0].title(),
            role="user",
            company_name=request.company_name,
            company_ice=request.company_ice,
            company_rc=request.company_rc
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Create token
        token = create_access_token({
            "user_id": new_user.user_id,
            "email": new_user.email,
            "company_name": new_user.company_name,
            "company_ice": new_user.company_ice
        })
        
        logger.info(f"✅ New user registered: {new_user.email}")
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "user_id": new_user.user_id,
                "email": new_user.email,
                "name": new_user.name,
                "role": new_user.role,
                "company_name": new_user.company_name,
                "company_ice": new_user.company_ice
            },
            "message": "Compte créé avec succès"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'inscription"
        )

@app.get("/api/auth/me")
async def get_current_user_info(user = Depends(get_current_user)):
    """Get current user information"""
    return user

# ============================================================================
# BATCH ENDPOINTS (Proxy to Orchestrator)
# ============================================================================

class CreateBatchRequest(BaseModel):
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None

@app.post("/api/batches")
async def create_batch(
    request: CreateBatchRequest,
    user = Depends(get_current_user)
):
    """Create a new processing batch"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches",
                json={
                    "user_id": user["user_id"],
                    "company_name": request.company_name,
                    "company_ice": request.company_ice,
                    "company_rc": request.company_rc
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error creating batch: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la création du batch")

@app.get("/api/batches")
async def list_batches(user = Depends(get_current_user)):
    """List all batches for current user"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{ORCHESTRATOR_URL}/users/{user['user_id']}/batches"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error listing batches: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération des batches")

@app.get("/api/batches/{batch_id}")
async def get_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Get batch details"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting batch: {e}")
            raise HTTPException(status_code=404, detail="Batch non trouvé")

@app.post("/api/batches/{batch_id}/upload/invoices")
async def upload_invoices(
    batch_id: str,
    files: List[UploadFile] = File(...),
    user = Depends(get_current_user)
):
    """Upload invoice files"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            files_data = []
            for file in files:
                content = await file.read()
                files_data.append(
                    ("files", (file.filename, content, file.content_type or "application/pdf"))
                )
            
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/upload/invoices",
                files=files_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error uploading invoices: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'upload des factures")

@app.post("/api/batches/{batch_id}/upload/payments")
async def upload_payments(
    batch_id: str,
    files: List[UploadFile] = File(...),
    user = Depends(get_current_user)
):
    """Upload payment files"""
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            files_data = []
            for file in files:
                content = await file.read()
                files_data.append(
                    ("files", (file.filename, content, file.content_type or "application/pdf"))
                )
            
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/upload/payments",
                files=files_data
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error uploading payments: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'upload des paiements")

@app.post("/api/batches/{batch_id}/process")
async def process_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Start batch processing"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/process"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error processing batch: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors du traitement")

@app.post("/api/batches/{batch_id}/process/invoices")
async def process_invoices_only(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Phase 1: Process invoices only"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/process/invoices"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error processing invoices: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors du traitement des factures")

@app.post("/api/batches/{batch_id}/process/complete")
async def complete_with_payments(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Phase 2: Complete processing with payments"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/process/complete"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error completing with payments: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la finalisation avec paiements")

@app.get("/api/batches/{batch_id}/results")
async def get_batch_results(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Get batch processing results"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/results"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting results: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération des résultats")

class BatchUpdateRequest(BaseModel):
    invoice_updates: Optional[List[dict]] = None
    payment_updates: Optional[List[dict]] = None

class ValidationRequest(BaseModel):
    invoice_updates: List[dict]
    delivery_dates_confirmed: bool = False
    amounts_confirmed: bool = False

@app.patch("/api/batches/{batch_id}")
async def update_batch(
    batch_id: str,
    update: BatchUpdateRequest,
    user = Depends(get_current_user)
):
    """Update batch data (invoices/payments) before validation"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"📤 Forwarding PATCH to orchestrator for batch {batch_id}")
            response = await client.patch(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}",
                json={
                    "invoice_updates": update.invoice_updates or [],
                    "payment_updates": update.payment_updates or [],
                    "user_id": user["user_id"]
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            # Pass through the error from orchestrator
            logger.error(f"❌ Orchestrator returned error: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            try:
                error_detail = e.response.json().get("detail", "Erreur lors de la mise à jour")
            except:
                error_detail = "Erreur lors de la mise à jour"
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            logger.error(f"❌ Request error updating batch: {str(e)}")
            raise HTTPException(status_code=503, detail="Service orchestrateur indisponible")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Erreur lors de la mise à jour")

@app.delete("/api/batches/{batch_id}")
async def delete_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Delete a draft batch"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"📤 Forwarding DELETE to orchestrator for batch {batch_id}")
            response = await client.delete(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Orchestrator returned error: {e.response.status_code}")
            logger.error(f"Response body: {e.response.text}")
            try:
                error_detail = e.response.json().get("detail", "Erreur lors de la suppression")
            except:
                error_detail = "Erreur lors de la suppression"
            raise HTTPException(status_code=e.response.status_code, detail=error_detail)
        except httpx.RequestError as e:
            logger.error(f"❌ Request error deleting batch: {str(e)}")
            raise HTTPException(status_code=503, detail="Service orchestrateur indisponible")
        except Exception as e:
            logger.error(f"❌ Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Erreur lors de la suppression")

@app.post("/api/batches/{batch_id}/recalculate")
async def recalculate_legal_results(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Recalculate legal results after payment updates"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"🔄 Proxying recalculation request for batch {batch_id}")
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/recalculate"
            )
            response.raise_for_status()
            logger.info(f"✅ Recalculation successful for batch {batch_id}")
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"❌ Error recalculating batch: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors du recalcul")

@app.post("/api/batches/{batch_id}/validate")
async def validate_batch(
    batch_id: str,
    validation: ValidationRequest,
    user = Depends(get_current_user)
):
    """Submit validation"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/validate",
                json={
                    "batch_id": batch_id,
                    "user_id": user["user_id"],
                    "invoice_updates": validation.invoice_updates,
                    "delivery_dates_confirmed": validation.delivery_dates_confirmed,
                    "amounts_confirmed": validation.amounts_confirmed
                }
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error validating batch: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la validation")

@app.get("/api/batches/{batch_id}/documents/{document_id}/pdf")
async def get_document_pdf(
    batch_id: str,
    document_id: str
):
    """
    Proxy PDF document requests to orchestrator service.
    No authentication required since PDFs are opened in new tabs.
    Access control is handled by document_id being a UUID that's hard to guess.
    """
    from fastapi.responses import StreamingResponse
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            logger.info(f"📄 Proxying PDF request: batch={batch_id}, document={document_id}")
            response = await client.get(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/documents/{document_id}/pdf",
                follow_redirects=True
            )
            response.raise_for_status()
            
            # Stream the PDF response back to the client
            return StreamingResponse(
                iter([response.content]),
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f'inline; filename="{document_id}.pdf"'
                }
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ Error fetching PDF: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=e.response.text)
        except httpx.RequestError as e:
            logger.error(f"❌ Request error fetching PDF: {str(e)}")
            raise HTTPException(status_code=503, detail="Service orchestrateur indisponible")
        except Exception as e:
            logger.error(f"❌ Unexpected error fetching PDF: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/batches/{batch_id}/export/csv")
async def export_csv(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Export DGI declaration as CSV"""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.get(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/export/csv"
            )
            response.raise_for_status()
            
            return Response(
                content=response.content,
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=DGI_Declaration_{batch_id}.csv"
                }
            )
        except httpx.HTTPError as e:
            logger.error(f"Error exporting CSV: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de l'export CSV")

@app.get("/api/batches/{batch_id}/audit-log")
async def get_audit_log(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Get audit trail"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{ORCHESTRATOR_URL}/batches/{batch_id}/audit-log"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Error getting audit log: {e}")
            raise HTTPException(status_code=500, detail="Erreur lors de la récupération de l'audit")

# ============================================================================
# HEALTH & INFO
# ============================================================================

@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DGI API Gateway",
        "version": "1.0.0",
        "docs": "/docs"
    }