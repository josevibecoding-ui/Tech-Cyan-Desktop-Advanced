import sys, os, traceback
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.config import get_collection_source, get_workspace_root, validate_collection_path
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile

print("=== Test 1: get_collection_source y get_workspace_root ===")
cs = get_collection_source()
wr = get_workspace_root()
print(f"get_collection_source() = {cs}")
print(f"get_workspace_root() = {wr}")

print("\n=== Test 2: validate_collection_path ===")
print(f"validate_collection_path(None) = {validate_collection_path(None)}")
try:
    result = validate_collection_path(Path(r"C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced"))
    print(f"validate_collection_path(Tech-Cyan) = {result}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Test 3: Repository creation ===")
try:
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        # Pequeño delay para evitar archivo bloqueado
        import time
        time.sleep(0.1)
        repo = Repository(db_path=str(db_path))
        print("✓ Repository creado")
        docs = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        print(f"  Documentos: {docs}")
        repo.close()
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()