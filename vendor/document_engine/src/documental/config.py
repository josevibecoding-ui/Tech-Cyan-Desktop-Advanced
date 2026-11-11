"""Configuración centralizada: rutas inyectables, sin defaults de usuario."""
import os
from pathlib import Path

# --- Rutas de colección y workspace ---
# Política preserve: ninguna ruta se resuelve automáticamente.
# El usuario/deployment debe proveer estas variables de entorno.
COLLECTION_SOURCE = (
    Path(os.getenv("DOC_COLLECTION_SOURCE")) if os.getenv("DOC_COLLECTION_SOURCE") else None
)
WORKSPACE_ROOT = (
    Path(os.getenv("DOC_WORKSPACE_ROOT")) if os.getenv("DOC_WORKSPACE_ROOT") else None
)

# Derivadas — si WORKSPACE_ROOT es None, estas también lo serán y
# fallarán temprano con errores explícitos en tiempo de ejecución.
DATABASE_PATH = WORKSPACE_ROOT / "database" / "documents.db" if WORKSPACE_ROOT else None
EXTRACTED_DIR = WORKSPACE_ROOT / "extracted" if WORKSPACE_ROOT else None
LOGS_DIR = WORKSPACE_ROOT / "logs" if WORKSPACE_ROOT else None
REPORTS_DIR = WORKSPACE_ROOT / "reports" if WORKSPACE_ROOT else None

# --- Umbrales y configuración OCR ---
# Ningún umbral viene hardcodeado de usuario. Todos son configurables.
DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))
# OCR local (Tesseract): sin nube, sin LLM, sin costes de reconocimiento.
# IMPORTANTE: TESSERACT_CMD y TESSDATA_PREFIX SIN valores por defecto de usuario.
# Si no están definidas, OCR fallará de forma explícita en tiempo de ejecución
# (is_available() -> False), nunca degradado silencioso con ruta equivocada.
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # Ningún default; obligatorio configurar
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX")  # Ningún default; obligatorio configurar
OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "spa")  # Idioma principal OCR (spa/eng). Configurable via DOC_OCR_LANGUAGES
OCR_DPI = int(os.getenv("OCR_DPI", "200"))  # Resolución DPI para OCR Tesseract (estándar 200dpi). Configurable via DOC_OCR_DPI
OCR_ENABLED = os.getenv("OCR_ENABLED", "1") == "1"  # 1=habilitado, 0=deshabilitado. Modo seguro por defecto. Configurable via DOC_OCR_ENABLED

# --- IA / síntesis (Fase 4): mock por defecto, sin red y sin coste ---
AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")  # mock | api. Modo mock (seguro por defecto). Cambiar a API requiere DOC_AI_PROVIDER=api
AI_MAX_EVIDENCE = int(os.getenv("DOC_AI_MAX_EVIDENCE", "8"))
AI_MAX_EVIDENCE_ROWS = int(os.getenv("DOC_AI_MAX_EVIDENCE_ROWS", "12"))
AI_MAX_FRAGMENT_CHARS = int(os.getenv("DOC_AI_MAX_FRAGMENT_CHARS", "1200"))
AI_MAX_CONTEXT_CHARS = int(os.getenv("DOC_AI_MAX_CONTEXT_CHARS", "9000"))

# Funciones auxiliares de resolución


def get_collection_source() -> Path | None:
    """Devuelve la ruta de la colección o None si no está configurada.
    Políticas preserve: el caller debe verificar que no sea None antes de usarse."""
    return COLLECTION_SOURCE


def get_workspace_root() -> Path | None:
    """Devuelve la raíz de trabajo o None si no está configurada."""
    return WORKSPACE_ROOT


def validate_collection_path(path: Path) -> bool:
    """Validar que la ruta sea un directorio existente.
    Retorna False también si path es None (sin colección configurada)."""
    return path is not None and path.is_dir()


def ensure_directories():
    """Crear directorios derivados solo si WORKSPACE_ROOT está configurado.
    Si no, no hay nada que crear (el usuario debe proveer la estructura)."""
    if WORKSPACE_ROOT is None:
        return
    for p in [DATABASE_PATH.parent, EXTRACTED_DIR, LOGS_DIR, REPORTS_DIR]:
        p.mkdir(parents=True, exist_ok=True)


def detect_collection_source_fallback() -> Path | None:
    """Intentar detectar colección en rutas comunes de Windows SOLO si no está DOC_COLLECTION_SOURCE.
    Esto es una ayuda, no un default automático. Política preserve: el usuario debe
    configurar explícitamente DOC_COLLECTION_SOURCE."""
    import os as _os
    fallback_paths = [
        Path(_os.getenv("USERPROFILE", "")) / "Documentos",
        Path(_os.getenv("APPDATA", "")) / "TechCyan",
    ]
    for p in fallback_paths:
        if p is not None and p.is_dir():
            return p
    return None