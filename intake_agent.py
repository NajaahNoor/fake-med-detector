"""
agents/intake_agent.py
----------------------
Extracts structured fields from raw user input.
Accepted inputs:
  - Free-text string  (e.g. "Check registration 134108 for Axaleo 400mg")
  - Dict with explicit keys
  - Image path (delegated to OCR agent downstream)
"""

import re
from dataclasses import dataclass, field
from typing import Optional

REG_NO_RE   = re.compile(r"\b(\d{5,7})\b")
BATCH_NO_RE = re.compile(r"\b(?:batch|lot|b\.?no\.?)[:\s#]*([A-Z0-9\-]+)", re.IGNORECASE)


@dataclass
class IntakeData:
    registration_number: Optional[str] = None
    product_name:        Optional[str] = None
    generic_name:        Optional[str] = None
    batch_number:        Optional[str] = None
    company_name:        Optional[str] = None
    image_path:          Optional[str] = None
    raw_input:           str           = ""
    errors:              list = field(default_factory=list)


def parse_input(user_input) -> IntakeData:
    """
    Accepts a string, dict, or file-path string and returns an IntakeData.

    String input
    ------------
    Heuristics extract registration number and batch number from free text.

    Dict input
    ----------
    Expected keys (all optional):
        registration_number, product_name, generic_name,
        batch_number, company_name, image_path

    Image path input
    ----------------
    If the string looks like a file path to an image, it is stored as
    image_path and registration_number is left for the OCR agent to fill.
    """
    data = IntakeData()

    if isinstance(user_input, dict):
        data.registration_number = user_input.get("registration_number") or user_input.get("reg_no")
        data.product_name        = user_input.get("product_name")
        data.generic_name        = user_input.get("generic_name")
        data.batch_number        = user_input.get("batch_number")
        data.company_name        = user_input.get("company_name")
        data.image_path          = user_input.get("image_path")
        data.raw_input           = str(user_input)

    elif isinstance(user_input, str):
        data.raw_input = user_input

        # Detect image path
        image_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp")
        if any(user_input.lower().endswith(ext) for ext in image_exts):
            data.image_path = user_input
        else:
            # Extract registration number
            reg_match = REG_NO_RE.search(user_input)
            if reg_match:
                data.registration_number = reg_match.group(1)

            # Extract batch number
            batch_match = BATCH_NO_RE.search(user_input)
            if batch_match:
                data.batch_number = batch_match.group(1)
    else:
        data.errors.append(f"Unsupported input type: {type(user_input)}")

    # Validate: we need at least a reg number or an image
    if not data.registration_number and not data.image_path:
        data.errors.append(
            "No registration number or image detected. "
            "Please provide a 5-7 digit DRAP registration number or upload a label image."
        )

    return data