"""
app/agents/router_agent.py
---------------------------
Router agent for formatting final response and determining next steps.
"""

from typing import Optional, List
from app.services.database import db
from app.core.logging import logger
from app.core.exceptions import AgentException


class RouterAgent:
    """Agent for formatting verification results into user-friendly responses."""
    
    def __init__(self):
        self.db = db
    
    def process(
        self,
        registration_number: str,
        verdict: str,
        score: int,
        reasons: List[str],
        db_record: Optional[dict] = None,
        brand_name: str = None,
        partial_matches: Optional[List[dict]] = None
    ) -> dict:
        """
        Format verification result into final response.
        
        Parameters
        ----------
        registration_number : str
            Drug NDC or application number
        verdict : str
            Verification verdict (VERIFIED, SUSPICIOUS, COUNTERFEIT)
        score : int
            Risk score
        reasons : List[str]
            Reasons for verdict
        db_record : dict, optional
            Drug information from database
        brand_name : str, optional
            Brand name
        
        Returns
        -------
        dict
            Formatted response with message and recommendations
        """
        try:
            # Get emoji for verdict
            verdict_emoji = self._get_verdict_emoji(verdict)
            
            # Format main message
            message_parts = [
                f"{verdict_emoji} **{verdict}**",
                "",
                "---",
                ""
            ]
            
            # Drug Information Section
            message_parts.append("## Drug Information")
            message_parts.append("")
            message_parts.append(f"**NDC/Application Number:** {registration_number}")
            
            if db_record:
                message_parts.append(f"**Brand Name:** {db_record.get('brand_name', 'N/A')}")
                if db_record.get('generic_name'):
                    message_parts.append(f"**Generic Name:** {db_record.get('generic_name', 'N/A')}")
                message_parts.append(f"**Manufacturer:** {db_record.get('labeler_name', 'N/A')}")
                if db_record.get('dosage_form'):
                    message_parts.append(f"**Dosage Form:** {db_record.get('dosage_form', 'N/A')}")
                if db_record.get('route'):
                    message_parts.append(f"**Route:** {db_record.get('route', 'N/A')}")
            elif brand_name:
                message_parts.append(f"**Brand Name:** {brand_name}")
            
            message_parts.append("")
            
            # Risk Assessment Section
            message_parts.append("## Risk Assessment")
            message_parts.append("")
            message_parts.append(f"**Risk Score:** {score}/100")
            message_parts.append(f"**Assessment Level:** {self._get_risk_level(score)}")
            message_parts.append("")
            
            if reasons:
                message_parts.append("**Flags & Warnings:**")
                for reason in reasons:
                    message_parts.append(f"- {reason}")
                message_parts.append("")
            else:
                message_parts.append("✅ No flags detected.")
                message_parts.append("")
            
            # Ingredients Section
            if db_record and self._has_ingredients(db_record):
                message_parts.append("## Ingredients")
                message_parts.append("")
                ingredients_text = self._format_ingredients(db_record)
                message_parts.append(ingredients_text)
                message_parts.append("")
            
            # Recommendation Section
            message_parts.append("## Recommendation")
            message_parts.append("")
            
            if verdict == "VERIFIED":
                message_parts.append(
                    "✅ This medicine is **registered and verified** in the FDA database. "
                    "It is safe to use if obtained from authorized sources."
                )
            elif verdict == "SUSPICIOUS":
                if partial_matches:
                    message_parts.append(
                        "⚠️ The detected number matches an FDA NDC labeler prefix, "
                        "but it is not a full product/package NDC. Please verify "
                        "the complete NDC from the label before using this medicine."
                    )
                else:
                    message_parts.append(
                        "⚠️ This medicine has some **discrepancies** in the database. "
                        "Please verify the batch number and packaging carefully. "
                        "Consider reporting to your health authority if concerns are confirmed."
                    )
            else:  # COUNTERFEIT
                message_parts.append(
                    "🚨 This medicine is **classified as COUNTERFEIT**. "
                    "**DO NOT USE THIS MEDICINE.** "
                    "A complaint has been automatically filed. "
                    "Please report this to the nearest health authority immediately."
                )
            
            message = "\n".join(message_parts)
            
            logger.info(f"Router formatted response for {registration_number}")
            
            return {
                "status": "success",
                "message": message,
                "verdict": verdict,
                "score": score,
                "registration_number": registration_number,
                "brand_name": db_record.get("brand_name") if db_record else brand_name,
                "drug_info": db_record,
                "partial_matches": partial_matches or [],
                "ingredients": self._format_ingredients(db_record) if db_record else None,
                "flags": reasons,
                "action": self._get_action(verdict)
            }
            
        except Exception as e:
            logger.error(f"Router error: {e}")
            raise AgentException(f"Failed to format response: {e}")
    
    def _get_verdict_emoji(self, verdict: str) -> str:
        """Get emoji for verdict."""
        emojis = {
            "VERIFIED": "✅",
            "SUSPICIOUS": "⚠️",
            "COUNTERFEIT": "🚨"
        }
        return emojis.get(verdict, "❓")
    
    def _get_risk_level(self, score: int) -> str:
        """Get risk level description."""
        if score <= 10:
            return "**LOW** - Verified Medicine"
        elif score <= 39:
            return "**MEDIUM** - Suspicious Activity Detected"
        else:
            return "**HIGH** - Likely Counterfeit"
    
    def _has_ingredients(self, db_record: dict) -> bool:
        """Check if record has ingredient information."""
        return any([
            db_record.get("active_ingredients"),
            db_record.get("excipients")
        ])
    
    def _format_ingredients(self, db_record: dict) -> str:
        """Format ingredients for display."""
        if not db_record:
            return "No ingredient information available."
        
        parts = []
        
        if db_record.get("active_ingredients"):
            parts.append(f"**Active Ingredients:** {db_record['active_ingredients']}")
        
        if db_record.get("excipients"):
            parts.append(f"**Excipients:** {db_record['excipients']}")
        
        return "\n".join(parts) if parts else "No ingredient information available."
    
    def _get_action(self, verdict: str) -> str:
        """Get recommended action."""
        actions = {
            "VERIFIED": "CLEAR",
            "SUSPICIOUS": "FLAG",
            "COUNTERFEIT": "COMPLAINT"
        }
        return actions.get(verdict, "REVIEW")


# Global router agent instance
router_agent = RouterAgent()
