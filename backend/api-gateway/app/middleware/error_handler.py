from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging
import httpx

logger = logging.getLogger(__name__)


def add_error_handlers(app: FastAPI):
    """Add global error handlers to the app"""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors"""
        return JSONResponse(
            status_code=422,
            content={
                "error": "Validation error",
                "details": exc.errors()
            }
        )
    
    @app.exception_handler(httpx.HTTPStatusError)
    async def httpx_exception_handler(request: Request, exc: httpx.HTTPStatusError):
        """Handle errors from backend services"""
        logger.error(f"Backend service error: {exc}")
        return JSONResponse(
            status_code=exc.response.status_code,
            content={
                "error": "Backend service error",
                "detail": str(exc),
                "status_code": exc.response.status_code
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle any other exceptions"""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc)
            }
        )