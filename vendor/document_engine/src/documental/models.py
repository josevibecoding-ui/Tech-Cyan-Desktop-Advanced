"""Modelos y DTOs compartidos: estructura de datos sin dependencias de I/O."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal


# --- OperationResult: resultado de cualquier operación del motor ---

@dataclass
class OperationResult:
    """Resultado estandarizado de una operación del motor documental.

    TODAS las funciones expuestas del adapter deben retornar este tipo,
    NUNCA print() ni sys.exit(). El caller (GUI o CLI) decide qué hacer
    con el resultado (mostrar diálogo, barra de estado, consola, etc.).
    """
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = field(default=None)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = field(default=None)

    @classmethod
    def success_result(cls, message: str, data: Optional[Dict[str, Any]] = None) -> OperationResult:
        """Factory para crear resultados de éxito."""
        return cls(success=True, message=message, data=data)

    @classmethod
    def error_result(cls, message: str, error: Optional[str] = None) -> OperationResult:
        """Factory para crear resultados con error."""
        return cls(success=False, message=message, error=error)


# --- JobState: estado de un job para UI thread-safe ---

@dataclass
class JobState:
    """Estado de un job en ejecución, para comunicación thread-safe entre worker y UI."""

    job_id: str
    status: Literal["pending", "running", "completed", "failed", "cancelled"] = "pending"
    progress: float = 0.0  # 0.0 - 1.0
    current_step: str = ""
    elapsed_seconds: float = 0.0
    estimated_total_seconds: Optional[float] = None
    error: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "status": self.status,
            "progress": self.progress,
            "current_step": self.current_step,
            "elapsed_seconds": self.elapsed_seconds,
            "estimated_total_seconds": self.estimated_total_seconds,
            "error": self.error,
            "extra": self.extra,
        }


# --- DTOs de dominio para el adapter ---

@dataclass
class EngineStatusDTO:
    """Estructura de retorno de get_engine_status."""
    documents_total: int
    pages_total: int
    pages_with_text: int
    fts_index_rows: int
    ocr_available: bool
    provider_mode: str
    collection_root: Optional[str] = None
    workspace_root: Optional[str] = None


@dataclass
class DocumentDTO:
    """Estructura de retorno de get_document."""
    document_id: str
    relative_path: str
    filename: str
    content_sha256: Optional[str] = None
    file_size: Optional[int] = None
    modified_at: Optional[str] = None
    page_count: int = 0
    status: str = "indexed"
    last_processed_at: Optional[str] = None


@dataclass
class UpdateReportDTO:
    """Estructura de retorno de update_collection."""
    nuevos: int = 0
    modificados: int = 0
    duplicados: int = 0
    sin_cambios: int = 0
    errores: int = 0
    no_encontrados: int = 0
    paginas: int = 0
    ocr: int = 0
    success: bool = True
    message: str = ""
    # Detalle por documento
    detalles: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class QueryResultDTO:
    """Estructura de retorno de ask_document_question / search_documents."""
    question: str
    answer: str
    provider: str
    evidence: List[Dict[str, Any]] = field(default_factory=list)
    citations: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def has_evidence(self) -> bool:
        return bool(self.evidence)


@dataclass
class OcrPageResultDTO:
    """Resultado de OCR de una página individual."""
    page_id: str
    document_id: str
    page_number: int
    text: str
    quality: bool  # True = ok, False = con problemas
    error: Optional[str] = None
    extraction_method: str = "ocr"


@dataclass
class ValidationReportDTO:
    """Estructura de retorno de validate_engine."""
    problems_total: int = 0
    ok: bool = True
    integrity_sqlite: str = "unknown"
    foreign_key_issues: int = 0
    fts_coherence: bool = False
    total_pages: int = 0
    pages_with_text: int = 0
    fts_rows: int = 0
    documents_without_hash: int = 0
    dup_hashes_count: int = 0
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    pending_ocr_pages: int = 0
    marked_documents: int = 0


# --- DTOs adicionales para adapter ---

@dataclass
class CleanupReportDTO:
    """Estructura de retorno de clean_derived_data."""
    items_removed: int = 0
    backup_available: bool = False
    restoration_possible: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class ReindexReportDTO:
    """Estructura de retorno de reindex_collection."""
    fts_reindexed: int = 0
    ocr_pages_processed: int = 0
    validation: ValidationReportDTO = field(default_factory=ValidationReportDTO)