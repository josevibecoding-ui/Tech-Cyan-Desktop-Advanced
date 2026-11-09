"""Evidencia citable: deduplicación, identificadores y presupuesto de contexto.

Reglas (AGENTS.md §6 y §11):
- los fragmentos se deduplican sin perder las referencias de origen;
- cada evidencia recibe un ID estable (E1, E2, ...);
- el contexto se limita por relevancia (orden FTS5), no por corte arbitrario;
- la cita es `NombreArchivo.pdf | ruta relativa | pág. X`.
"""
import re
from typing import Any, Dict, List, Optional

from .config import (
    AI_MAX_CONTEXT_CHARS,
    AI_MAX_EVIDENCE,
    AI_MAX_FRAGMENT_CHARS,
)

_WS = re.compile(r"\s+")


def normalize_fragment(text: Optional[str]) -> str:
    return _WS.sub(" ", text or "").strip()


def citation_for(ref: Dict[str, Any]) -> str:
    filename = ref.get("filename") or ref.get("document_id") or "?"
    rel = ref.get("relative_path") or ref.get("document_id") or "?"
    page = ref.get("page_number", "?")
    return f"{filename} | {rel} | pág. {page}"


def _truncate(text: str, limit: int) -> str:
    """Trunca en frontera de palabra (no a mitad de palabra)."""
    if limit <= 0 or len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > int(limit * 0.6):
        cut = cut[:sp]
    return cut.rstrip() + " ..."


def build_evidence(rows: List[Dict[str, Any]],
                   max_items: Optional[int] = None,
                   fragment_chars: Optional[int] = None,
                   context_chars: Optional[int] = None) -> List[Dict[str, Any]]:
    """Construye la lista de evidencia desde filas de búsqueda (orden de relevancia).

    Cada fila debe traer: filename, relative_path, document_id, page_number, text.
    Filas con texto idéntico se fusionan en una evidencia con varias referencias.
    """
    max_items = max_items or AI_MAX_EVIDENCE
    fragment_chars = fragment_chars or AI_MAX_FRAGMENT_CHARS
    context_chars = context_chars or AI_MAX_CONTEXT_CHARS

    evidence: List[Dict[str, Any]] = []
    by_text: Dict[str, Dict[str, Any]] = {}
    used_chars = 0

    for row in rows:
        if len(evidence) >= max_items:
            break
        text = normalize_fragment(row.get("text"))
        if not text:
            continue
        key = text
        ref = {
            "document_id": row.get("document_id"),
            "filename": row.get("filename"),
            "relative_path": row.get("relative_path"),
            "page_number": row.get("page_number"),
        }
        if key in by_text:
            # Deduplicar sin perder la referencia de origen
            entry = by_text[key]
            if all(r.get("document_id") != ref["document_id"]
                   or r.get("page_number") != ref["page_number"]
                   for r in entry["refs"]):
                entry["refs"].append(ref)
            continue
        frag = _truncate(text, fragment_chars)
        cost = len(frag)
        if evidence and used_chars + cost > context_chars:
            # Presupuesto de contexto: se respeta; al menos una evidencia siempre
            continue
        entry = {
            "id": f"E{len(evidence) + 1}",
            "text": frag,
            "refs": [ref],
        }
        by_text[key] = entry
        evidence.append(entry)
        used_chars += cost

    return evidence


def evidence_lines(evidence: List[Dict[str, Any]]) -> List[str]:
    """Bloques de evidencia para el prompt de un proveedor."""
    lines = []
    for e in evidence:
        cits = " / ".join(citation_for(r) for r in e["refs"])
        lines.append(f"[{e['id']}] {cits}\n«{e['text']}»")
    return lines
