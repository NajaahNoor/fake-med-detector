"""
complaint/complaint_drafter.py
-------------------------------
Auto-drafts a formal DRAP complaint letter as a .docx file.

The complaint is addressed to the Drug Regulatory Authority of Pakistan (DRAP)
and includes all relevant drug details, risk flags, and reporter information.

Usage (standalone):
    python complaint/complaint_drafter.py
"""

import os
from datetime import date
from typing import Optional

BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR    = os.path.join(BASE_DIR, "data", "complaints")


def _ensure_output_dir() -> str:
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    return OUTPUT_DIR


def draft_complaint(
    registration_number: str,
    drug_name:           str,
    company_name:        str,
    flags:               list,
    score:               int,
    batch_no:            str = "",
    reporter:            str = "",
    output_path:         Optional[str] = None,
) -> str:
    """
    Generate a formal DRAP complaint document (.docx).

    Parameters
    ----------
    registration_number : str
        DRAP registration number of the suspected counterfeit drug.
    drug_name : str
        Brand / product name of the drug.
    company_name : str
        Manufacturer name as it appears on the label.
    flags : list[str]
        List of risk flags from the verification agent.
    score : int
        Total risk score.
    batch_no : str
        Batch / lot number (optional).
    reporter : str
        Name or organisation filing the complaint (optional).
    output_path : str, optional
        Full path to save the .docx file. Auto-generated if not provided.

    Returns
    -------
    str
        Absolute path to the saved complaint document.
    """
    try:
        from docx import Document
        from docx.shared import Pt, Inches
        from docx.enum.text import WD_ALIGN_PARAGRAPH
    except ImportError:
        raise RuntimeError(
            "python-docx is required. Run: pip install python-docx"
        )

    today      = date.today().strftime("%B %d, %Y")
    batch_line = f"Batch / Lot No  : {batch_no}" if batch_no else "Batch / Lot No  : Not provided"
    reporter_  = reporter or "Concerned Citizen / Pharmacy Inspector"

    doc = Document()

    # ── Page margins ──────────────────────────────────────────────────────
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.25)
        section.right_margin  = Inches(1.25)

    # ── Header ────────────────────────────────────────────────────────────
    header = doc.add_paragraph()
    header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = header.add_run("DRUG REGULATORY AUTHORITY OF PAKISTAN (DRAP)")
    run.bold      = True
    run.font.size = Pt(14)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sub.add_run("Formal Complaint — Suspected Counterfeit / Unregistered Medicine").italic = True

    doc.add_paragraph()  # spacer

    # ── Date & Reference ──────────────────────────────────────────────────
    doc.add_paragraph(f"Date       : {today}")
    doc.add_paragraph(f"Subject    : Complaint Regarding Suspicious Drug — Reg. No. {registration_number}")
    doc.add_paragraph(f"Filed By   : {reporter_}")

    doc.add_paragraph()

    # ── Salutation ────────────────────────────────────────────────────────
    doc.add_paragraph("To,")
    doc.add_paragraph("The Director General,")
    doc.add_paragraph("Drug Regulatory Authority of Pakistan (DRAP),")
    doc.add_paragraph("Mauve Area, G-10/4, Islamabad, Pakistan.")
    doc.add_paragraph()

    doc.add_paragraph("Subject: Formal Complaint Regarding a Suspected Counterfeit/Unregistered Medicine").bold = False

    doc.add_paragraph()

    # ── Body ──────────────────────────────────────────────────────────────
    doc.add_paragraph(
        "Respected Sir/Madam,"
    )
    doc.add_paragraph(
        "I/We hereby submit this formal complaint to bring to your attention a medicine that has been "
        "identified as potentially counterfeit or unregistered by the DRAP Fake Medicine Detection & "
        "Pharmacy Audit System. The details of the suspect drug are as follows:"
    )

    doc.add_paragraph()

    # ── Drug Details Table ────────────────────────────────────────────────
    table = doc.add_table(rows=5, cols=2)
    table.style = "Table Grid"

    details = [
        ("Registration Number",  registration_number),
        ("Product / Drug Name",  drug_name or "Not provided"),
        ("Manufacturer / Company", company_name or "Not provided"),
        (batch_line.split(":")[0].strip(), batch_no or "Not provided"),
        ("Risk Score",           f"{score} / 100"),
    ]

    for i, (label, value) in enumerate(details):
        row = table.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        row.cells[0].paragraphs[0].runs[0].bold = True

    doc.add_paragraph()

    # ── Flags Section ─────────────────────────────────────────────────────
    doc.add_paragraph("The following risk flags were identified during the automated verification:").bold = False

    for flag in flags:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(flag)

    doc.add_paragraph()

    # ── Legal Reference ───────────────────────────────────────────────────
    doc.add_paragraph(
        "Under Section 23 of the DRAP Ordinance 2012, the manufacture, import, sale, or storage of "
        "counterfeit or substandard drugs is a punishable offence. We request DRAP to:"
    )

    actions = [
        "Investigate the authenticity of the above-mentioned drug.",
        "Conduct a surprise inspection of the pharmacy / distributor in question.",
        "Initiate legal proceedings if the drug is confirmed to be counterfeit or unregistered.",
        "Issue a public health alert if necessary.",
    ]
    for action in actions:
        p = doc.add_paragraph(style="List Number")
        p.add_run(action)

    doc.add_paragraph()
    doc.add_paragraph(
        "We are committed to cooperating fully with DRAP authorities and can provide additional "
        "evidence (label photographs, purchase receipts) upon request."
    )

    doc.add_paragraph()

    # ── Closing ───────────────────────────────────────────────────────────
    doc.add_paragraph("Respectfully submitted,")
    doc.add_paragraph()
    doc.add_paragraph(reporter_)
    doc.add_paragraph(f"Date: {today}")
    doc.add_paragraph()

    # ── Footer note ───────────────────────────────────────────────────────
    note = doc.add_paragraph()
    note.add_run(
        "This complaint was auto-generated by the DRAP Fake Medicine Detection & Pharmacy Audit Agent "
        "(FAST-NUCES). Risk scoring is based on the DRAP registration database and weighted heuristics."
    ).italic = True

    # ── Save ──────────────────────────────────────────────────────────────
    if not output_path:
        safe_reg = registration_number.replace("/", "_").replace("\\", "_")
        filename   = f"DRAP_Complaint_{safe_reg}_{date.today().strftime('%Y%m%d')}.docx"
        output_path = os.path.join(_ensure_output_dir(), filename)

    doc.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# CLI / demo
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    path = draft_complaint(
        registration_number="999999",
        drug_name="FakeMed 500mg Tablet",
        company_name="Unknown Pharma Ltd.",
        flags=[
            "Registration number 999999 NOT found in DRAP database.",
        ],
        score=40,
        batch_no="BT-2024-001",
        reporter="Demo Inspector",
    )
    print(f"Complaint saved to: {path}")