import sys, os
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.config import get_collection_source, get_workspace_root, validate_collection_path
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile

print("=== Test 1: Repository sin colección configurada ===")
with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / "test.db"
    try:
        repo = Repository(db_path=str(db_path))
        print("✓ Repository creado exitosamente")
        docs = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        print(f"  Documentos: {docs}")
        repo.close()
    except Exception as e:
        print(f"✗ Error creando repositorio: {e}")

print("\n=== Test 2: validate_collection_path con None ===")
print(f"validate_collection_path(None) = {validate_collection_path(None)}")

print("\n=== Test 3: get_collection_source y get_workspace_root ===")
print(f"get_collection_source() = {get_collection_source()}")
print(f"get_workspace_root() = {get_workspace_root()}")

print("\n=== Test 4: ensure_directories sin WORKSPACE_ROOT ===")
ensure_directories()
print("  ensure_directories() completado (debería ser no-op cuando WORKSPACE_ROOT es None)")