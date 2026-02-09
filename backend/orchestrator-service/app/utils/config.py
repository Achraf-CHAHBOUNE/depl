from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SERVICE_NAME = "orchestrator-service"
    VERSION = "1.0.0"
    
    # External services
    OCR_SERVICE_URL = os.getenv("OCR_SERVICE_URL", "http://localhost:8001")
    INTELLIGENCE_SERVICE_URL = os.getenv("INTELLIGENCE_SERVICE_URL", "http://localhost:8004")
    
    # Storage
    STORAGE_PATH = os.getenv("STORAGE_PATH", "./storage/uploads")
    
    # Database
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://dgi_user:dgi_password@localhost:5432/dgi_compliance"
    )

config = Config()