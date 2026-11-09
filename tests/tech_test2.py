import sys
import tempfile
from pathlib import Path
sys.path.insert(0, r'C:\workspace\Tech-Cyan-Desktop-Advanced-documentacion-base\Tech-Cyan-Desktop-Advanced\vendor')
from document_engine.src.documental.database import Repository
from document_engine.src.documental.config import get_collection_source, get_workspace_root, ensure_directories

print(f"Collection source: {get_collection_source()}")
print(f"Workspace root: {get_workspace_root()}")

with tempfile.TemporaryDirectory() as tmp:
    db_path = Path(tmp) / 'test.db'
    print(f"\nIntentando abrir BD en: {db_path}")
    repo = Repository(db_path=str(db_path))
    print('DB abierta exitosamente')
    docs = repo.conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
    pages = repo.conn.execute('SELECT COUNT(*) FROM pages').fetchone()[0]
    print(f'Documentos: {docs}, Páginas: {pages}')
    
    # Test scan collection
    from document_engine.src.documental.cli import cmd_scan
    from unittest.mock import Mock
    
    # Test basic operations
    abs_path = str(Path(tmp) / 'sample.pdf')
    from document_engine.src.documental.extractor import extract_pdf_digital
    # Create a simple PDF
    import fitz as pymupdf
    pdf_path = Path(tmp) / "sample.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 70), "Texto de prueba para test")
    doc.save(str(pdf_path))
    doc.close()
    
    results = extract_pdf_digital(pdf_path)
    print(f"Resultados extracción: {len(results)} páginas")
    for r in results:
        print(f"  Página {r['page_number']}: quality={r['quality_status']}, text_len={len(r['text'])}, method={r['extraction_method']}")
    
    repo.close()
    
print("\nTest completado sin errores críticos")