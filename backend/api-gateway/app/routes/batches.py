from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from typing import List, Optional
from pydantic import BaseModel
import httpx
from ..middleware.auth_middleware import get_current_user
from ..utils.http_client import HTTPClient
from ..config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# HTTP client for orchestrator service
orchestrator_client = HTTPClient(settings.ORCHESTRATOR_SERVICE_URL, timeout=300.0)


class BatchCreateRequest(BaseModel):
    company_name: str
    company_ice: str
    company_rc: Optional[str] = None


@router.post("/")
async def create_batch(
    request: BatchCreateRequest,
    user = Depends(get_current_user)
):
    """Create a new processing batch"""
    try:
        result = await orchestrator_client.post(
            "/batches",
            json_data={
                "user_id": user["user_id"],
                "company_name": request.company_name,
                "company_ice": request.company_ice,
                "company_rc": request.company_rc
            }
        )
        logger.info(f"Batch created: {result.get('batch_id')}")
        return result
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to create batch: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/")
async def list_batches(
    limit: int = 50,
    user = Depends(get_current_user)
):
    """List all batches for current user"""
    try:
        result = await orchestrator_client.get(
            f"/users/{user['user_id']}/batches?limit={limit}"
        )
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/{batch_id}")
async def get_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Get batch details"""
    try:
        result = await orchestrator_client.get(f"/batches/{batch_id}")
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/{batch_id}/upload/invoices")
async def upload_invoices(
    batch_id: str,
    files: List[UploadFile] = File(...),
    user = Depends(get_current_user)
):
    """Upload invoice files"""
    try:
        # Prepare files for upload
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append(
                ("files", (file.filename, content, file.content_type))
            )
        
        # Forward to orchestrator
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/batches/{batch_id}/upload/invoices",
                files=files_data
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/{batch_id}/upload/payments")
async def upload_payments(
    batch_id: str,
    files: List[UploadFile] = File(...),
    user = Depends(get_current_user)
):
    """Upload payment files"""
    try:
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append(
                ("files", (file.filename, content, file.content_type))
            )
        
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/batches/{batch_id}/upload/payments",
                files=files_data
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/{batch_id}/process")
async def process_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Start processing the batch"""
    try:
        result = await orchestrator_client.post(
            f"/batches/{batch_id}/process",
            json_data={}
        )
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/{batch_id}/results")
async def get_batch_results(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Get processing results for validation"""
    try:
        result = await orchestrator_client.get(f"/batches/{batch_id}/results")
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.post("/{batch_id}/validate")
async def validate_batch(
    batch_id: str,
    validation_data: dict,
    user = Depends(get_current_user)
):
    """Submit user validation"""
    try:
        validation_data["user_id"] = user["user_id"]
        validation_data["batch_id"] = batch_id
        
        result = await orchestrator_client.post(
            f"/batches/{batch_id}/validate",
            json_data=validation_data
        )
        return result
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.get("/{batch_id}/export/csv")
async def export_csv(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Export DGI declaration as CSV"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{settings.ORCHESTRATOR_SERVICE_URL}/batches/{batch_id}/export/csv"
            )
            response.raise_for_status()
            
            return Response(
                content=response.content,
                media_type="text/csv",
                headers=response.headers
            )
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: str,
    user = Depends(get_current_user)
):
    """Delete a batch"""
    # TODO: Implement in orchestrator service
    raise HTTPException(status_code=501, detail="Not implemented yet")