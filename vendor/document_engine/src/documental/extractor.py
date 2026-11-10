"""Extractor digital por página con fallback pypdf ↔ pymupdf.

Estrategia (brecha de interoperabilidad, auditoría §3.3):
- pypdf es el backend primario; pymupdf es el respaldo.
- El fallback se activa ante ImportError, excepción de extracción
 o texto vacío en TODAS las páginas (pypdf puede devolver "" en
 PDFs válidos generados por otras librerías).
- Ambos backends devuelven la misma estructura: lista de texto crudo por página.
"""
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


def _import_pypdf():
    import pypdf
    return pypdf


def _import_pymupdf():
    import pymupdf
    return pymupdf

def normalize_text(text: str) -> str:
    import re
    return re.sub(r'\s+', ' ', text).strip()
def assess_text_quality(text: str, threshold: int = 10) -> dict:
    cc = len(text)
    if cc == 0: return {"has_useful_text": False, "character_count": 0, "quality_status": "empty", "extraction_method": "digital"}
    if cc < threshold: return {"has_useful_text": False, "character_count": cc, "quality_status": "suspicious", "extraction_method": "digital"}
    return {"has_useful_text": True, "character_count": cc, "quality_status": "ok", "extraction_method": "digital"}
def _extract_with_pypdf(filepath: Path) -> List[str]:
    """Backend primario: texto crudo por página con pypdf."""
    pypdf = _import_pypdf()
    reader = pypdf.PdfReader(str(filepath))
    return [page.extract_text() or "" for page in reader.pages]


def _extract_with_pymupdf(filepath: Path) -> List[str]:
    """Backend de respaldo: texto crudo por página con pymupdf."""
    pymupdf = _import_pymupdf()
    doc = pymupdf.open(str(filepath))
    try:
        return [page.get_text() or "" for page in doc]
    finally:
        doc.close()


def _backend_functions():
    """Se resuelven en tiempo de llamada para permitir monkeypatch en tests."""
    return (
        ("pypdf", _extract_with_pypdf),
        ("pymupdf", _extract_with_pymupdf),
    )


def extract_pdf_digital(filepath: Path) -> List[Dict[str, Any]]:
    """Extracción digital con fallback: pypdf primero, pymupdf como respaldo.

    Activa el fallback si el backend no se puede importar, si la extracción
    lanza excepción o si devuelve texto vacío en todas las páginas.
    Nunca lanza excepción: en fallo total retorna un registro 'failed'.
    """
    last_error: Optional[Exception] = None
    for backend_name, backend in _backend_functions():
        try:
            raw_pages = backend(filepath)
        except ImportError as e:
            logger.info("Backend %s no disponible: %s", backend_name, e)
            last_error = e
            continue
        except Exception as e:
            logger.warning("Backend %s falló en %s: %s", backend_name, filepath, e)
            last_error = e
            continue
        if not any(normalize_text(p) for p in raw_pages):
            # pypdf puede devolver cadenas vacías en PDFs válidos generados
            # por otras librerías (interoperabilidad pymupdf↔pypdf)
            logger.warning(
                "Backend %s devolvió texto vacío en todas las páginas de %s; "
                "probando fallback", backend_name, filepath)
            last_error = RuntimeError("texto vacío en todas las páginas")
            continue
        results = []
        for page_num, raw in enumerate(raw_pages, start=1):
            norm = normalize_text(raw)
            ass = assess_text_quality(norm)
            results.append({"document_id": str(filepath), "page_number": page_num,
                            "text": norm if ass["has_useful_text"] else "",
                            "extraction_method": ass["extraction_method"],
                            "quality_status": ass["quality_status"],
                            "character_count": ass["character_count"],
                            "error_message": None})
        logger.info("Extracción digital con backend %s: %d páginas (%s)",
                    backend_name, len(results), filepath)
        return results
    logger.error("Extracción fallida con todos los backends (%s): %s",
                 filepath, last_error)
    return [{"document_id": str(filepath), "page_number": 0, "text": "",
             "extraction_method": "failed", "quality_status": "failed",
             "character_count": 0, "error_message": str(last_error)}]

def extract_pdf(filepath: Path, use_ocr: bool = True) -> List[Dict[str, Any]]:
    """Extracción digital primero; OCR local solo en páginas sin texto útil."""
    results = extract_pdf_digital(filepath)
    if not use_ocr:
        return results
    from .ocr import is_available, ocr_pages_if_needed
    if not is_available():
        return results
    return ocr_pages_if_needed(filepath, results)