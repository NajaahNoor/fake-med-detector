"""
app/api/routes/health.py
------------------------
Health check and status endpoints.
"""

from fastapi import APIRouter, Depends
from app.core.config import settings
from app.services.database import db
from app.schemas.analysis import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    
    Returns application status and database health.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        debug=settings.debug,
        database_connected=db.is_healthy()
    )


@router.get("/status")
async def get_status():
    """Get detailed system status."""
    db_stats = db.get_stats()
    return {
        "app_name": settings.app_name,
        "version": settings.app_version,
        "debug": settings.debug,
        "database": {
            "path": db_stats["path"],
            "connected": db.is_healthy(),
            "source_json": "drug-ndc-0001-of-0001.json",
            "drug_count": db_stats["drug_count"],
            "package_count": db_stats["package_count"]
        },
        "llm": {
            "primary_model": settings.primary_model,
            "fallback_models": settings.fallback_models_list
        },
        "ocr": {
            "version": settings.ocr_version,
            "language": settings.ocr_lang,
            "angle_cls": settings.ocr_use_angle_cls,
            "onednn_disabled": settings.flags_use_onednn == 0
        }
    }
