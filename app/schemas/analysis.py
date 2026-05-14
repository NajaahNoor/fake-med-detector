"""
app/schemas/analysis.py
------------------------
Request and response schemas for the analysis pipeline.
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class VerdictEnum(str, Enum):
    """Possible verdicts for drug verification."""
    VERIFIED = "VERIFIED"
    SUSPICIOUS = "SUSPICIOUS"
    COUNTERFEIT = "COUNTERFEIT"


class AnalysisRequest(BaseModel):
    """Request schema for drug analysis."""
    registration_number: Optional[str] = Field(None, description="DRAP registration number")
    product_name: Optional[str] = Field(None, description="Drug product name")
    company_name: Optional[str] = Field(None, description="Manufacturer company name")
    batch_number: Optional[str] = Field(None, description="Drug batch/lot number")
    image_path: Optional[str] = Field(None, description="Path to medicine label image")
    reporter: Optional[str] = Field(None, description="Name of the person reporting")
    
    class Config:
        schema_extra = {
            "example": {
                "registration_number": "134108",
                "product_name": "Axaleo 400mg",
                "company_name": "AKHSAH PHARMACEUTICALS"
            }
        }


class DrugInfo(BaseModel):
    """Drug information from database."""
    id: Optional[int] = Field(None, description="Database ID")
    sr_no: Optional[int] = Field(None, description="Serial number (DRAP)")
    registration_number: Optional[str] = Field(None, description="DRAP registration number")
    product_name: Optional[str] = Field(None, description="Product name (DRAP)")
    
    # OpenFDA fields
    product_ndc: Optional[str] = Field(None, description="FDA NDC (National Drug Code)")
    brand_name: Optional[str] = Field(None, description="Brand name")
    generic_name: Optional[str] = Field(None, description="Generic name of drug")
    labeler_name: Optional[str] = Field(None, description="Manufacturer/labeler name")
    company_name: Optional[str] = Field(None, description="Company name (DRAP)")
    
    # Ingredients
    tablet_core: Optional[str] = Field(None, description="Tablet core ingredients (DRAP)")
    tablet_coat: Optional[str] = Field(None, description="Tablet coating ingredients (DRAP)")
    active_ingredients: Optional[str] = Field(None, description="Active ingredients (FDA)")
    excipients: Optional[str] = Field(None, description="Non-tablet excipients")
    
    # FDA additional fields
    dosage_form: Optional[str] = Field(None, description="Dosage form")
    route: Optional[str] = Field(None, description="Route of administration")
    marketing_category: Optional[str] = Field(None, description="Marketing category")
    application_number: Optional[str] = Field(None, description="FDA application number")
    marketing_start_date: Optional[str] = Field(None, description="Marketing start date")
    listing_expiration_date: Optional[str] = Field(None, description="Listing expiration date")
    is_finished: Optional[int] = Field(None, description="Is finished (1=yes, 0=no)")
    
    class Config:
        extra = "allow"  # Allow additional fields


class VerificationResult(BaseModel):
    """Result of drug verification."""
    registration_number: str
    verdict: VerdictEnum
    score: int = Field(ge=0, description="Risk score (0-100)")
    reasons: List[str] = Field(default_factory=list, description="Reasons for verdict")
    db_record: Optional[DrugInfo] = None


class AnalysisResponse(BaseModel):
    """Response schema for drug analysis."""
    status: str = Field(description="Status of analysis: success or error")
    message: str = Field(description="Human-readable analysis result")
    verdict: Optional[VerdictEnum] = Field(None, description="Final verdict")
    registration_number: Optional[str] = Field(None, description="Identified registration number")
    product_name: Optional[str] = Field(None, description="Identified product name")
    drug_info: Optional[dict] = Field(None, description="Drug details from database")
    ingredients: Optional[str] = Field(None, description="Listed ingredients")
    risk_score: Optional[int] = Field(None, description="Overall risk score")
    flags: List[str] = Field(default_factory=list, description="Risk flags or warnings")
    confidence: Optional[float] = Field(None, description="OCR confidence (0-1)")
    
    class Config:
        extra = "allow"  # Allow additional fields
        schema_extra = {
            "example": {
                "status": "success",
                "message": "✅ VERIFIED - Drug is registered in DRAP database",
                "verdict": "VERIFIED",
                "registration_number": "134108",
                "product_name": "Axaleo 400mg",
                "drug_info": {
                    "sr_no": 1,
                    "registration_number": "134108",
                    "product_name": "Axaleo 400mg Tablet",
                    "generic_name": "Linezolid",
                    "company_name": "AKHSAH PHARMACEUTICALS (PVT) LTD."
                },
                "risk_score": 0,
                "flags": []
            }
        }


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    debug: bool
    database_connected: bool
