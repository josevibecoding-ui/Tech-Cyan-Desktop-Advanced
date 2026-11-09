"""Repository simplificado para Fase 1."""
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from .config import DATABASE_PATH, ensure_directories
logger = logging.getLogger(__name__)
class Repository:
    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self.conn = None
        self._open()
    def _open(self):
        try:
            # Asegurar que el directorio padre exista (AGENTS.md: corregir creación de directorios)
            db_dir = Path(str(self.db_path)).parent
            db_dir.mkdir(parents=True, exist_ok=True)
            self.conn = sqlite3.connect(str(self.db_path))
            # --- E1: Foreign keys activadas para integridad referencial ---
            self.conn.execute("PRAGMA foreign_keys=ON")
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.conn.execute("PRAGMA synchronous=NORMAL")
            self._create_tables()
            logger.info(f"DB abierta: {self.db_path}")
        except Exception as e:
            logger.error(f"Error DB: {e}")
            raise
    def _create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                relative_path TEXT UNIQUE,
                filename TEXT,
                content_sha256 TEXT,
                file_size INTEGER,
                modified_at TEXT,
                page_count INTEGER,
                status TEXT DEFAULT 'indexed',
                last_processed_at TEXT
            );
            CREATE TABLE IF NOT EXISTS pages (
                page_id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                text TEXT,
                extraction_method TEXT,
                quality_status TEXT,
                error_message TEXT,
                ocr_engine TEXT,
                ocr_language TEXT,
                ocr_version TEXT,
                UNIQUE(document_id, page_number)
            );
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS artifacts (
                artifact_key TEXT PRIMARY KEY, content_sha256 TEXT,
                extraction_version TEXT, artifact_path TEXT,
                validation_status TEXT DEFAULT 'valid');
            CREATE TABLE IF NOT EXISTS processing_runs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT DEFAULT (datetime('now')),
                finished_at TEXT, run_type TEXT NOT NULL,
                files_processed INTEGER DEFAULT 0,
                pages_extracted INTEGER DEFAULT 0,
                pages_ocr INTEGER DEFAULT 0,
                pages_failed INTEGER DEFAULT 0, error_summary TEXT);
        """)
        # Migración ligera: columnas OCR en pages (si faltan en BD existente)
        try:
            cols = [r[1] for r in self.conn.execute("PRAGMA table_info(pages)")]
            for col in ("ocr_engine", "ocr_language", "ocr_version"):
                if col not in cols:
                    self.conn.execute(f"ALTER TABLE pages ADD COLUMN {col} TEXT")
        except Exception as e:
            logger.warning(f"Error migrando columnas OCR: {e}")
        # Crear índice FTS5 (tabla independiente, sin content=)
        # Solo crear si no existe; no borrar datos existentes
        try:
            self.conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS pages_fts USING fts5(
                    text,
                    document_id,
                    page_number,
                    tokenize='unicode61 remove_diacritics 2'
                )
            """)
        except Exception as e:
            logger.warning(f"Error creando FTS5: {e}")
        self.conn.commit()
    def document_exists(self, document_id): 
        cur = self.conn.execute("SELECT 1 FROM documents WHERE document_id=?", (document_id,))
        return cur.fetchone() is not None
    def insert_document(self, document_id, relative_path, filename, content_sha256, file_size, modified_at, page_count):
        self.conn.execute("""INSERT OR REPLACE INTO documents 
            (document_id, relative_path, filename, content_sha256, file_size, modified_at, page_count, status, last_processed_at)
            VALUES (?,?,?,?,?,?,?, 'indexed', datetime('now'))""",
            (document_id, relative_path, filename, content_sha256, file_size, modified_at, page_count))
    def update_document_status(self, document_id, status):
        self.conn.execute("UPDATE documents SET status=?, last_processed_at=datetime('now') WHERE document_id=?", (status, document_id))
    def get_document(self, document_id):
        cur = self.conn.execute("SELECT * FROM documents WHERE document_id=?", (document_id,))
        row = cur.fetchone()
        if row is None: return None
        cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))
    def insert_page(self, page_id, document_id, page_number, text, extraction_method, quality_status, error_message,
                    ocr_engine=None, ocr_language=None, ocr_version=None):
        self.conn.execute("""INSERT OR REPLACE INTO pages 
            (page_id, document_id, page_number, text, extraction_method, quality_status, error_message,
             ocr_engine, ocr_language, ocr_version)
            VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (page_id, document_id, page_number, text, extraction_method, quality_status, error_message,
             ocr_engine, ocr_language, ocr_version))
        # Sincronizar FTS5 (tabla independiente)
        if text and len(text.strip()) > 0:
            try:
                self.conn.execute(
                    "INSERT INTO pages_fts(text, document_id, page_number) VALUES (?,?,?)",
                    (text, document_id, page_number)
                )
            except Exception as e:
                logger.warning(f"Error sincronizando FTS5: {e}")
    def delete_document_pages(self, document_id):
        """Elimina las páginas de un documento (y su entrada FTS) antes de reextraer.

        No borra el registro de documento: solo su texto derivado.
        """
        try:
            self.conn.execute(
                "DELETE FROM pages_fts WHERE document_id=?", (document_id,))
            self.conn.execute(
                "DELETE FROM pages WHERE document_id=?", (document_id,))
        except Exception as e:
            logger.error(f"Error limpiando páginas de {document_id}: {e}")
            raise

    def get_pages_by_document(self, document_id):
        cur = self.conn.execute("SELECT * FROM pages WHERE document_id=? ORDER BY page_number", (document_id,))
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_pending_ocr_pages(self, limit=None):
        """Páginas sin texto digital útil, pendientes de OCR."""
        sql = """SELECT p.page_id, p.document_id, p.page_number, p.quality_status,
                        d.relative_path
                 FROM pages p
                 JOIN documents d ON d.document_id = p.document_id
                 WHERE p.quality_status IN ('empty','ocr_required')
                    OR (p.quality_status = 'suspicious'
                        AND (p.extraction_method IS NULL OR p.extraction_method != 'ocr'))
                 ORDER BY d.relative_path, p.page_number"""
        if limit:
            sql += f" LIMIT {int(limit)}"
        cur = self.conn.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def update_page_ocr(self, page_id, text, extraction_method, quality_status,
                        error_message=None, ocr_engine=None, ocr_language=None, ocr_version=None):
        """Actualiza una página con el resultado del OCR y sincroniza FTS5."""
        self.conn.execute("""UPDATE pages
            SET text=?, extraction_method=?, quality_status=?, error_message=?,
                ocr_engine=?, ocr_language=?, ocr_version=?
            WHERE page_id=?""",
            (text, extraction_method, quality_status, error_message,
             ocr_engine, ocr_language, ocr_version, page_id))
        # Sincronizar FTS5: eliminar entrada previa e insertar la nueva
        try:
            row = self.conn.execute(
                "SELECT document_id, page_number FROM pages WHERE page_id=?",
                (page_id,)).fetchone()
            if row:
                self.conn.execute(
                    "DELETE FROM pages_fts WHERE document_id=? AND page_number=?",
                    (row[0], row[1]))
                if text and text.strip():
                    self.conn.execute(
                        "INSERT INTO pages_fts(text, document_id, page_number) VALUES (?,?,?)",
                        (text, row[0], row[1]))
        except Exception as e:
            logger.warning(f"Error sincronizando FTS5 en OCR: {e}")

    def set_meta(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?,?)", (key, value))

    def get_meta(self, key):
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else None
    def search_fts(self, query, limit=50):
        """Búsqueda full-text usando FTS5."""
        try:
            # FTS5 MATCH: soporta comillas, operadores AND/OR, prefijos con *
            if ' ' in query and not query.startswith('"'):
                fts_query = f'"{query}"'
            else:
                fts_query = query
            
            sql = """
                SELECT document_id, page_number, text
                FROM pages_fts
                WHERE pages_fts MATCH ?
                LIMIT ?
            """
            cur = self.conn.execute(sql, (fts_query, limit))
            cols = [d[0] for d in cur.description]
            results = []
            for row in cur.fetchall():
                d = dict(zip(cols, row))
                # Obtener metadatos adicionales de pages
                meta = self.conn.execute(
                    "SELECT extraction_method, quality_status FROM pages WHERE document_id=? AND page_number=?",
                    (d['document_id'], d['page_number'])
                ).fetchone()
                if meta:
                    d['extraction_method'] = meta[0]
                    d['quality_status'] = meta[1]
                results.append(d)
            return results
        except Exception as e:
            logger.warning(f"Error FTS5, usando LIKE: {e}")
            pattern = f"%{query}%"
            cur = self.conn.execute(
                "SELECT document_id, page_number, text, extraction_method, quality_status FROM pages WHERE text LIKE ? LIMIT ?",
                (pattern, limit)
            )
            cols = [d[0] for d in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]
    def log_processing_run(self, run_type, files_processed, pages_extracted, pages_ocr=0, pages_failed=0, error_summary=None):
        run_id = str(self.conn.execute("""INSERT INTO processing_runs (run_type, files_processed, pages_extracted, pages_ocr, pages_failed, error_summary) 
            VALUES (?,?,?,?,?,?)""", (run_type, files_processed, pages_extracted, pages_ocr, pages_failed, error_summary)).lastrowid)
        self.conn.commit()
        logger.info(f"Lote: run_id={run_type}, files={files_processed}, pages={pages_extracted}")
        return run_id
    def commit(self):
        if self.conn: self.conn.commit()

    def rebuild_fts_index(self):
        """Reconstruir índice FTS5 desde datos existentes en pages."""
        try:
            # Limpiar índice actual
            self.conn.execute("DELETE FROM pages_fts")
            # Insertar todas las páginas con texto útil
            self.conn.execute("""
                INSERT INTO pages_fts(text, document_id, page_number)
                SELECT text, document_id, page_number 
                FROM pages 
                WHERE text IS NOT NULL AND LENGTH(text) > 0
            """)
            self.conn.commit()
            count = self.conn.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
            logger.info(f"Índice FTS5 reconstruido: {count} documentos")
            return count
        except Exception as e:
            logger.error(f"Error reconstruyendo FTS5: {e}")
            return 0

    def close(self):
        if self.conn: self.conn.close()