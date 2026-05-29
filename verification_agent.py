"""
agents/verification_agent.py
-----------------------------
Queries the local DRAP SQLite database and applies the risk-scoring
rule engine defined in the proposal.

Risk Score Weights
------------------
+40  Drug not found in DRAP database (unregistered)
+30  Drug found but marked as expired
+20  Manufacturer / company name mismatch (if user supplied a company name)

Verdict Thresholds
------------------
 0 – 10  → Verified     ✅
11 – 39  → Suspicious   ⚠️
40+      → Counterfeit  🚨
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dataclasses import dataclass, field
from typing import Optional

from .db_manager import lookup_by_registration


SCORE_NOT_FOUND  = 40
SCORE_EXPIRED    = 30
SCORE_MISMATCH   = 20

THRESHOLD_VERIFIED   = 10
THRESHOLD_SUSPICIOUS = 39


@dataclass
class VerificationResult:
    registration_number: str
    score:               int            = 0
    verdict:             str            = "Verified"
    db_record:           Optional[dict] = None
    reasons:             list           = field(default_factory=list)

    @property
    def verdict_emoji(self) -> str:
        return {"Verified": "✅", "Suspicious": "⚠️", "Counterfeit": "🚨"}.get(self.verdict, "")

    def summary(self) -> str:
        lines = [
            f"Registration No : {self.registration_number}",
            f"Verdict         : {self.verdict_emoji} {self.verdict}  (score: {self.score})",
        ]
        if self.db_record:
            lines += [
                f"Product         : {self.db_record.get('product_name', 'N/A')}",
                f"Generic         : {self.db_record.get('generic_name', 'N/A')}",
                f"Company         : {self.db_record.get('company_name', 'N/A')}",
            ]
        if self.reasons:
            lines.append("Flags           :")
            for r in self.reasons:
                lines.append(f"  • {r}")
        return "\n".join(lines)


def _derive_verdict(score: int) -> str:
    if score <= THRESHOLD_VERIFIED:
        return "Verified"
    if score <= THRESHOLD_SUSPICIOUS:
        return "Suspicious"
    return "Counterfeit"


def verify_drug(
    registration_number: str,
    supplied_company_name: Optional[str] = None,
) -> VerificationResult:
    """
    Perform database lookup and apply the risk-scoring rule engine.

    Parameters
    ----------
    registration_number : str
        DRAP registration number to check.
    supplied_company_name : str, optional
        Company name provided by the user (for mismatch check).

    Returns
    -------
    VerificationResult
    """
    reg_no = str(registration_number).strip()
    result = VerificationResult(registration_number=reg_no)

    record = lookup_by_registration(reg_no)

    # Rule 1 — Not found
    if record is None:
        result.score  += SCORE_NOT_FOUND
        result.reasons.append(f"Registration number {reg_no} NOT found in DRAP database.")
        result.verdict = _derive_verdict(result.score)
        return result

    result.db_record = record

    # Rule 2 — Expired
    if record.get("is_expired", 0):
        result.score  += SCORE_EXPIRED
        result.reasons.append("Drug registration is EXPIRED in the DRAP database.")

    # Rule 3 — Manufacturer mismatch
    if supplied_company_name:
        db_company   = (record.get("company_name") or "").lower().strip()
        user_company = supplied_company_name.lower().strip()
        if user_company and user_company not in db_company and db_company not in user_company:
            result.score  += SCORE_MISMATCH
            result.reasons.append(
                f"Manufacturer mismatch: label says '{supplied_company_name}', "
                f"database has '{record.get('company_name', 'N/A')}'."
            )

    result.verdict = _derive_verdict(result.score)
    return result