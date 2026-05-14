"""
app/agents/ocr_agent.py
------------------------
OCR agent for extracting drug information from medicine label images using PP-OCRv5.
Integrates the OneDNN workaround for PaddlePaddle 3.0.0.
"""

import os
import re
from pathlib import Path
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import OCRException
from app.agents.prompts import OCR_AGENT_PROMPT


# Set environment variables BEFORE importing PaddleOCR
os.environ["FLAGS_use_onednn"] = str(settings.flags_use_onednn)
os.environ["FLAGS_use_mkldnn"] = str(settings.flags_use_mkldnn)

try:
    from paddleocr import PaddleOCR
    OCR_AVAILABLE = True
except ImportError:
    logger.warning("PaddleOCR not installed, OCR functionality will be limited")
    OCR_AVAILABLE = False


class OCRAgent:
    """Agent for extracting text from medicine label images."""
    
    REG_NO_PATTERN = re.compile(r"\b(\d{5,7})\b")
    
    def __init__(self):
        """Initialize OCR agent (lazy load model on first use)."""
        self.prompt = OCR_AGENT_PROMPT
        self.ocr_model = None
        self._model_loaded = False
    
    def _load_ocr_model(self):
        """Load PP-OCRv5 model with workaround for OneDNN issues."""
        if self._model_loaded:
            return self.ocr_model
        
        if not OCR_AVAILABLE:
            logger.warning("PaddleOCR not available")
            return None
        
        try:
            logger.info("Loading PP-OCR model...")
            ocr = PaddleOCR(
                ocr_version=settings.ocr_version,
                use_angle_cls=settings.ocr_use_angle_cls,
                lang=settings.ocr_lang,
            )
            self.ocr_model = ocr
            self._model_loaded = True
            logger.info(f"PP-OCR model loaded (version: {settings.ocr_version})")
            return ocr
        except Exception as e:
            logger.error(f"Failed to load OCR model: {e}")
            raise OCRException(f"Failed to load OCR model: {e}")
    
    def process(self, image_path: str) -> dict:
        """
        Extract text and registration number from image.
        
        Parameters
        ----------
        image_path : str
            Path to medicine label image
        
        Returns
        -------
        dict
            Extracted data: registration_number, product_name, raw_text, confidence
        """
        if not OCR_AVAILABLE:
            logger.warning("OCR not available, returning empty result")
            return {
                "registration_number": None,
                "product_name": None,
                "raw_text": "",
                "confidence": 0.0
            }
        
        try:
            # Lazy load model on first use
            ocr = self._load_ocr_model()
            if not ocr:
                logger.warning("OCR model not available")
                return {
                    "registration_number": None,
                    "product_name": None,
                    "raw_text": "",
                    "confidence": 0.0
                }
            
            # Validate image path
            path = Path(image_path)
            if not path.exists():
                raise OCRException(f"Image not found: {image_path}")
            
            # Run OCR (removed cls parameter for compatibility)
            logger.info(f"Running OCR on image: {image_path}")
            result = ocr.ocr(str(path))
            
            # Extract text and confidence
            raw_text_parts = []
            confidences = []
            
            # Handle different result formats from PaddleOCR/PaddleX
            if result:
                # Format 1: List of pages with OCRResult objects (PaddleX v3)
                if isinstance(result, list) and len(result) > 0:
                    page_result = result[0]
                    
                    # Check if it's an OCRResult object (has rec_texts and rec_scores)
                    if hasattr(page_result, 'rec_texts') and hasattr(page_result, 'rec_scores'):
                        # PaddleX OCRResult format
                        texts = page_result.rec_texts or []
                        scores = page_result.rec_scores or []
                        logger.info(f"Processing OCRResult: {len(texts)} texts found")
                        
                        for i, text in enumerate(texts):
                            try:
                                conf = scores[i] if i < len(scores) else 0.9
                                if isinstance(conf, str):
                                    conf = float(conf)
                                if text and text.strip():  # Only add non-empty text
                                    raw_text_parts.append(text)
                                    confidences.append(conf)
                                    logger.debug(f"Extracted: '{text}' (conf: {conf})")
                            except (ValueError, TypeError, IndexError) as e:
                                logger.debug(f"Failed to parse OCRResult item: {e}")
                                continue
                    # Format 2: Traditional list format [[points], text, confidence]
                    elif isinstance(page_result, list):
                        for text_box in page_result:
                            try:
                                if text_box and len(text_box) >= 2:
                                    text = text_box[1]  # text content
                                    conf = text_box[2] if len(text_box) > 2 else 0.9  # confidence
                                    
                                    if isinstance(conf, str):
                                        conf = float(conf.replace('p', '').replace('%', '')) / 100.0
                                    else:
                                        conf = float(conf)
                                    
                                    if text and text.strip():
                                        raw_text_parts.append(text)
                                        confidences.append(conf)
                            except (ValueError, TypeError, IndexError) as e:
                                logger.debug(f"Failed to parse traditional format: {e}")
                                continue
                    # Format 3: Dict with 'texts' (Alternate PaddleX)
                    elif isinstance(page_result, dict):
                        if 'rec_texts' in page_result and 'rec_scores' in page_result:
                            texts = page_result.get('rec_texts', [])
                            scores = page_result.get('rec_scores', [])
                            for i, text in enumerate(texts):
                                try:
                                    conf = scores[i] if i < len(scores) else 0.9
                                    if isinstance(conf, str):
                                        conf = float(conf)
                                    if text and text.strip():
                                        raw_text_parts.append(text)
                                        confidences.append(conf)
                                except (ValueError, TypeError, IndexError):
                                    continue
            
            raw_text = " ".join(raw_text_parts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            # Log the extracted text for debugging
            logger.info(f"OCR extracted text: {raw_text[:200] if raw_text else 'EMPTY'}")
            
            # Extract registration number using regex
            reg_match = self.REG_NO_PATTERN.search(raw_text)
            registration_number = reg_match.group(1) if reg_match else None
            
            logger.info(
                f"OCR complete - Found reg_no: {registration_number}, "
                f"confidence: {avg_confidence:.2f}"
            )
            
            return {
                "registration_number": registration_number,
                "product_name": None,  # Could be extracted with more sophisticated NLP
                "raw_text": raw_text,
                "confidence": avg_confidence
            }
            
        except Exception as e:
            logger.error(f"OCR processing error: {e}")
            raise OCRException(f"Failed to process image: {e}")


# Global OCR agent instance
# Note: Model is loaded lazily on first use, not at startup
ocr_agent = OCRAgent()
