import sys
import tempfile
from pathlib import Path
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.database import Repository

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / 'test.db'
    print(f"Intentando abrir BD en: {db_path}")
    repo = Repository(db_path=str(db_path))
    print('DB abierta exitosamente')
    docs = repo.conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    pages = repo.conn.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
    print(f'Documentos: {docs}, Páginas: {pages}')
    repo.close()