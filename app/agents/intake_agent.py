"""
app/agents/intake_agent.py
---------------------------
Intake agent for parsing user input and extracting structured information.
"""

import re
from app.services.llm_client import llm_client
from app.agents.prompts import INTAKE_AGENT_PROMPT
from app.core.logging import logger
from app.core.exceptions import AgentException


class IntakeAgent:
    """Agent for parsing and structuring user input."""
    
    def __init__(self):
        self.llm = llm_client
        self.prompt = INTAKE_AGENT_PROMPT
    
    def process(self, user_input: str) -> dict:
        """
        Process user input and extract structured fields.
        
        Parameters
        ----------
        user_input : str or dict
            Raw user input (text, path, or dict)
        
        Returns
        -------
        dict
            Structured intake data
        """
        try:
            # Convert dict input to string
            if isinstance(user_input, dict):
                return self._process_dict(user_input)
            elif isinstance(user_input, str):
                return self._process_string(user_input)
            else:
                raise AgentException(f"Unsupported input type: {type(user_input)}")
        except Exception as e:
            logger.error(f"Intake agent error: {e}")
            raise AgentException(f"Failed to process input: {e}")
    
    def _process_dict(self, data: dict) -> dict:
        """Process dictionary input directly."""
        return {
            "registration_number": data.get("registration_number") or data.get("reg_no"),
            "product_name": data.get("product_name"),
            "company_name": data.get("company_name"),
            "batch_number": data.get("batch_number"),
            "image_path": data.get("image_path"),
            "confidence": 1.0
        }
    
    def _process_string(self, text: str) -> dict:
        """Process string input using heuristics and LLM."""
        # First try heuristics
        heuristic_result = self._extract_heuristics(text)
        
        # If we got some data and it looks like an image path, return early
        if heuristic_result.get("image_path"):
            return heuristic_result
        
        # Otherwise use LLM for better extraction
        try:
            messages = [{"role": "user", "content": f"Extract drug information from this text:\n\n{text}"}]
            response = self.llm.call(
                messages=messages,
                system_prompt=self.prompt,
                json_mode=True,
                max_tokens=500
            )
            
            result = self.llm.extract_json(response)
            logger.info(f"Intake agent extracted: {result}")
            return result
            
        except Exception as e:
            logger.warning(f"LLM extraction failed, using heuristics: {e}")
            return heuristic_result
    
    def _extract_heuristics(self, text: str) -> dict:
        """Extract data using regex heuristics."""
        # Check for image path
        image_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")
        if any(text.lower().endswith(ext) for ext in image_exts):
            return {
                "image_path": text,
                "registration_number": None,
                "product_name": None,
                "company_name": None,
                "batch_number": None,
                "confidence": 0.9
            }
        
        # Extract registration number (5-7 digits)
        reg_pattern = r"\b(\d{5,7})\b"
        reg_match = re.search(reg_pattern, text)
        registration_number = reg_match.group(1) if reg_match else None
        
        # Extract batch number
        batch_pattern = r"\b(?:batch|lot|b\.?no\.?)[:\s#]*([A-Z0-9\-]+)"
        batch_match = re.search(batch_pattern, text, re.IGNORECASE)
        batch_number = batch_match.group(1) if batch_match else None
        
        return {
            "registration_number": registration_number,
            "product_name": None,
            "company_name": None,
            "batch_number": batch_number,
            "image_path": None,
            "confidence": 0.6
        }


# Global intake agent instance
intake_agent = IntakeAgent()
