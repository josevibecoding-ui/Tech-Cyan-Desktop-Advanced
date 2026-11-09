"""Scanner: inventario recursivo."""
import os
from pathlib import Path
from typing import List, Dict
PDF_EXTENSION = ".pdf"
def is_pdf_file(filename: str) -> bool:
    return filename.lower().endswith(PDF_EXTENSION)
def scan_collection(source_path: Path) -> List[Dict]:
    results = []
    for root, dirs, files in os.walk(source_path):
        for filename in sorted(files):
            filepath = Path(root) / filename
            if is_pdf_file(filename):
                rel = filepath.relative_to(source_path)
                results.append({"document_id": str(rel).replace(os.sep, "/"),
                                "relative_path": str(rel),
                                "filepath": str(filepath.resolve()),
                                "filename": filename})
    return results