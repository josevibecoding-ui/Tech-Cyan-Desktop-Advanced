import sys, os, traceback
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.database import Repository
from pathlib import Path
import tempfile

print("=== Test: Repository con directorio inexistente (ahora debería crearse) ===")
# Usar una ruta de BD en un directorio que no existe temporalmente
try:
    tmpdir = tempfile.mkdtemp()
    # Crear una ruta de BD en un subdirectorio que no existe aún
    fake_db_path = Path(tmpdir) / "subdir" / "nested" / "documents.db"
    print(f"Intentando crear BD en: {fake_db_path}")
    print(f"Directorio padre existe antes: {fake_db_path.parent.exists()}")
    
    repo = Repository(db_path=str(fake_db_path))
    print("✓ Repository creado exitosamente")
    
    docs = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    pages = repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
    print(f"  Documentos: {docs}, Páginas: {pages}")
    
    # Verificar que el directorio fue creado
    print(f"Directorio padre existe después: {fake_db_path.parent.exists()}")
    
    repo.close()
    
    # Cleanup
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)
    print("✓ Limpieza completada")
except Exception as e:
    print(f"✗ Error: {e}")
    traceback.print_exc()