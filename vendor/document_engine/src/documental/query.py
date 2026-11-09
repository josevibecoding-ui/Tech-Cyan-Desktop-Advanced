"""Consulta ordinaria: pregunta -> FTS5 -> evidencia -> proveedor -> cita verificada.

Flujo (AGENTS.md §6):
1. interpretar términos;
2. consultar SQLite FTS5 (nunca la carpeta fuente);
3. recuperar documento, ruta relativa, página y fragmento;
4. deduplicar sin perder referencias;
5. limitar el contexto por relevancia;
6. si el proveedor es mock, responder con resultados y declarar que no hubo IA;
7. validar que cada cita corresponda a un ID de evidencia entregado;
8. declarar explícitamente cuando no hay evidencia suficiente.
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .database import Repository
from .evidence import build_evidence, citation_for
from .providers import (OUTPUT_INSTRUCTIONS, Provider, ProviderError,
                        get_provider, validate_citations)

logger = logging.getLogger(__name__)

# Palabras vacías del español para interpretar la pregunta
_STOPWORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "u", "que", "en", "con", "por", "para", "se", "su", "sus", "lo",
    "le", "les", "es", "son", "esta", "este", "estos", "estas", "como", "mas",
    "más", "muy", "sin", "sobre", "cuando", "donde", "cual", "cuál", "quien",
    "quién", "qué", "cómo", "porque", "pero", "tambien", "también", "ya",
    "hay", "tiene", "puede", "hace", "entre", "hasta", "desde", "ese", "esa",
    "eso", "aquel", "mismo", "todo", "todos", "cada", "otro", "otra",
}


@dataclass
class QueryResult:
    question: str
    provider: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    citations: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


def extract_terms(question: str) -> List[str]:
    """Extrae términos significativos de la pregunta (sin palabras vacías)."""
    tokens = re.findall(r"[^\W\d_][\wáéíóúüñÁÉÍÓÚÜÑ\-]{1,}", question or "",
                        re.UNICODE)
    terms = []
    seen = set()
    for t in tokens:
        tl = t.lower().strip("-")
        if len(tl) < 3 or tl in _STOPWORDS:
            continue
        if tl not in seen:
            seen.add(tl)
            terms.append(tl)
    return terms


def build_fts_query(terms: List[str]) -> str:
    """Construye una consulta FTS5 con OR entre términos (acento-insensible)."""
    quoted = " OR ".join(f'"{t}"' for t in terms)
    return quoted


def search_evidence(repo: Repository, question: str,
                    limit: int) -> List[Dict[str, Any]]:
    """Recupera filas relevantes de FTS5 con metadatos de cita."""
    terms = extract_terms(question)
    if not terms:
        return []
    fts_query = build_fts_query(terms)
    sql = """
        SELECT f.document_id, f.page_number, f.text,
               d.filename, d.relative_path
        FROM pages_fts f
        JOIN documents d ON d.document_id = f.document_id
        WHERE pages_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """
    try:
        cur = repo.conn.execute(sql, (fts_query, limit))
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    except Exception as e:
        logger.warning("FTS5 falló en consulta, usando LIKE: %s", e)
        rows = []
        for t in terms:
            cur = repo.conn.execute(
                """SELECT p.document_id, p.page_number, p.text,
                          d.filename, d.relative_path
                   FROM pages p JOIN documents d ON d.document_id = p.document_id
                   WHERE p.text LIKE ? LIMIT ?""", (f"%{t}%", limit))
            cols = [d[0] for d in cur.description]
            rows.extend(dict(zip(cols, r)) for r in cur.fetchall())
    return rows


def run_query(question: str, provider_mode: Optional[str] = None,
              evidence_limit: int = 12, evidence_items: int = 8,
              repo: Optional[Repository] = None) -> QueryResult:
    """Ejecuta una consulta completa con evidencia y cita verificada."""
    result = QueryResult(question=question, provider=provider_mode or "mock")
    q = (question or "").strip()
    if not q:
        result.error = "Pregunta vacía."
        return result

    own_repo = repo is None
    if own_repo:
        repo = Repository()
    try:
        # 1-4: búsqueda y evidencia (nunca se abre la carpeta fuente)
        rows = search_evidence(repo, q, evidence_limit)
        result.evidence = build_evidence(rows, max_items=evidence_items)
        if not result.evidence:
            result.answer = ("No se encontró evidencia suficiente en el índice "
                             "para responder la pregunta.")
            result.warnings.append("sin_evidencia")
            return result

        # 5-6: proveedor (mock por defecto, sin red)
        try:
            provider: Provider = get_provider(provider_mode)
        except ProviderError as e:
            result.error = str(e)
            return result
        result.provider = provider.name

        if provider.name == "mock":
            result.answer = provider.synthesize(q, result.evidence,
                                                OUTPUT_INSTRUCTIONS)
            # En mock no hay síntesis: se declaran citas solo informativas
            result.citations = validate_citations(result.answer, result.evidence)
            return result

        # Aviso previo a proveedor externo lo emite la CLI antes de llamar;
        # aquí solo se envían los fragmentos seleccionados.
        try:
            result.answer = provider.synthesize(q, result.evidence,
                                                OUTPUT_INSTRUCTIONS)
        except ProviderError as e:
            result.error = str(e)
            return result

        # 7: verificar citas contra los IDs entregados
        result.citations = validate_citations(result.answer, result.evidence)
        if not result.citations.get("has_citations"):
            result.warnings.append("sin_citas")
        if result.citations.get("invalid"):
            result.warnings.append(
                "citas_invalidas:" + ",".join(result.citations["invalid"]))
        return result
    finally:
        if own_repo:
            repo.close()


def render_answer(result: QueryResult) -> str:
    """Formatea la respuesta con el formato de citas recomendado."""
    out = []
    mode = "mock (sin IA)" if result.provider == "mock" else result.provider
    out.append(f"Modo: {mode}")
    if result.error:
        out.append(f"Error: {result.error}")
        return "\n".join(out)
    out.append("")
    out.append(result.answer)
    if result.evidence:
        out.append("")
        out.append("Evidencia:")
        for e in result.evidence:
            cits = " / ".join(citation_for(r) for r in e["refs"])
            out.append(f"  [{e['id']}] {cits}")
            out.append(f"      {e['text'][:220]}")
    if result.warnings:
        out.append("")
        out.append("Avisos: " + "; ".join(result.warnings))
    return "\n".join(out)
