import sys, os, traceback
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.cli import cmd_scan, cmd_status
from document_engine.src.documental.config import get_collection_source, get_workspace_root, ensure_directories
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile

print("=== Test: cmd_status sin colección configurada ===")
result = cmd_scan(type('Args', (), {'source': None})())
print("cmd_scan resultado:", result)
print("  success:", result.success if result else "N/A")
print("  message:", result.message if result and hasattr(result, 'message') else "N/A")

print("\n=== Test: Repository con meta collection_root vacía ===")
with tempfile.TemporaryDirectory() as tmpdir:
    db_path = Path(tmpdir) / "test.db"
    repo = Repository(db_path=str(db_path))
    # Simular que no hay colección en meta
    repo.set_meta("collection_root", None)
    source = repo.get_meta("collection_root") or get_collection_source()
    print("Fuente desde meta o env:", source)
    # Validar
    sp = Path(source) if source else None
    print("Path source:", sp)
    if sp:
        print("Validando ruta...")
        valid = validate_collection_path(sp)
        print("Valid:", valid)
    repo.close()