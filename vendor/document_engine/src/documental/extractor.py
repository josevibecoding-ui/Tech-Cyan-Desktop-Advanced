"""Extractor digital por página."""
import logging
from pathlib import Path
from typing import List, Dict, Any
import pypdf
logger = logging.getLogger(__name__)
def normalize_text(text: str) -> str:
    import re
    return re.sub(r'\s+', ' ', text).strip()
def assess_text_quality(text: str, threshold: int = 10) -> dict:
    cc = len(text)
    if cc == 0: return {"has_useful_text": False, "character_count": 0, "quality_status": "empty", "extraction_method": "digital"}
    if cc < threshold: return {"has_useful_text": False, "character_count": cc, "quality_status": "suspicious", "extraction_method": "digital"}
    return {"has_useful_text": True, "character_count": cc, "quality_status": "ok", "extraction_method": "digital"}
def extract_pdf_digital(filepath: Path) -> List[Dict[str, Any]]:
    results = []
    try:
        reader = pypdf.PdfReader(str(filepath))
        for page_num in range(1, len(reader.pages) + 1):
            raw = reader.pages[page_num - 1].extract_text()
            norm = normalize_text(raw)
            ass = assess_text_quality(norm)
            results.append({"document_id": str(filepath), "page_number": page_num,
                            "text": norm if ass["has_useful_text"] else "",
                            "extraction_method": ass["extraction_method"],
                            "quality_status": ass["quality_status"],
                            "character_count": ass["character_count"],
                            "error_message": None})
    except Exception as e:
        logger.error(f"Error {filepath}: {e}")
        results.append({"document_id": str(filepath), "page_number": 0, "text": "",
                        "extraction_method": "failed", "quality_status": "failed",
                        "character_count": 0, "error_message": str(e)})
    return results

def extract_pdf(filepath: Path, use_ocr: bool = True) -> List[Dict[str, Any]]:
    """Extracción digital primero; OCR local solo en páginas sin texto útil."""
    results = extract_pdf_digital(filepath)
    if not use_ocr:
        return results
    from .ocr import is_available, ocr_pages_if_needed
    if not is_available():
        return results
    return ocr_pages_if_needed(filepath, results)