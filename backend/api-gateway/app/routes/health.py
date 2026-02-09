from fastapi import APIRouter
import httpx
from ..config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "api-gateway",
        "version": settings.VERSION
    }


@router.get("/health/services")
async def check_backend_services():
    """Check health of all backend services"""
    services = {
        "orchestrator": f"{settings.ORCHESTRATOR_SERVICE_URL}/health",
    }
    
    results = {}
    
    for service_name, url in services.items():
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                results[service_name] = {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "status_code": response.status_code
                }
        except Exception as e:
            results[service_name] = {
                "status": "unreachable",
                "error": str(e)
            }
    
    all_healthy = all(r["status"] == "healthy" for r in results.values())
    
    return {
        "api_gateway": "healthy",
        "backend_services": results,
        "overall_status": "healthy" if all_healthy else "degraded"
    }