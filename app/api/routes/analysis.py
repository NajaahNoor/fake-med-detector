"""
app/api/routes/analysis.py
--------------------------
Main analysis endpoints.
"""

import os
import uuid
from fastapi import APIRouter, File, UploadFile, HTTPException
from app.schemas.analysis import AnalysisRequest, AnalysisResponse
from app.services.pipeline import pipeline
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import FakeMedDetectorException

router = APIRouter()


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_drug(request: AnalysisRequest):
    """
    Analyze a drug for authenticity.
    
    Accepts:
    - registration_number: DRAP registration number
    - product_name: Drug product name
    - company_name: Manufacturer name
    - batch_number: Drug batch number
    - image_path: Path to medicine label image (preprocessed)
    
    Returns:
    - Verdict (VERIFIED, SUSPICIOUS, COUNTERFEIT)
    - Risk score and reasons
    - Drug information and ingredients
    - Recommendations
    """
    try:
        # Prepare input
        user_input = {
            "registration_number": request.registration_number,
            "product_name": request.product_name,
            "company_name": request.company_name,
            "batch_number": request.batch_number,
            "image_path": request.image_path,
            "reporter": request.reporter
        }
        
        logger.info(f"Analysis request: reg={request.registration_number}, image={request.image_path}")
        
        # Run pipeline
        result = pipeline.analyze(user_input)
        
        # Transform to response model
        response = AnalysisResponse(
            status=result.get("status", "success"),
            message=result.get("message", ""),
            verdict=result.get("verdict"),
            registration_number=result.get("registration_number"),
            product_name=result.get("product_name"),
            drug_info=result.get("drug_info"),
            ingredients=result.get("ingredients"),
            risk_score=result.get("score"),
            flags=result.get("flags", []),
            confidence=result.get("ocr_confidence")
        )
        
        return response
        
    except FakeMedDetectorException as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/upload-and-analyze", response_model=AnalysisResponse)
async def upload_and_analyze(file: UploadFile = File(...)):
    """
    Upload a medicine label image and analyze it.
    
    Processes:
    1. Image upload and validation
    2. OCR extraction
    3. Drug verification
    4. Risk assessment
    
    Returns complete analysis result.
    """
    try:
        # Validate file
        allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
            )
        
        # Save uploaded file
        os.makedirs(settings.upload_dir, exist_ok=True)
        file_id = str(uuid.uuid4())
        file_path = os.path.join(settings.upload_dir, f"{file_id}{file_ext}")
        
        contents = await file.read()
        file_size_mb = len(contents) / (1024 * 1024)
        
        if file_size_mb > settings.max_upload_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {settings.max_upload_size_mb}MB"
            )
        
        with open(file_path, "wb") as f:
            f.write(contents)
        
        logger.info(f"Uploaded image: {file_path} ({file_size_mb:.2f}MB)")
        
        # Analyze
        user_input = {
            "image_path": file_path,
            "reporter": file.filename
        }
        
        result = pipeline.analyze(user_input)
        
        # Transform to response model
        response = AnalysisResponse(
            status=result.get("status", "success"),
            message=result.get("message", ""),
            verdict=result.get("verdict"),
            registration_number=result.get("registration_number"),
            product_name=result.get("product_name"),
            drug_info=result.get("drug_info"),
            ingredients=result.get("ingredients"),
            risk_score=result.get("score"),
            flags=result.get("flags", []),
            confidence=result.get("ocr_confidence")
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_drugs(query: str, limit: int = 10):
    """
    Search drugs by name in the database.
    
    Parameters:
    - query: Product or generic name to search
    - limit: Maximum results (default: 10)
    
    Returns:
    List of matching drugs.
    """
    try:
        from app.services.database import db
        results = db.search_by_name(query, limit=limit)
        
        return {
            "status": "success",
            "query": query,
            "count": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
