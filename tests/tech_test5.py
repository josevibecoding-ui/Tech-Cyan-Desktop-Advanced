import sys, os, traceback
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.config import get_collection_source, get_workspace_root, validate_collection_path
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile

print("=== Test 1: get_collection_source y get_workspace_root ===")
cs = get_collection_source()
wr = get_workspace_root()
print("get_collection_source() =", cs)
print("get_workspace_root() =", wr)

print("\n=== Test 2: validate_collection_path ===")
print("validate_collection_path(None) =", validate_collection_path(None))
result = validate_collection_path(Path(r"C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced"))
print("validate_collection_path(Tech-Cyan) =", result)

print("\n=== Test 3: Repository creation ===")
try:
    tmpdir = tempfile.mkdtemp()
    db_path = Path(tmpdir) / "test.db"
    repo = Repository(db_path=str(db_path))
    print("Repository creado OK")
    docs = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    print("Documentos:", docs)
    repo.close()
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
except Exception as e:
    print("Error:", e)
    traceback.print_exc()