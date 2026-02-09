from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # Service Info
    SERVICE_NAME: str = "api-gateway"
    VERSION: str = "1.0.0"
    
    # JWT Settings
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "change-this-secret-key-in-production")
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]
    
    # Backend Services URLs
    ORCHESTRATOR_SERVICE_URL: str = os.getenv(
        "ORCHESTRATOR_SERVICE_URL",
        "http://orchestrator-service:8005"
    )
    AUTH_SERVICE_URL: str = os.getenv(
        "AUTH_SERVICE_URL",
        "http://auth-service:8006"
    )
    
    # Database (if gateway needs direct DB access)
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://dgi_user:dgi_password@postgres:5432/dgi_compliance"
    )
    
    class Config:
        case_sensitive = True


settings = Settings()