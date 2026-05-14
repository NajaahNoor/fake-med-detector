"""
ocr/ocr_agent.py
----------------
Uses PaddleOCR PP-OCRv5 to extract medicine registration numbers from
label images.

The agent:
1. Runs PP-OCRv5 over the provided image.
2. Searches all detected text blocks for patterns matching DRAP registration
   numbers (typically 5-7 digit numeric codes, e.g. "134108").
3. Returns the best candidate or the full raw OCR text if no number is matched.
"""

import re
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# DRAP Registration Number Pattern
# DRAP reg numbers appear as 5-7 digit numeric strings on labels,
# sometimes preceded by "Reg. No." or "REG NO" labels.
# ---------------------------------------------------------------------------
REG_NO_PATTERN = re.compile(r"\b(\d{5,7})\b")


def _load_ocr():
    """Lazy-load PaddleOCR PP-OCRv5 to avoid import overhead at startup."""
    try:
        from paddleocr import PaddleOCR  # type: ignore
        ocr = PaddleOCR(
            ocr_version="PP-OCRv4",   # Change to "PP-OCRv5" once paddleocr >= 2.8.0
            use_angle_cls=True,
            lang="en",
            show_log=False,
        )
        return ocr
    except ImportError:
        return None


_OCR_INSTANCE = None


def get_ocr():
    global _OCR_INSTANCE
    if _OCR_INSTANCE is None:
        _OCR_INSTANCE = _load_ocr()
    return _OCR_INSTANCE


class OCRResult:
    def __init__(self, registration_number: Optional[str], raw_text: str, confidence: float):
        self.registration_number = registration_number
        self.raw_text            = raw_text
        self.confidence          = confidence

    def __repr__(self):
        return (
            f"OCRResult(reg_no={self.registration_number!r}, "
            f"confidence={self.confidence:.2f})"
        )


def extract_registration_number(image_path: str) -> OCRResult:
    """
    Run PP-OCRv5 on *image_path* and return an OCRResult.

    Parameters
    ----------
    image_path : str
        Path to the medicine label image (JPEG, PNG, BMP, etc.)

    Returns
    -------
    OCRResult
        .registration_number  — best candidate string, or None
        .raw_text             — all detected text joined by spaces
        .confidence           — confidence of the matched block (0.0 if no match)
    """
    path = Path(image_path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")

    ocr = get_ocr()
    if ocr is None:
        raise RuntimeError(
            "PaddleOCR is not installed. Run: pip install paddlepaddle paddleocr"
        )

    result = ocr.ocr(str(path), cls=True)

    lines        = result[0] if result else []
    all_texts    = []
    best_reg_no  = None
    best_conf    = 0.0

    for line in lines:
        if not line:
            continue
        text, score = line[1]
        all_texts.append(text)

        match = REG_NO_PATTERN.search(text)
        if match and score > best_conf:
            context = text.lower()
            if any(kw in context for kw in ("reg", "registration", "reg.")):
                best_reg_no = match.group(1)
                best_conf   = score

    # Fallback: accept any 5-7-digit number if no labelled match found
    if best_reg_no is None:
        for line in lines:
            if not line:
                continue
            text, score = line[1]
            match = REG_NO_PATTERN.search(text)
            if match and score > best_conf:
                best_reg_no = match.group(1)
                best_conf   = score

    return OCRResult(
        registration_number=best_reg_no,
        raw_text=" | ".join(all_texts),
        confidence=best_conf,
    )


# ---------------------------------------------------------------------------
# CLI helper
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python ocr_agent.py <image_path>")
        sys.exit(1)

    res = extract_registration_number(sys.argv[1])
    print(f"Registration Number : {res.registration_number}")
    print(f"Confidence          : {res.confidence:.2f}")
    print(f"Raw OCR Text        : {res.raw_text}")