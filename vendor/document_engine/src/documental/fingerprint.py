"""Fingerprint: SHA-256 para detección de cambios y duplicados exactos.

Regras (AGENTS.md §7 y §8):
- SHA-256 del contenido binario; nunca del nombre base.
- Se registra también tamaño, fecha de modificación y conteo de páginas.
- Dos rutas con contenido idéntico conservan dos registros de ubicación.
"""
import hashlib
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pypdf

_CHUNK = 1024 * 1024


def compute_sha256(filepath: Path) -> str:
    """SHA-256 del contenido del archivo, por bloques (sin cargarlo en memoria)."""
    h = hashlib.sha256()
    with Path(filepath).open("rb") as f:
        for chunk in iter(lambda: f.read(_CHUNK), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_file_metadata(filepath: Path) -> Dict[str, Any]:
    """Hash, tamaño, fecha de modificación y conteo de páginas de un archivo."""
    p = Path(filepath)
    stat = p.stat()
    # Obtener conteo de páginas usando pypdf (misma librería que extractor.py)
    try:
        reader = pypdf.PdfReader(str(p))
        page_count = len(reader.pages)
    except Exception:
        page_count = 0
    return {
        "content_sha256": compute_sha256(p),
        "file_size": stat.st_size,
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(
            timespec="seconds"),
        "page_count": page_count,
    }


def normalize_document_id(relative_path: str) -> str:
    """Normaliza un identificador derivado de la ruta relativa (Unicode NFC)."""
    normalized = unicodedata.normalize("NFC", relative_path or "")
    return " ".join(normalized.split())