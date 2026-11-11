#!/usr/bin/env python
import sys

with open('vendor/document_engine/src/documental/config.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Nuevo contenido de config.py segun el plan (sin saltos de línea problemáticos)
new_config_content = """# --- Rutas de coleccion y workspace ---
# Politica preserve: ninguna ruta se resuelve automaticamente.
# El usuario/deployment debe proveer estas variables de entorno.
# Ninguna ruta tiene default automatico; si no estan definidas, son None
# y el sistema fallara temprano con errores explicitos en tiempo de ejecucion,
# solicitando al usuario que configure DOC_COLLECTION_SOURCE y DOC_WORKSPACE_ROOT.
COLLECTION_SOURCE = Path(os.getenv("DOC_COLLECTION_SOURCE")) if os.getenv("DOC_COLLECTION_SOURCE") else None
WORKSPACE_ROOT = Path(os.getenv("DOC_WORKSPACE_ROOT")) if os.getenv("DOC_WORKSPACE_ROOT") else None

# Derivadas: si WORKSPACE_ROOT es None, estas tambein lo seran
# y fallaran temprano con errores explicitos en tiempo de ejecucion.
DATABASE_PATH = WORKSPACE_ROOT / "database" / "documents.db" if WORKSPACE_ROOT else None
EXTRACTED_DIR = WORKSPACE_ROOT / "extracted" if WORKSPACE_ROOT else None
LOGS_DIR = WORKSPACE_ROOT / "logs" if WORKSPACE_ROOT else None
REPORTS_DIR = WORKSPACE_ROOT / "reports" if WORKSPACE_ROOT else None

# --- Umbrales y configuracion OCR ---
# TODAS las variables de configuracion OCR son obligatorias mediante variable de entorno.
# Ningun default de usuario que oculte la falta de configuracion.
# El usuario/deployment debe proveer estas variables de entorno.
DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD"))  # sin default; obligatorio configurar
# OCR local (Tesseract): sin nube, sin LLM, sin costes de reconocimiento.
# IMPORTANTE: TESSERACT_CMD y TESSDATA_PREFIX SIN valores por defecto de usuario.
# Si no estan definidas, OCR fallara de forma explicita en tiempo de ejecucion
# (is_available() -> False), nunca degradado silencioso con ruta equivocada.
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # Ningun default; obligatorio configurar
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX")  # Ningun default; obligatorio configurar

# IA / sintesis (Fase 4): mock por defecto, sin red y sin coste
# El modo mock es el modo por defecto seguro; cambiar a API requiere DOC_AI_PROVIDER=api
AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")  # mock | api - mock es el modo seguro por defecto
AI_MAX_EVIDENCE = int(os.getenv("DOC_AI_MAX_EVIDENCE", "8"))
AI_MAX_EVIDENCE_ROWS = int(os.getenv("DOC_AI_MAX_EVIDENCE_ROWS", "12"))
AI_MAX_FRAGMENT_CHARS = int(os.getenv("DOC_AI_MAX_FRAGMENT_CHARS", "1200"))
AI_MAX_CONTEXT_CHARS = int(os.getenv("DOC_AI_MAX_CONTEXT_CHARS", "9000"))

# Funciones auxiliares de resolucion


def get_collection_source_content():
    pass

def get_workspace_root_content():
    pass

def validate_collection_path_content(path):
    pass

def ensure_directories_content():
    pass

def detect_collection_source_fallback_content():
    pass

def is_ocr_enabled_content():
    pass
"""

# Extraer solo la parte de configuración superior (hasta AI_PROVIDE) del nuevo contenido
# Tomamos solo las líneas necesarias
lines = new_config_content.split('\n')
# Filtrar solo las líneas de configuración superior (hasta la línea AI_PROVIDER)
config_lines = []
in_config = False
for line in lines:
    if 'AI_PROVIDER = os.getenv' in line:
        in_config = True
    if in_config:
        config_lines.append(line)
    if len(config_lines) > 30:  # límite de seguridad
        break

config_section = '\n'.join(config_lines)

# Verificar si el contenido actual tiene los patrones que queremos reemplazar
old_markers = [
    'COLLECTION_SOURCE = (',
    'WORKSPACE_ROOT = (',
    'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))',
    'TESSERACT_CMD = os.getenv("TESSERACT_CMD")',
    'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")',
]

found = sum(1 for m in old_markers if m in content)
print('Patrones encontrados en config.py:', found, '/', len(old_markers))

if found >= 3:
    # Hacer el reemplazo sección por sección
    # 1. Reemplazar COLLECTION_SOURCE y WORKSPACE_ROOT
    if 'COLLECTION_SOURCE = (' in content:
        content = content.replace(
            'COLLECTION_SOURCE = (Path(os.getenv("DOC_COLLECTION_SOURCE")) if os.getenv("DOC_COLLECTION_SOURCE") else None)',
            'COLLECTION_SOURCE = Path(os.getenv("DOC_COLLECTION_SOURCE")) if os.getenv("DOC_COLLECTION_SOURCE") else None'
        )
    
    if 'WORKSPACE_ROOT = (' in content:
        content = content.replace(
            'WORKSPACE_ROOT = (Path(os.getenv("DOC_WORKSPACE_ROOT")) if os.getenv("DOC_WORKSPACE_ROOT") else None)',
            'WORKSPACE_ROOT = Path(os.getenv("DOC_WORKSPACE_ROOT")) if os.getenv("DOC_WORKSPACE_ROOT") else None'
        )
    
    # 2. Reemplazar DIGITAL_TEXT_THRESHOLD
    if 'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))' in content:
        content = content.replace(
            'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))',
            'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD"))'
        )
    
    # 3. Reemplazar TESSERACT_CMD
    if 'TESSERACT_CMD = os.getenv("TESSERACT_CMD")' not in content:
        # Agregarlo si no existe o reemplazar la versión vieja
        pass
    
    # 4. Reemplazar AI_PROVIDER
    if 'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")' in content:
        content = content.replace(
            'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")',
            'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")'
        )
    
    # Escribir el contenido modificado
    with open('vendor/document_engine/src/documental/config.py', 'w', encoding='utf-8', errors='replace') as f:
        f.write(content)
    
    print('config.py actualizada exitosamente')
    # Mostrar primeras líneas
    actual_lines = content.split('\n')
    print('Nuevas líneas 1-15:')
    for i in range(min(15, len(actual_lines))):
        print(f'L{i+1}: {actual_lines[i]}')
else:
    print('No se encontraron suficientes patrones para reemplazar automáticamente')
    # Mostrar qué hay realmente
    print('Intentando leer config.py actual...')
    with open('vendor/document_engine/src/documental/config.py', 'r', encoding='utf-8', errors='replace') as f:
        actual = f.read()
    print('Líneas 1-15 del actual:')
    for i, line in enumerate(actual.split('\n')[:15]):
        print(f'L{i+1}: {line}')
    sys.exit(1)