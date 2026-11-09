# brechas-de-integracion-engine

## Diferencias entre el motor documental actual y la arquitectura objetivo de Tech Cyan

**Fecha:** 8 de noviembre de 2026  
**Alcance:** Comparación de funcionalidades, arquitectura y contratos entre `vendor/document_engine/` (agente-documental 0.1.0) y el contrato `DocumentEngineAdapter` propuesto para Tech Cyan Desktop Advanced.  
**Metodología:** Auditoría estática, sin ejecución, sin modificación de archivos del motor original.

---

### 1. Mapeo de contrapartes: Motor actual ↔ DocumentEngineAdapter

| Contrato Tech Cyan | Motor actual | Brecha | Prioridad |
|---|---|---|---|
| `get_engine_status` | ❌ No existe | No hay función que retorne estado estructurado del motor. El `cli.cmd_status()` solo imprime conteo y usa `print()`/`sys.exit()`. | CRÍTICA |
| `scan_collection` | ✅ Parcial | `scanner.scan_collection(source_path)` existe y retorna `List[Dict]` con document_id, relative_path, filepath, filename. Brecha: ruta de colección hardcodeada en `config.py:4` (`COLLECTION_SOURCE = Path(r"D:/aliat/...")`) y `repo.get_meta("collection_root")`. Requiere wrapper que acepte ruta configurable. | ALTA |
| `update_collection` | ⚠️ Con riesgo crítico | Motor tiene `cmd_update` que procesa nuevos/modificados por fingerprint SHA-256 (agentes.md §7). Brechas: (1) **R1**: elimina páginas antiguas antes de reextraer sin staging transaccional; (2) rutas hardcodeadas; (3) `sys.exit()` en CLI; (4) sin progreso/cancelación estructurada. Requiere reescritura antes de exponer como adaptador. | CRÍTICA |
| `search_documents` | ✅ Disponible | `query.search_evidence(repo, question, limit)` + `repository.search_fts()` existen. Retornan filas con `document_id`, `page_number`, `text`, `extraction_method`, `quality_status`. Brecha: normalizar formato de retorno a DTO estructurado (no `print()`). | MEDIA |
| `get_document` | ✅ Disponible | `repository.get_document(document_id)` retorna `Dict` con campos `document_id`, `relative_path`, `filename`, `content_sha256`, `file_size`, `modified_at`, `page_count`, `status`, `last_processed_at`. Formato compatible con contrato. | BAJA |
| `rebuild_search_index` | ✅ Idéntico | `repo.rebuild_fts_index()` existe con misma funcionalidad: limpiar índice FTS5 e insertar desde tabla `pages` donde `text IS NOT NULL AND LENGTH(text) > 0`. Nombre y comportamiento coinciden exactamente. | NINGUNA |
| `process_pending_ocr` | ✅ Estructura, adaptación requerida | Flujo: `repo.get_pending_ocr_pages(limit)` → `ocr.ocr_pdf_page(fp, page_number)` → `repo.update_page_ocr(page_id, text, method, status, error, ocr_engine, language, version)`. Brecha: no hay wrapper único que acepte parámetros configurables (dpi, source) y reporte progreso. | ALTA |
| `ask_document_question` | ✅ Flujo, adaptación de interfaz | `run_query(question, provider_mode, evidence_limit, evidence_items, repo)` existe con flujo completo. Brecha: adapter debe exponer `question: str` → `QueryResult` y manejar modo mock/api, avisos de envío a proveedor externo y validación de citas. | ALTA |
| `validate_engine` | ✅ Disponible | `cmd_validate` existe y realiza: integridad SQLite, coherencia FTS5, huellas SHA-256, calidad de páginas, documentos marcados, documentos no en disco. Retorna reporte de problemas. Brecha: usa `print()`/`sys.exit()`, necesita wrapper DTO. | MEDIA |
| `remove_document_index` | ⚠️ Funcionalidad distinta | Motor tiene `repo.delete_document_pages(document_id)` que elimina filas de `pages` + `pages_fts` para un documento. El contrato propone `remove_document_index` como método nuevo. Funcionalidad superpuesta pero nombre diferente. Requiere wrapper que expare DTO y gestione staging. | MEDIA |
| `clean_derived_data` | ❌ No existe | No hay función en el motor actual que limpie datos derivados (cache, extracted, reports) de manera segura con backup-confirmar-restaurar. Requiere implementación nueva. | ALTA |
| `reindex_collection` | ❌ No existe | No hay comando público de reindexación completa. `rebuild_fts_index()` reconstruye FTS5 desde datos existentes pero no re-OCR'd ni re-extrae. Requiere implementación nueva que combine rebuild + OCR pendiente. | ALTA |

---

### 2. Brechas de Arquitectura

#### 2.1 Patrón de adaptación: CLI ↔ Adaptador Python

| Característica | Motor actual | Arquitectura Tech Cyan | Brecha | Esfuerzo |
|---|---|---|---|---|
| Punto de entrada | `cli.main()` con `argparse` | Servicios estructurados, sin `print()`/`sys.exit()` | Requerir reescritura de todas las funciones CLI para que retornen DTO en lugar de imprimir. | ALTO |
| Salida de información | `print()` en stdout | Cola thread-safe → actualización de widgets en hilo UI principal | Todas las funciones de motor usan `print()` — deben transformarse a retornos de valor. | ALTO |
| Manejo de errores | `sys.exit(1)` / `sys.exit(2)` / excepciones | Excepciones tipadas, progreso y cancelación cooperativa | `sys.exit()` en 8 funciones CLI impide uso desde GUI sin wrapping completo. | ALTO |
| Progreso y cancelación | No estructurado | Jobs con ID, tipo, estado, tiempos, progreso, contadores, errores, cancelación en puntos seguros | Requerir nuevo sistema de jobs/cola thread-safe. | ALTO |
| Rutas de colección | Hardcodeadas en `config.py` | Configuración por entorno, validación, rutas relativas | `COLLECTION_SOURCE = Path(r"D:/aliat/...")` y `WORKSPACE_ROOT` usuario-specific deben reescribirse. | ALTO |
| Base de datos | `Repository()` abre DB por instancia | Conexión SQLite por hilo, migraciones versionadas, `busy_timeout` | Repository actual no usa `threading.local` para conexiones ni migraciones versionadas. | MEDIO |
| Proveedores IA | `MockProvider` / `APIProvider` con env vars | `Provider`, `ProviderRegistry`, `ProviderManager`, `CredentialStore`, `FallbackPolicy`, `ResponseNormalizer` | Interfaces adicionales requeridos (Registry, Manager, CredentialStore, FallbackPolicy, ResponseNormalizer). | ALTO |
| PDF originales | Solo lectura en CLI | PDF originales solo lectura, nunca alterar — política `preserve` | Motor usa `pymupdf.open()` + `pypdf.PdfReader()` sobre rutas — compatibilidad con política `preserve` requiere validación. | BAJA |
| Tickets/citas | Formato `filename | rel | pág. X` | Contrato distinguir: ID de cita válido, referencia real, soporte semántico | Motor valida citas FTS5 (`validate_citations`) pero no demuestra respaldo semántico (según AGENTS.md §32). | MEDIO |
| Trabajo pesado fuera hilo principal | No aplicable (CLI) | Workers fuera del hilo UI; comunicación por cola thread-safe; widgets solo desde hilo Tk | Requerir arquitectura de jobs workers para integración GUI. | ALTO |

#### 2.2 Brechas de Modelo de Datos

| Tabla Motor | Campos | Tech Cyan Requerido | Brecha |
|---|---|---|---|
| `documents` | `document_id PK`, `relative_path UNIQUE`, `filename`, `content_sha256`, `file_size`, `modified_at`, `page_count`, `status`, `last_processed_at` | `app_meta`, `settings`, `provider_profiles`, migraciones versionadas | Motor tiene esquema propio; Tech Cyan necesita tabla `app_meta` separada para versión/instalación. |
| `pages` | `page_id PK`, `document_id FK`, `page_number`, `text`, `extraction_method`, `quality_status`, `error_message`, `ocr_engine`, `ocr_language`, `ocr_version` | Dos bases SQLite separadas: Tech Cyan independiente | No replicar ni modificar desde Tech Cyan directamente (según DATA_MODEL.md). |
| `pages_fts` | `text`, `document_id`, `page_number` (FTS5) | FTS5 existente en DB propia, no duplicar extracción/OCR/FTS5 | El motor ya tiene FTS5 `pages_fts`; Tech Cyan debe usar su propia DB, no la del motor. |
| `meta` | `key PK`, `value` | `settings`, `provider_profiles`, `maintenance_history`, `backup_history`, `job_history`, `audit_log`, `schema_migrations` | Motor usa `meta` simple; Tech Cyan necesita esquema expandido con historial y migraciones. |
| `artifacts` | `artifact_key PK`, `content_sha256`, `extraction_version`, `artifact_path`, `validation_status` | No definido en auditoría | Tabla nueva para artefactos derivados. |
| `processing_runs` | `run_id AIK`, `started_at`, `finished_at`, `run_type`, `files_processed`, `pages_extracted`, `pages_ocr`, `pages_failed`, `error_summary` | `job_history` con estados `pending`/`running`/`completed`/`failed`/`cancelled` | Estructuras compatibles pero nombres ligeramente diferentes. |

#### 2.3 Brechas de Flujo de Trabajo

| Flujo Motor | Flujo Tech Cyan | Brecha |
|---|---|---|
| `scan → update → search` | `dashboard → collection → research → maintenance` | Requerir mapeo de casos de uso y asegurarse de que el staging/transaccionalidad se preserve. |
| OCR bajo demanda | `ocr` procesa páginas pendientes | Mismo flujo, pero adapter debe exponer `process_pending_ocr` con parámetros configurables (dpi, límite, source). |
| Consulta con IA | `ask` modo mock por defecto, `--yes` para API | Mismo flujo, pero adapter debe añadir: distinguir ID de cita válido, referencia real y soporte semántico (según AGENTS.md §32). |
| Validación de integridad | `validate` CLI con `sys.exit()` | Adapter debe exponer validación como retorno estructurado (no como salida por consola + exit code). |
| Reindexación | `rebuild-index` reconstruye FTS5 desde texto | Requerir nuevo `reindex_collection` que combine rebuild FTS5 + re-OCR de páginas marcadas + re-validación de huellas. |

---

### 3. Brechas de Seguridad y Política

| Política Tech Cyan | Estado en Motor | Brecha |
|---|---|---|
| `preserve`: no mover colección PDF ni base documental automáticamente | Motor usa rutas hardcodeadas `COLLECTION_SOURCE` y `WORKSPACE_ROOT` basadas en usuario. | Rutas deben reescribirse para no mover datos automáticamente. |
| `embedded`: motor empaquetado pero independiente detrás de `DocumentEngineAdapter` | Motor es paquete Python embebido, pero `Repository()` abre DB en `WORKSPACE_ROOT/database/documents.db` — ruta usuario-dependiente. | Requerir configuración portable, no rutas absolutas de usuario. |
| `safe`: backup obligatorio antes de operaciones destructivas | No hay backup automático antes de `delete_document_pages()` ni actualizaciones masivas. | Implementar backup verificación previa a operaciones que modifiquen datos. |
| PDF originales solo lectura | No verificado estáticamente | Motor lee PDFs con `pymupdf.open()` y `pypdf.PdfReader()` — no hay escritura sobre archivos originales, pero sí riesgo en staging/extracción. | Validar que ninguna función modifique PDFs originales. |
| Dos SQLite separadas | Motor tiene su propia DB `documents.db`, Tech Cyan propuesta independiente | Motor no duplica extracción/OCR/FTS5 desde Tech Cyan (agente_documental_nuevo referencia). | Asegurar que Tech Cyan no llame a operaciones de escritura en la DB del motor. |
| Sin nube/sync en V1 | Motor tiene proveedor `APIProvider` con HTTP a endpoint externo | Brecha: motor provee soporte de proveedor externo, pero V1 de Tech Cyan excluye nube/sync. | Desactivar o enmascarar proveedor `api` por defecto; usar solo `mock`. |
| Sin embeddings/vector search sin decisión explícita | No encontrado en motor actual | Motor no tiene embeddings ni búsqueda vectorial. | Compatibilidad con decisión futura, no bloqueante. |
| Secretos en Windows Credential Manager | No verificado en código motor | `APIProvider` lee `DOC_AI_API_KEY` de env vars, no de Credential Manager. | Requerir integración con Windows Credential Manager para producción. |
| No SQL arbitrario, shell arbitrario ni rutas irrestrictas desde UI | Motor CLI usa `sys.exit()` y rutas hardcodeadas | El motor mismo es de consola; riesgo está al integrarse en GUI de Tech Cyan. | Validar que adapter no exponga rutas irrestrictas. |
| No enviar documentos completos a IA por defecto | `OUTPUT_INSTRUCTIONS` y `evidence_lines` envían solo fragmentos | Cumplido: `provider.synthesize()` recibe `evidence` (fragmentos seleccionados) + `instructions`, nunca documentos completos. | Mantener esta política en adapter. |

---

### 4. Brechas de Funcionalidad Reutilizable

| Categoría | % Código reutilizable | Comentario |
|---|---|---|
| Lógica pura (sin I/O, sin CLI) | ~65% | `fingerprint`, `evidence` (normalize, citation, build), `providers` (interfaces, Mock, validate), `query` (extract_terms, build_fts_query, render_answer), `ocr` (is_available, ocr_image_png) son módulos puros sin efectos secundarios. |
| Modelos y DTOs | ~80% | `QueryResult`, `Provider`, `ProviderError`, `MockProvider`, `APIProvider`, `citation_for`, estructuras de evidencia son compatibles con adaptación. |
| Consultas DB puras | ~70% | `search_fts`, `rebuild_fts_index`, `get_pending_ocr_pages`, `update_page_ocr`, `get_pages_by_document`, `get_document` son queries SQL que pueden reutilizarse si se corrigen riesgos. |
| Extracción PDF + OCR | ~50% | `extract_pdf_digital`, `extract_pdf`, `ocr_pages_if_needed`, `ocr_pdf_page` tienen lógica condicional y dependencias de configuración (umbrales, rutas). Requerir parametrización. |
| Scanner e inventario | ~80% | `scan_collection`, `compute_sha256`, `compute_file_metadata` son lógica pura, solo necesita rutas configurables. |
| CLI y presentación | ~0% | TODAS las funciones CLI usan `print()`/`sys.exit()` y tienen rutas hardcodeadas. Requerir reescritura completa para adapter. |
| Proveedores IA | ~70% | `MockProvider` es inmediato. `APIProvider` requiere configuración de credenciales y endpoints — adapter debe acoplarse a `ProviderManager` de Tech Cyan. |

**Total estimado:** Aproximadamente el 55-65% del código del motor puede reutilizarse o adaptarse con esfuerzo mediano, pero el 35-45% restante (capa de presentación/CLI, rutas, sistema de jobs, integración de seguridad) requiere reescritura o adaptación significativa.

---

### 5. Prioridades de Corrección para Integración

#### 5.1 Orden inmediato (primeros sprints)

1. **CRÍTICA - Staging transaccional en update** (R1/R5): Implementar patrón donde se extrae nuevo contenido primero, se insertan páginas nuevas, y solo entonces (o nunca) se borran las antiguas. Prevenir pérdida de datos en documentos modificados.

2. **CRÍTICA - Rutas configurable y portable** (R2): Reemplazar todas las rutas absolutas hardcodeadas por variables de entorno con valores por defecto detectados automáticamente o relativos al workspace.

3. **ALTA - Eliminar `sys.exit()` de funciones de motor** (R4): Reemplazar por excepciones personalizadas o tuplas `(éxito, mensaje)` para permitir reutilización desde adaptador GUI.

4. **ALPHA - Expositor `get_engine_status`** (brecha tabla 1): Nuevo método en `Repository` que retorne `Dict` con conteo de documentos, páginas, salud DB, y estado de configuración.

5. **ALHA - Wrapper `process_pending_ocr` unificado** (brecha tabla 1): Nueva función que acepte `(limit, dpi, source)` y retorne `List[Dict]` con resultados, sin imprimir ni llamar `sys.exit()`.

6. **ALTA - Adapter `ask_document_question`** (brecha tabla 1): Exponer `question: str + provider_mode opcional → QueryResult` con manejo de modo mock (declara sin síntesis) y modo aviso antes de enviar a API.

#### 5.2 Mediano plazo (2-3 sprints)

7. **MEDIA - Sistema de jobs/cola thread-safe** (R10): Implementar estructura básica de Job ID, estado, progreso y mecanismo de cancelación cooperativa para integración con UI CustomTkinter.

8. **MEDIA - Validar y Documentar esquema SQLite** (brechas modelo datos): Añadir `schema_migrations` table, `PRAGMA foreign_keys=ON`, y documentación de migraciones versionadas.

9. **MEDIA - Proveedor Registry/Manager** (brechas seguridad): Implementar `ProviderRegistry`, `CredentialStore` integración con Windows Credential Manager, y `FallbackPolicy` para fallback explícito (no silencioso).

10. **BAJA - `clean_derived_data` implementation** (brecha tabla 1): Nuevo método que respete backup-confirmar-restore patrón antes de limpiar datos derivados.

#### 5.3 Largo plazo (post-V1)

11. **BAJA - `reindex_collection` implementation** (brecha tabla 1): Combinar `rebuild_fts_index` + re-OCR de páginas marcadas + validación de huellas en un solo comando atómico.

12. **OPCIONAL - Búsqueda vectorial** (brecha política): Evaluar añadir embeddings/vector search en una versión posterior, según decisión explícita (según AGENTS.md §43: "Sin embeddings/vector search sin decisión explícita").

---

### 6. Muestra de Código: Adaptador Requerido (esbozo)

```python
# Propuesto: tech_cyan/application/document_engine_adapter.py

from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
import sqlite3

from document_engine.database import Repository
from document_engine.providers import get_provider, Provider, ProviderError
from document_engine.ocr import is_available
from document_engine.query import run_query, extract_terms, build_fts_query
from document_engine.evidence import build_evidence, citation_for

@dataclass
class EngineStatus:
    documents_total: int
    pages_total: int
    pages_with_text: int
    fts_index_rows: int
    ocr_available: bool
    provider_mode: str
    collection_root: Optional[str]

@dataclass  
class QueryResultDTO:
    question: str
    answer: str
    provider: str
    evidence: List[Dict[str, Any]]
    citations: Dict[str, Any]
    warnings: List[str]
    error: Optional[str]

class DocumentEngineAdapter:
    """Adapter que exponer el contrato DocumentEngineAdapter para Tech Cyan."""
    
    def __init__(self, db_path: Optional[Path] = None, 
                 collection_root: Optional[Path] = None,
                 ai_provider: Optional[str] = None):
        self.repo = Repository(db_path)
        self.collection_root = collection_root or self._detect_collection_root()
        self.provider_mode = ai_provider or get_ai_provider_default()
    
    def get_engine_status(self) -> EngineStatus:
        """Retorna estado estructurado del motor."""
        dc = self.repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        pc = self.repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        pw = self.repo.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE text IS NOT NULL AND LENGTH(TRIM(text)) > 0"
        ).fetchone()[0]
        fts = self.repo.conn.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
        oa = is_available()
        return EngineStatus(
            documents_total=dc,
            pages_total=pc,
            pages_with_text=pw,
            fts_index_rows=fts,
            ocr_available=oa,
            provider_mode=self.provider_mode,
            collection_root=str(self.collection_root) if self.collection_root else None,
        )
    
    def scan_collection(self, source: Optional[Path] = None) -> List[Dict]:
        """Escanear colección PDF. source opcional; usa colección registrada si no se provee."""
        from document_engine.scanner import scan_collection
        sp = source or Path(self.repo.get_meta("collection_root")) if self.repo.get_meta("collection_root") else None
        if sp is None:
            from document_engine.config import get_collection_source
            sp = get_collection_source()
        files = scan_collection(sp)
        # Retornar formato estandarizado (sin filepath absoluto si es sensible)
        return [
            {
                "document_id": f["document_id"],
                "relative_path": f["relative_path"],
                "filename": f["filename"],
                # Omitir filepath completo por seguridad
            } 
            for f in files
        ]
    
    def update_collection(self, source: Optional[Path] = None, use_ocr: bool = True) -> Dict[str, Any]:
        """Procesar nuevos/modificados en colección. Retorna reporte estructurado."""
        # TODO: Implementar staging transaccional antes de borrar páginas antiguas
        # Patrón: extraer → insertar → confirmar → borrar antiguas
        from document_engine.cli import cmd_update
        # NOTE: cmd_update usa sys.exit() y print(); adapter deberá reescribir lógica
        # Por ahora, delegar con advertencia
        raise NotImplementedError("cmd_update requiere reescritura para adapter - usar repo directamente")
    
    def search_documents(self, question: str, limit: int = 12) -> QueryResultDTO:
        """Buscar documentos con evidencia y cita verificada."""
        from document_engine.query import run_query
        result = run_query(
            question=question,
            provider_mode=self.provider_mode,
            evidence_limit=limit,
            evidence_items=limit * 2,
            repo=self.repo,
        )
        # Formatear a DTO
        return QueryResultDTO(
            question=result.question,
            answer=result.answer,
            provider=result.provider,
            evidence=result.evidence,
            citations=result.citations,
            warnings=result.warnings,
            error=result.error,
        )
    
    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Obtener metadatos de un documento."""
        return self.repo.get_document(document_id)
    
    def rebuild_search_index(self) -> int:
        """Reconstruir índice FTS5 desde datos existentes."""
        return self.repo.rebuild_fts_index()
    
    def process_pending_ocr(self, limit: Optional[int] = None, dpi: int = 200) -> List[Dict[str, Any]]:
        """OCR de páginas pendientes. Retorna lista de resultados por página."""
        from document_engine.database import Repository
        from document_engine import ocr as ocrmod
        results = []
        pending = self.repo.get_pending_ocr_pages(limit=limit)
        for p in pending:
            fp = Path(self.collection_root) / Path(p["relative_path"])
            if not fp.is_file():
                results.append({
                    "page_id": p["page_id"],
                    "document_id": p["document_id"],
                    "page_number": p["page_number"],
                    "error": "archivo_no_encontrado",
                })
                continue
            res = ocrmod.ocr_pdf_page(fp, p["page_number"], dpi=dpi)
            # Actualizar en BD
            self.repo.update_page_ocr(
                p["page_id"],
                res["text"],
                "ocr",
                "ok" if not res["error"] and len(res["text"]) >= 10 else ("suspicious" if len(res["text"]) > 0 else "ocr_required"),
                res["error"] or None,
                res["ocr_engine"],
                res["ocr_language"],
                res["ocr_version"],
            )
            results.append({
                "page_id": p["page_id"],
                "document_id": p["document_id"],
                "page_number": p["page_number"],
                "text": res["text"],
                "quality": res["error"] is None,
                "error": res["error"],
            })
        return results
    
    def ask_document_question(self, question: str, provider: Optional[str] = None) -> QueryResultDTO:
        """Consulta con evidencia e interpretación."""
        from document_engine.query import run_query
        mode = provider or self.provider_mode
        result = run_query(
            question=question,
            provider_mode=mode,
            evidence_limit=8,
            evidence_items=12,
            repo=self.repo,
        )
        return QueryResultDTO(
            question=result.question,
            answer=result.answer,
            provider=result.provider,
            evidence=result.evidence,
            citations=result.citations,
            warnings=result.warnings,
            error=result.error,
        )
    
    def validate_engine(self) -> Dict[str, Any]:
        """Comprobar integridad del índice. Retorna reporte estructurado."""
        # Simulación de validación sin print/sys.exit
        problems = 0
        
        # Integridad SQLite
        res = self.repo.conn.execute("PRAGMA integrity_check").fetchone()[0]
        if res != "ok":
            problems += 1
        
        # Claves foráneas
        fk = self.repo.conn.execute("PRAGMA foreign_key_check").fetchall()
        problems += len(fk)
        
        # Coherencia páginas <-> FTS5
        total_pages = self.repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        pages_with_text = self.repo.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE text IS NOT NULL AND LENGTH(TRIM(text)) > 0"
        ).fetchone()[0]
        fts_rows = self.repo.conn.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
        if fts_rows != pages_with_text:
            problems += 1
        
        # Huellas SHA-256
        without_hash = self.repo.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE content_sha256 IS NULL OR content_sha256 = ''"
        ).fetchone()[0]
        problems += without_hash
        
        # Páginas calidad mala
        bad = self.repo.conn.execute(
            "SELECT quality_status, COUNT(*) FROM pages GROUP BY quality_status"
        ).fetchall()
        bad_map = {k: v for k, v in bad if k in ("empty", "suspicious", "ocr_required", "error")}
        pendientes = self.repo.get_pending_ocr_pages()
        
        return {
            "problems_total": problems,
            "integrity_sqlite": res if 'res' in dir() else "unknown",
            "foreign_key_issues": len(fk),
            "fts_coherence": fts_rows == pages_with_text,
            "documents_without_hash": without_hash,
            "quality_distribution": bad_map,
            "pending_ocr_pages": len(pendientes),
        }
    
    def remove_document_index(self, document_id: str) -> bool:
        """Eliminar índice de un documento (páginas + FTS5)."""
        try:
            self.repo.delete_document_pages(document_id)
            return True
        except Exception:
            return False
    
    def clean_derived_data(self) -> Dict[str, Any]:
        """Limpiar datos derivados con backup-confirmar-restore."""
        # TODO: Implementar patrón completo
        # 1. Backup verificable de DB actual
        # 2. Confirmación explícita
        # 3. Staging de datos a conservar
        # 4. Ejecución de limpieza
        # 5. Validación posterior
        # 6. Restore si falla
        raise NotImplementedError("clean_derived_data requiere implementación completa")
    
    def reindex_collection(self) -> Dict[str, Any]:
        """Reindexación completa: rebuild FTS5 + re-OCR pendiente + validación."""
        from document_engine.database import Repository
        # 1. Reconstruir FTS5
        fts_count = self.rebuild_search_index()
        # 2. OCR de páginas pendientes
        ocr_results = self.process_pending_ocr()
        # 3. Validar resultado
        validation = self.validate_engine()
        return {
            "fts_reindexed": fts_count,
            "ocr_pages_processed": len(ocr_results),
            "validation": validation,
        }
    
    def close(self):
        self.repo.close()
```

---

### 7. Checklist de Validación para Integración

Antes de considerar al adapter listo para Tech Cyan, verificar:

- [ ] **No hay `print()`** en funciones expuestas del adapter (todos retornan DTO/valores)
- [ ] **No hay `sys.exit()`** en funciones expuestas del adapter
- [ ] **Todas las rutas son configurables por entorno** sin hardcodeos de usuario
- [ ] **Staging transaccional** en cualquier operación que elimine páginas antes de reextraer
- [ ] **Backup verificable** antes de operaciones destructivas (validar_engine o función separada)
- [ ] **Progress/cancelación** expuesta para UI CustomTkinter (IDs de job, estados, señales)
- [ ] **PDF originales sin alterar** — confirmar que ningúna función escribe sobre archivos fuente
- [ ] **Dos bases SQLite separadas** — Tech Cyan no escribe en DB del motor, ni lee/ modifica sus datos de forma permanente
- [ ] **Modo mock por defecto, API solo con --yes o autorización explícita**
- [ ] **Fragmentos limitados y autorizados** enviados a proveedor externo (nunca documentos completos)
- [ ] **Validación de citas** distingue ID válido, referencia real y soporte semántico
- [ ] **Licencia PyMuPDF** aprobada para distribución onedir
- [ ] **Pruebas unitarias aisladas** con `tmp_path` y fixtures temporales (según QUALITY_AND_TESTING.md)

---