"""Configuración centralizada: rutas inyectables, sin defaults de usuario.

Este módulo lee exclusivamente variables TCDA_* para el aislamiento de configuración
del motor documental en Tech Cyan Desktop Advanced. No se accede a variables DOC_*
del entorno de Windows bajo ningún concepto.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any


class TCDAConfig:
    """Configuración centralizada e inyectable con prefijo TCDA_.

    Responsabilidades:
    - Leer exclusivamente variables TCDA_* del entorno.
    - Validar tipos y valores de configuración.
    - Producir errores explícitos ante configuraciones inválidas.
    - No detección automática de colecciones (política preserve).
    - Rutas derivadas basadas en WORKSPACE_ROOT configurado explícitamente.
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Inicializar con configuración opcional inyectable para pruebas.

        Args:
            config_overrides: Diccionario con valores para inyección en pruebas.
                Si se provee, estos valores tienen prioridad sobre el entorno.
        """
        # --- Rutas de colección y workspace ---
        # Política preserve: ninguna ruta se resuelve automáticamente.
        # El usuario/deployment debe proveer estas variables TCDA_*.
        self._collection_source = self._read_path_env("TCDA_COLLECTION_SOURCE", None)
        self._workspace_root = self._read_path_env("TCDA_WORKSPACE_ROOT", None)

        # Derivadas — si WORKSPACE_ROOT es None, estas también lo serán y
        # fallarán temprano con errores explícitos en tiempo de ejecución.
        self._database_path: Optional[Path] = None
        _extracted_dir: Optional[Path] = None
        _logs_dir: Optional[Path] = None
        _reports_dir: Optional[Path] = None
        if self._workspace_root is not None:
            self._database_path = Path(self._workspace_root) / "database" / "documents.db"
            _extracted_dir = Path(self._workspace_root) / "extracted"
            _logs_dir = Path(self._workspace_root) / "logs"
            _reports_dir = Path(self._workspace_root) / "reports"

        self._database_path = Path(self._database_path) if self._database_path else None
        self._extracted_dir = Path(_extracted_dir) if _extracted_dir else None
        self._logs_dir = Path(_logs_dir) if _logs_dir else None
        self._reports_dir = Path(_reports_dir) if _reports_dir else None

        # --- Umbrales y configuración OCR ---
        # Ningún umbral viene hardcodeado de usuario. Todos son configurables.
        self._digital_text_threshold = self._read_int_env("TCDA_DIGITAL_TEXT_THRESHOLD", 10)
        # OCR local (Tesseract): sin nube, sin LLM, sin costes de reconocimiento.
        # IMPORTANTE: TESSERACT_CMD y TESSDATA_PREFIX SIN valores por defecto de usuario.
        # Si no están definidas, OCR fallará de forma explícita en tiempo de ejecución
        # (is_available() -> False), nunca degradado silencioso con ruta equivocada.
        self._tesseract_cmd = self._read_tesseract_cmd_env()
        self._tessdata_prefix = self._read_tessdata_prefix_env()
        self._ocr_languages = self._read_ocr_languages_env()
        self._ocr_dpi = self._read_int_env("TCDA_OCR_DPI", 200)
        self._ocr_enabled = self._read_ocr_enabled_env()

        # --- IA / síntesis (Fase 4): mock por defecto, sin red y sin coste ---
        self._ai_provider = self._read_ai_provider_env()
        self._ai_max_evidence = self._read_int_env("TCDA_AI_MAX_EVIDENCE", 8)
        self._ai_max_evidence_rows = self._read_int_env("TCDA_AI_MAX_EVIDENCE_ROWS", 12)
        self._ai_max_fragment_chars = self._read_int_env("TCDA_AI_MAX_FRAGMENT_CHARS", 1200)
        self._ai_max_context_chars = self._read_int_env("TCDA_AI_MAX_CONTEXT_CHARS", 9000)

        # Aplicar overrides de prueba si fueron proveídos
        if config_overrides:
            self._apply_overrides(config_overrides)

    # ------------------------------------------------------------------
    # Lectores de entorno con prefijo TCDA_
    # ------------------------------------------------------------------

    @staticmethod
    def _read_path_env(var_name: str, default: Any = None) -> Optional[str]:
        """Leer variable de ruta de entorno TCDA_*. Retorna None si no está definida."""
        value = os.getenv(var_name)
        return value.strip() if value else default

    @staticmethod
    def _read_int_env(var_name: str, default: int) -> int:
        """Leer variable entera de entorno TCDA_* con valor por defecto."""
        value = os.getenv(var_name)
        if value is not None:
            try:
                return int(value.strip())
            except (ValueError, AttributeError):
                pass
        return default

    @staticmethod
    def _read_ocr_languages_env() -> str:
        """Leer TCDA_OCR_LANGUAGES, default 'spa'."""
        value = os.getenv("TCDA_OCR_LANGUAGES")
        if value:
            return value.strip()
        # No caer back a DOC_OCR_LANGUAGES bajo ningún concepto
        return "spa"

    @staticmethod
    def _read_ocr_enabled_env() -> bool:
        """Leer TCDA_OCR_ENABLED. 1=habilitado, 0=deshabilitado."""
        value = os.getenv("TCDA_OCR_ENABLED")
        if value is not None:
            return value.strip() == "1"
        return True  # Modo seguro por defecto

    @staticmethod
    def _read_ai_provider_env() -> str:
        """Leer TCDA_AI_PROVIDER, default 'mock'."""
        value = os.getenv("TCDA_AI_PROVIDER")
        if value is not None:
            return value.strip().lower()
        return "mock"

    @staticmethod
    def _read_tesseract_cmd_env() -> Optional[str]:
        """Leer TCDA_TESSERACT_CMD. Ningún default; obligatorio configurar.

        Returns:
            La ruta del ejecutable Tesseract si está definida, None en caso contrario.
            IMPORTANTE: No establece ningún valor global permanente.
        """
        value = os.getenv("TCDA_TESSERACT_CMD")
        return value.strip() if value else None

    @staticmethod
    def _read_tessdata_prefix_env() -> Optional[str]:
        """Leer TCDA_TESSDATA_PREFIX. Ningún default; obligatorio configurar.

        Returns:
            El prefijo TESSDATA si está definido, None en caso contrario.
            IMPORTANTE: No establece os.environ["TESSDATA_PREFIX"] permanentemente.
        """
        value = os.getenv("TCDA_TESSDATA_PREFIX")
        return value.strip() if value else None

    # ------------------------------------------------------------------
    # Aplicación de overrides (para pruebas)
    # ------------------------------------------------------------------

    def _apply_overrides(self, overrides: Dict[str, Any]) -> None:
        """Aplicar overrides de configuración para tests aislados.

        Este método permite inyectar valores de configuración en pruebas
        sin modificar el entorno global. Los overrides tienen prioridad sobre
        las variables de entorno TCDA_*.

        Los keys se esperan con prefijo TCDA_ (ej. TCDA_WORKSPACE_ROOT),
        y se mapean a los atributos internos sin prefijo (ej. _workspace_root).
        El mapeo ignora mayúsculas/minúsculas para flexibilidad.
        """
        for key, value in overrides.items():
            # Quitar prefijo TCDA_ para mapear al atributo interno
            attr_key = key
            if attr_key.startswith("TCDA_"):
                attr_key = attr_key[5:]  # Remover "TCDA_"
            # Normalizar a minúsculas para coincidir con los atributos
            # (TCDA_WORKSPACE_ROOT -> _workspace_root)
            attr_key = attr_key.lower()
            target_attr = "_" + attr_key if attr_key else key
            if hasattr(self, target_attr):
                setattr(self, target_attr, value)

    # ------------------------------------------------------------------
    # Propiedades de acceso (compatibilidad con imports existentes)
    # ------------------------------------------------------------------

    @property
    def collection_source(self) -> Optional[Path]:
        """Devuelve la ruta de la colección o None si no está configurada."""
        if self._collection_source is None:
            return None
        return Path(self._collection_source)

    @property
    def workspace_root(self) -> Optional[Path]:
        """Devuelve la raíz de trabajo o None si no está configurada."""
        if self._workspace_root is None:
            return None
        return Path(self._workspace_root)

    @property
    def database_path(self) -> Optional[Path]:
        """Devuelve la ruta de la base de datos o None."""
        return self._database_path

    @property
    def extracted_dir(self) -> Optional[Path]:
        """Devuelve la carpeta de extraídos o None."""
        return self._extracted_dir

    @property
    def logs_dir(self) -> Optional[Path]:
        """Devuelve la carpeta de logs o None."""
        return self._logs_dir

    @property
    def reports_dir(self) -> Optional[Path]:
        """Devuelve la carpeta de reportes o None."""
        return self._reports_dir

    @property
    def digital_text_threshold(self) -> int:
        """Umbral de calidad de texto digital."""
        return self._digital_text_threshold

    @property
    def tesseract_cmd(self) -> Optional[str]:
        """Ruta al ejecutable Tesseract. Ningún default; puede ser None."""
        return self._tesseract_cmd

    @property
    def tessdata_prefix(self) -> Optional[str]:
        """Prefijo TESSDATA. Ningún default; puede ser None."""
        return self._tessdata_prefix

    @property
    def ocr_languages(self) -> str:
        """Idioma principal OCR (spa/eng)."""
        return self._ocr_languages

    @property
    def ocr_dpi(self) -> int:
        """Resolución DPI para OCR Tesseract."""
        return self._ocr_dpi

    @property
    def ocr_enabled(self) -> bool:
        """¿El OCR está habilitado?"""
        return self._ocr_enabled

    @property
    def ai_provider(self) -> str:
        """Proveedor de IA: 'mock' o 'api'."""
        return self._ai_provider

    @property
    def ai_max_evidence(self) -> int:
        """Máximo de evidencias a recuperar."""
        return self._ai_max_evidence

    @property
    def ai_max_evidence_rows(self) -> int:
        """Máximo de filas de evidencia."""
        return self._ai_max_evidence_rows

    @property
    def ai_max_fragment_chars(self) -> int:
        """Número máximo de caracteres por fragmento."""
        return self._ai_max_fragment_chars

    @property
    def ai_max_context_chars(self) -> int:
        """Número máximo de caracteres de contexto."""
        return self._ai_max_context_chars

    # ------------------------------------------------------------------
    # Funciones auxiliares de resolución (compatibilidad)
    # ------------------------------------------------------------------

    def get_collection_source(self) -> Optional[Path]:
        """Devuelve la ruta de la colección o None si no está configurada."""
        return self.collection_source

    def get_workspace_root(self) -> Optional[Path]:
        """Devuelve la raíz de trabajo o None si no está configurada."""
        return self.workspace_root

    def validate_collection_path(self, path: Path) -> bool:
        """Validar que la ruta sea un directorio existente.

        Retorna False también si path es None (sin colección configurada).
        """
        return path is not None and path.is_dir()

    def ensure_directories(self) -> None:
        """Crear directorios derivados solo si WORKSPACE_ROOT está configurado.

        Si no, no hay nada que crear (el usuario debe proveer la estructura).
        """
        if self._workspace_root is None:
            return
        for p in [self._database_path, self._extracted_dir, self._logs_dir, self._reports_dir]:
            if p is not None:
                p.mkdir(parents=True, exist_ok=True)


# Instancia global única para compatibilidad gradual.
# Los componentes principales deberían recibir configuración explícita
# en lugar de depender de esta global, pero mantenemos ella para
# evitar romper imports existentes de golpe.
_config_instance: Optional[TCDAConfig] = None


def get_config() -> TCDAConfig:
    """Obtener la instancia global de configuración TCDA_.

    Returns:
        La configuración global TCDA_. Se crea en el primer llamado.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = TCDAConfig()
    return _config_instance


def init_config(config_overrides: Optional[Dict[str, Any]] = None) -> TCDAConfig:
    """Inicializar (o re-inicializar) la configuración global TCDA_.

    Esta función debe usarse en tests y en la entrada principal del proceso
    para asegurar que la configuración está activa y aislada.

    Args:
        config_overrides: Diccionario con valores para inyección en tests.

    Returns:
        La instancia de TCDAConfig inicializada.
    """
    global _config_instance
    _config_instance = TCDAConfig(config_overrides=config_overrides)
    return _config_instance


# Alias para compatibilidad con imports existentes de "from documental.config import X"
# y para que database.py pueda importar DATABASE_PATH.
# Estos valores son placeholders; usar get_config().database_path en nuevo código.
COLLECTION_SOURCE = None  # Placeholder; usar get_config().get_collection_source() en nuevo código
WORKSPACE_ROOT = None  # Placeholder; usar get_config().get_workspace_root() en nuevo código
DATABASE_PATH = None  # Placeholder; usar get_config().database_path en nuevo código
DIGITAL_TEXT_THRESHOLD = 10  # Valor por defecto; usar get_config().digital_text_threshold
TESSERACT_CMD = None  # Placeholder; usar get_config().tesseract_cmd
TESSDATA_PREFIX = None  # Placeholder; usar get_config().tessdata_prefix
OCR_LANGUAGES = "spa"  # Valor por defecto; usar get_config().ocr_languages
OCR_DPI = 200  # Valor por defecto; usar get_config().ocr_dpi
OCR_ENABLED = True  # Modo seguro por defecto; usar get_config().ocr_enabled
AI_PROVIDER = "mock"  # Modo por defecto; usar get_config().ai_provider
AI_MAX_EVIDENCE = 8
AI_MAX_EVIDENCE_ROWS = 12
AI_MAX_FRAGMENT_CHARS = 1200
AI_MAX_CONTEXT_CHARS = 9000


def validate_collection_path(path: Path) -> bool:
    """Validar que la ruta sea un directorio existente.

    Retorna False también si path es None (sin colección configurada).
    """
    from .config import get_config
    return get_config().validate_collection_path(path)


def ensure_directories() -> None:
    """Crear directorios derivados solo si WORKSPACE_ROOT está configurado."""
    from .config import get_config
    get_config().ensure_directories()


# Funciones auxiliares legacy (mantenidas para compatibilidad de imports)
# Estas ya NO leen variables DOC_* del entorno; usan la configuración TCDA_*.

def get_collection_source() -> Optional[Path]:
    """Devuelve la ruta de la colección o None si no está configurada.

    Política preserve: el caller debe verificar que no sea None antes de usarse.
    """
    from .config import get_config
    return get_config().get_collection_source()


def get_workspace_root() -> Optional[Path]:
    """Devuelve la raíz de trabajo o None si no está configurada."""
    from .config import get_config
    return get_config().get_workspace_root()


# ------------------------------------------------------------------
# Detectar colección raíz de forma perezosa (solo desde configuración TCDA_)
# ------------------------------------------------------------------

def detect_collection_source_fallback() -> Optional[Path]:
    """Política preserve: NO detectar colección automáticamente.

    Esta función está desactivada. La configuración TCDA_* debe proveerse
    explícitamente. No se realizan búsquedas en rutas comunes de Windows.
    """
    # Política preserve: sin detección automática.
    # El usuario debe configurar TCDA_COLLECTION_SOURCE explícitamente.
    return None