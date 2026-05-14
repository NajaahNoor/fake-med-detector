"""
app/services/pipeline.py
------------------------
Main analysis pipeline orchestrating all agents.
"""

from app.agents.intake_agent import intake_agent
from app.agents.ocr_agent import ocr_agent
from app.agents.verification_agent import verification_agent
from app.agents.router_agent import router_agent
from app.core.logging import logger



class AnalysisPipeline:
    """Orchestrates the drug analysis pipeline."""
    
    def __init__(self):
        self.intake = intake_agent
        self.ocr = ocr_agent
        self.verification = verification_agent
        self.router = router_agent
    
    def analyze(self, user_input) -> dict:
        """
        Run full analysis pipeline.
        
        Parameters
        ----------
        user_input : str or dict
            User input (text, image path, or structured data)
        
        Returns
        -------
        dict
            Final analysis result
        """
        try:
            logger.info("Starting analysis pipeline...")
            
            # Step 1: Intake
            logger.info("Step 1: Intake agent processing input")
            intake_result = self.intake.process(user_input)
            
            registration_number = intake_result.get("registration_number")
            product_name = intake_result.get("product_name")
            company_name = intake_result.get("company_name")
            image_path = intake_result.get("image_path")
            
            ocr_confidence = 0.0
            ocr_text = ""
            
            # Step 2: OCR (if image provided)
            if image_path:
                logger.info(f"Step 2: OCR agent processing image: {image_path}")
                try:
                    ocr_result = self.ocr.process(image_path)
                    if ocr_result.get("registration_number"):
                        registration_number = ocr_result["registration_number"]
                    ocr_text = ocr_result.get("raw_text", "")
                    ocr_confidence = ocr_result.get("confidence", 0.0)
                    logger.info(f"OCR extracted: reg={registration_number}, conf={ocr_confidence:.2f}")
                except Exception as e:
                    logger.warning(f"OCR processing failed: {e}")
                    return self._error_response(f"Image processing failed: {e}")
            else:
                logger.info("Step 2: Skipping OCR (no image provided)")
            
            # Step 3: Verification
            if not registration_number:
                return self._error_response(
                    "Could not identify registration number. Please provide a clear image or registration number."
                )
            
            logger.info(f"Step 3: Verification agent checking reg_no: {registration_number}")
            verification_result = self.verification.process(
                registration_number=registration_number,
                labeler_name=company_name,
                brand_name=product_name
            )
            
            # Step 4: Router (format response)
            logger.info("Step 4: Router agent formatting response")
            final_response = self.router.process(
                registration_number=registration_number,
                verdict=verification_result["verdict"],
                score=verification_result["score"],
                reasons=verification_result["reasons"],
                db_record=verification_result["db_record"],
                brand_name=product_name or intake_result.get("product_name")
            )
            
            # Add metadata
            final_response["ocr_confidence"] = ocr_confidence
            final_response["ocr_text"] = ocr_text
            
            logger.info(f"Analysis pipeline complete - Verdict: {final_response['verdict']}")
            return final_response
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            return self._error_response(str(e))
    
    def _error_response(self, error_msg: str) -> dict:
        """Create error response."""
        return {
            "status": "error",
            "message": f"❌ **Analysis Failed**\n\n{error_msg}",
            "verdict": None,
            "registration_number": None,
            "product_name": None,
            "drug_info": None,
            "score": None,
            "flags": [],
            "action": "REVIEW"
        }


# Global pipeline instance
pipeline = AnalysisPipeline()
