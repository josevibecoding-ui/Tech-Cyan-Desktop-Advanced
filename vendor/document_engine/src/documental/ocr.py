"""OCR local con Tesseract: solo para páginas sin texto digital útil.

Reglas:
- Sin servicios OCR en la nube, sin modelos LLM locales, sin costes.
- OCR únicamente cuando la extracción digital no es suficiente.
- Procesamiento por página.
"""
import io
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import (
    DIGITAL_TEXT_THRESHOLD,
    OCR_DPI,
    OCR_ENABLED,
    OCR_LANGUAGES,
    TESSDATA_PREFIX,
    TESSERACT_CMD,
)

logger = logging.getLogger(__name__)

_configured = False
_available: Optional[bool] = None


def _configure() -> bool:
    """Configura pytesseract (binario y tessdata). Devuelve True si responde."""
    global _configured, _available
    if _configured:
        return bool(_available)
    _configured = True
    try:
        import pytesseract

        if TESSERACT_CMD and Path(TESSERACT_CMD).exists():
            pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_CMD)
        if TESSDATA_PREFIX and Path(TESSDATA_PREFIX).is_dir():
            os.environ["TESSDATA_PREFIX"] = str(TESSDATA_PREFIX)
        # Comprobación real de disponibilidad
        _ = str(pytesseract.get_tesseract_version())
        _available = True
        logger.info("Tesseract disponible: %s", _)
    except Exception as e:
        _available = False
        logger.warning("Tesseract no disponible: %s", e)
    return bool(_available)


def is_available() -> bool:
    """OCR habilitado en configuración y Tesseract instalado."""
    if not OCR_ENABLED:
        return False
    return _configure()


def engine_info() -> Dict[str, str]:
    """Motor, idioma y versión usados (para registrar por página)."""
    info = {"engine": "tesseract", "language": OCR_LANGUAGES, "version": ""}
    try:
        import pytesseract

        info["version"] = str(pytesseract.get_tesseract_version())
    except Exception:
        info["version"] = "desconocida"
    return info


def ocr_image_png(png_bytes: bytes, lang: Optional[str] = None) -> str:
    """OCR de una imagen PNG ya renderizada."""
    import pytesseract
    from PIL import Image

    _configure()
    img = Image.open(io.BytesIO(png_bytes))
    text = pytesseract.image_to_string(img, lang=lang or OCR_LANGUAGES)
    return (text or "").strip()


def ocr_pdf_page(filepath: Path, page_number: int, dpi: Optional[int] = None,
                 lang: Optional[str] = None) -> Dict[str, Any]:
    """OCR de una página concreta de un PDF.

    Devuelve dict con: text, ocr_engine, ocr_language, ocr_version, error.
    """
    result = {
        "text": "",
        "ocr_engine": "tesseract",
        "ocr_language": lang or OCR_LANGUAGES,
        "ocr_version": "",
        "error": None,
    }
    if not is_available():
        result["error"] = "ocr_no_disponible"
        return result
    try:
        import pymupdf

        with pymupdf.open(str(filepath)) as doc:
            if page_number < 1 or page_number > doc.page_count:
                result["error"] = f"pagina_invalida:{page_number}"
                return result
            pix = doc[page_number - 1].get_pixmap(dpi=dpi or OCR_DPI)
            png = pix.tobytes("png")
        result["text"] = ocr_image_png(png, lang=lang)
        info = engine_info()
        result["ocr_version"] = info["version"]
    except Exception as e:
        logger.error("OCR falló %s pág %s: %s", filepath, page_number, e)
        result["error"] = str(e)
    return result


def ocr_pages_if_needed(filepath: Path, results: List[Dict[str, Any]],
                        lang: Optional[str] = None) -> List[Dict[str, Any]]:
    """Aplica OCR solo a páginas cuya extracción digital no fue suficiente.

    `results` es la salida de extractor.extract_pdf_digital.
    Devuelve la misma lista con las páginas OCR actualizadas.
    """
    if not is_available():
        logger.warning("OCR omitido: Tesseract no disponible")
        return results

    pending = [r for r in results
               if r.get("quality_status") in ("empty", "suspicious")
               and r.get("page_number", 0) > 0]
    if not pending:
        return results

    logger.info("OCR: %s página(s) pendientes en %s", len(pending), filepath.name)
    for r in pending:
        res = ocr_pdf_page(filepath, r["page_number"], lang=lang)
        r["ocr_engine"] = res["ocr_engine"]
        r["ocr_language"] = res["ocr_language"]
        r["ocr_version"] = res["ocr_version"]
        if res["error"]:
            # Conserva estado ocr_required y comunica el fallo
            r["extraction_method"] = "ocr"
            r["quality_status"] = "ocr_required" if r["quality_status"] == "empty" else r["quality_status"]
            r["error_message"] = res["error"]
            continue
        text = res["text"]
        cc = len(text)
        if cc == 0:
            r["extraction_method"] = "ocr"
            r["quality_status"] = "ocr_required"
            r["error_message"] = "ocr_sin_texto"
        elif cc < DIGITAL_TEXT_THRESHOLD:
            r["text"] = text
            r["extraction_method"] = "ocr"
            r["quality_status"] = "suspicious"
            r["character_count"] = cc
            r["error_message"] = None
        else:
            r["text"] = text
            r["extraction_method"] = "ocr"
            r["quality_status"] = "ok"
            r["character_count"] = cc
            r["error_message"] = None
    return results
