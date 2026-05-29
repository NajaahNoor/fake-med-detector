"""
app/agents/verification_agent.py
----------------------------------
Verification agent for checking drugs against DRAP database and calculating risk scores.
"""

from app.services.database import db
from app.services.llm_client import llm_client
from app.agents.prompts import VERIFICATION_AGENT_PROMPT
from app.core.logging import logger
from app.core.exceptions import VerificationException


class VerificationAgent:
    """Agent for verifying drugs against the DRAP database."""
    
    SCORE_NOT_FOUND = 40
    SCORE_EXPIRED = 30
    SCORE_MISMATCH = 20
    
    def __init__(self):
        self.llm = llm_client
        self.prompt = VERIFICATION_AGENT_PROMPT
        self.db = db
    
    def process(
        self,
        registration_number: str,
        labeler_name: str = None,
        brand_name: str = None
    ) -> dict:
        """
        Verify drug registration (FDA application number) and calculate risk score.
        
        Parameters
        ----------
        registration_number : str
            FDA application number or NDC
        labeler_name : str, optional
            Manufacturer/labeler name to verify
        brand_name : str, optional
            Brand name to verify
        
        Returns
        -------
        dict
            Verification result with verdict and score
        """
        try:
            if not registration_number:
                raise VerificationException("Registration number required")
            
            # Lookup in database by application number, product NDC, or package NDC.
            db_record = self.db.lookup_by_registration(registration_number)
            partial_matches = []
            
            # If still not found and brand name provided, try searching by brand name
            if not db_record and brand_name:
                results = self.db.search_by_name(brand_name, limit=1)
                db_record = results[0] if results else None
            
            # Calculate risk score
            score = 0
            reasons = []
            
            if not db_record:
                partial_matches = self.db.lookup_ndc_prefix(registration_number)
                if partial_matches:
                    score += self.SCORE_MISMATCH
                    reasons.append(
                        "Only a partial NDC labeler prefix was detected. "
                        "The prefix exists in the FDA database, but the full "
                        "product/package NDC is required to verify one medicine."
                    )
                else:
                    score += self.SCORE_NOT_FOUND
                    reasons.append("Drug not found in FDA database (unregistered)")
            else:
                # Check if not finished (discontinued)
                is_finished = db_record.get("is_finished", 1)
                if not is_finished:
                    score += self.SCORE_EXPIRED
                    reasons.append("Drug is marked as not finished/discontinued in FDA database")
                
                # Check labeler mismatch
                if labeler_name and db_record.get("labeler_name"):
                    if not self._names_match(labeler_name, db_record["labeler_name"]):
                        score += self.SCORE_MISMATCH
                        reasons.append(
                            f"Manufacturer mismatch: claimed '{labeler_name}' but "
                            f"registered as '{db_record['labeler_name']}'"
                        )
            
            # Determine verdict
            verdict = self._get_verdict(score)
            
            logger.info(
                f"Verification complete - Reg: {registration_number}, "
                f"Score: {score}, Verdict: {verdict}"
            )
            
            return {
                "registration_number": registration_number,
                "verdict": verdict,
                "score": score,
                "reasons": reasons,
                "db_record": dict(db_record) if db_record else None,
                "partial_matches": partial_matches,
                "confidence": 0.95 if db_record else 0.85
            }
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            raise VerificationException(f"Verification failed: {e}")
    
    def _names_match(self, name1: str, name2: str) -> bool:
        """Check if two company names match (fuzzy)."""
        # Normalize names
        n1 = name1.upper().strip()
        n2 = name2.upper().strip()
        
        # Exact match
        if n1 == n2:
            return True
        
        # Partial match (at least 70% similar)
        # Simple approach: check if most of name1 is in name2
        words1 = set(n1.split())
        words2 = set(n2.split())
        
        if len(words1) == 0:
            return False
        
        matching_words = words1.intersection(words2)
        similarity = len(matching_words) / len(words1)
        
        return similarity >= 0.7
    
    def _get_verdict(self, score: int) -> str:
        """Map risk score to verdict."""
        if score <= 10:
            return "VERIFIED"
        elif score <= 39:
            return "SUSPICIOUS"
        else:
            return "COUNTERFEIT"


# Global verification agent instance
verification_agent = VerificationAgent()
