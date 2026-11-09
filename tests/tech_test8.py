import sys, os, traceback
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile
import shutil

print("=== Test: Repository con directorio inexistente ===")
try:
    tmpdir = tempfile.mkdtemp()
    # Usar una ruta de BD en un subdirectorio anidado que no existe
    fake_db_path = str(Path(tmpdir) / "subdir" / "nested" / "documents.db")
    print("Ruta BD:", fake_db_path)
    print("Directorio padre existe antes:", Path(fake_db_path).parent.exists())
    
    repo = Repository(db_path=fake_db_path)
    print("Repository creado OK")
    
    docs = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    pages = repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    print("Documentos:", docs, "Páginas:", pages)
    
    # Verificar que el directorio fue creado
    parent_exists = Path(fake_db_path).parent.exists()
    print("Directorio padre existe después:", parent_exists)
    
    repo.close()
    
    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("Limpieza completada")
    print("TEST PASSED")
except Exception as e:
    print("ERROR:", e)
    traceback.print_exc()