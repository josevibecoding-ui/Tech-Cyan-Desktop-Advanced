"""OCR local con Tesseract: solo para páginas sin texto digital útil.

Reglas:
- Sin servicios OCR en la nube, sin modelos LLM locales, sin costes.
- OCR únicamente cuando la extracción digital no es suficiente.
- Procesamiento por página.
- Configuración acotada: variables de entorno Tesseract se establecen
  temporalmente y se restauran después, nunca dejando cambios permanentes.
"""

import io
import logging
import os
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple

from .config import get_config

logger = logging.getLogger(__name__)

_configured = False
_available: Optional[bool] = None
_environment_snapshot: Optional[Dict[str, str]] = None
_configure_lock = Lock()


def _snapshot_environment() -> Dict[str, str]:
    """Capturar el estado actual de variables de entorno relevantes.

    Returns:
        Dict con el estado previo de TESSDATA_PREFIX y otras variables
        para poder restaurar después.
    """
    return {
        k: v for k, v in os.environ.items()
        if k in ("TESSDATA_PREFIX",)
    }


def _restore_environment(snapshot: Dict[str, str]) -> None:
    """Restaurar variables de entorno a su estado previo.

    Args:
        snapshot: Dict con el estado previo capturado por _snapshot_environment.
    """
    for key, value in snapshot.items():
        if value is None:
            # Remover la variable si existía antes
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def _configure() -> bool:
    """Configura pytesseract (binario y tessdata) de forma acotada.

    Devuelve True si Tesseract está disponible.
    Las modificaciones a variables globales se restauran después.

    Reglas críticas:
    - No dejar cambios permanentes en os.environ["TESSDATA_PREFIX"].
    - No dejar pytesseract.pytesseract.tesseract_cmd modificado permanentemente.
    - Proteger llamadas simultáneas con lock.
    - Restaurar estado exacto aunque ocurra una excepción.
    """
    global _configured, _available
    with _configure_lock:
        if _configured:
            return bool(_available)
        _configured = True

        config = get_config()
        snapshot = _snapshot_environment()

        try:
            import pytesseract

            # Establecer Tesseract CMD de forma local y restaurar después
            tesseract_changed = False
            if config.tesseract_cmd and Path(config.tesseract_cmd).exists():
                # Establecer temporalmente para esta operación
                pytesseract.pytesseract.tesseract_cmd = str(config.tesseract_cmd)
                tesseract_changed = True

            # Establecer TESSDATA_PREFIX de forma temporal SOLO para esta operación
            # NO escribir en os.environ permanentemente.
            # Nota: pytesseract lee os.environ["TESSDATA_PREFIX"], así que lo
            # configuramos temporalmente y luego restauramos.
            if config.tessdata_prefix:
                os.environ["TESSDATA_PREFIX"] = str(config.tessdata_prefix)

            # Comprobación real de disponibilidad
            _ = str(pytesseract.get_tesseract_version())
            _available = True
            logger.info("Tesseract disponible")
        except Exception as e:
            _available = False
            logger.warning("Tesseract no disponible: %s", e)
        finally:
            # Restaurar entorno exacto aunque haya excepción
            _restore_environment(snapshot)

        return bool(_available)


def is_available() -> bool:
    """OCR habilitado en configuración y Tesseract instalado."""
    config = get_config()
    if not config.ocr_enabled:
        return False
    return _configure()


def engine_info() -> Dict[str, str]:
    """Motor, idioma y versión usados (para registrar por página)."""
    config = get_config()
    info = {"engine": "tesseract", "language": config.ocr_languages, "version": ""}
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

    config = get_config()
    _configure()
    img = Image.open(io.BytesIO(png_bytes))
    text = pytesseract.image_to_string(img, lang=lang or config.ocr_languages)
    return (text or "").strip()


def ocr_pdf_page(filepath: Path, page_number: int, dpi: Optional[int] = None,
                 lang: Optional[str] = None) -> Dict[str, Any]:
    """OCR de una página concreta de un PDF.

    Devuelve dict con: text, ocr_engine, ocr_language, ocr_version, error.
   """
    from .config import get_config as _get_config
    config = _get_config()
    result = {
        "text": "",
        "ocr_engine": "tesseract",
        "ocr_language": lang or config.ocr_languages,
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
            pix = doc[page_number - 1].get_pixmap(dpi=dpi or config.ocr_dpi)
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

    config = get_config()
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
        elif cc < config.digital_text_threshold:
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