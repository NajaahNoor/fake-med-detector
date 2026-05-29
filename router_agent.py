"""
agents/router_agent.py
----------------------
Routes a VerificationResult to one of three output actions:

  CLEAR     → return a simple "Verified" message
  FLAG      → return a detailed explanation of suspicious flags
  COMPLAINT → trigger the complaint-drafting module
"""

from .verification_agent import VerificationResult


class RouterOutput:
    def __init__(
        self,
        action: str,
        message: str,
        verification: VerificationResult,
        complaint_doc_path: str = "",
    ):
        self.action             = action
        self.message            = message
        self.verification       = verification
        self.complaint_doc_path = complaint_doc_path

    def __repr__(self):
        return f"RouterOutput(action={self.action!r}, verdict={self.verification.verdict!r})"


def route(
    verification: VerificationResult,
    draft_complaint_fn=None,
    drug_name: str = "",
    batch_no:  str = "",
    reporter:  str = "",
) -> RouterOutput:
    """
    Route the verification result to the appropriate response.

    Parameters
    ----------
    verification      : VerificationResult from verification_agent.verify_drug()
    draft_complaint_fn: callable — complaint_drafter.draft_complaint (injected)
    drug_name         : human-readable drug name for complaint
    batch_no          : batch number for complaint
    reporter          : name/org of the person reporting (for complaint doc)
    """
    verdict = verification.verdict

    if verdict == "Verified":
        msg = (
            f"✅ **VERIFIED**\n\n"
            f"The drug with registration number **{verification.registration_number}** "
            f"is registered in the DRAP database.\n\n"
            f"{_db_details(verification)}"
        )
        return RouterOutput("CLEAR", msg, verification)

    elif verdict == "Suspicious":
        flag_lines = "\n".join(f"- {r}" for r in verification.reasons)
        msg = (
            f"⚠️ **SUSPICIOUS** (risk score: {verification.score})\n\n"
            f"This drug has been flagged for the following reason(s):\n\n"
            f"{flag_lines}\n\n"
            f"{_db_details(verification)}\n\n"
            f"Consider reporting to DRAP if discrepancies are confirmed."
        )
        return RouterOutput("FLAG", msg, verification)

    else:  # Counterfeit
        flag_lines = "\n".join(f"- {r}" for r in verification.reasons)
        msg = (
            f"🚨 **COUNTERFEIT** (risk score: {verification.score})\n\n"
            f"This drug is classified as **Counterfeit** based on:\n\n"
            f"{flag_lines}\n\n"
            f"A formal DRAP complaint has been auto-drafted."
        )
        doc_path = ""
        if draft_complaint_fn:
            try:
                doc_path = draft_complaint_fn(
                    registration_number=verification.registration_number,
                    drug_name=drug_name or (
                        verification.db_record.get("product_name", "Unknown")
                        if verification.db_record else "Unknown"
                    ),
                    company_name=(
                        verification.db_record.get("company_name", "Unknown")
                        if verification.db_record else "Unknown"
                    ),
                    batch_no=batch_no,
                    flags=verification.reasons,
                    score=verification.score,
                    reporter=reporter,
                )
            except Exception as e:
                msg += f"\n\n_(Complaint draft failed: {e})_"

        return RouterOutput("COMPLAINT", msg, verification, complaint_doc_path=doc_path)


def _db_details(v: VerificationResult) -> str:
    if not v.db_record:
        return ""
    rec = v.db_record
    return (
        f"**Product :** {rec.get('product_name', 'N/A')}\n"
        f"**Generic :** {rec.get('generic_name', 'N/A')}\n"
        f"**Company :** {rec.get('company_name', 'N/A')}"
    )