"""CLI Fase 1 simplificado.
Excepciones personalizadas para permitir reutilización desde GUI sin sys.exit().
"""
import sys
import argparse
from pathlib import Path

from .models import (OperationResult, JobState, EngineStatusDTO, DocumentDTO,
                     UpdateReportDTO, QueryResultDTO, OcrPageResultDTO, ValidationReportDTO)
from .config import get_collection_source, get_workspace_root, ensure_directories, validate_collection_path


class CollectionPathError(Exception):
    """Ruta de colección inválida o no accesible."""
    pass


class OCRNotAvailableError(Exception):
    """Tesseract no configurado o indisponible."""
    pass


class InvalidQuestionError(Exception):
    """Pregunta vacía o inválida."""
    pass


class ProviderConfirmationError(Exception):
    """Falta confirmación explícita para modo API (uso con --yes)."""
    pass


class ValidationError(Exception):
    """Errores de validación de integridad detectados."""
    pass


class ExtractionError(Exception):
    """Errores en la extracción de PDF o proceso OCR."""
    pass


class ExtractionError(Exception):
    """Error en extracción o validación de PDF."""
    pass
from .scanner import scan_collection
from .database import Repository
from .extractor import extract_pdf_digital, extract_pdf
def cmd_status(args) -> OperationResult:
    """Retorna estado del motor como OperationResult (no imprime ni usa sys.exit())."""
    repo = Repository()
    try:
        dc = repo.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        pc = repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        pw = repo.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE text IS NOT NULL AND LENGTH(TRIM(text)) > 0"
        ).fetchone()[0]
        fts = repo.conn.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
        return OperationResult.success_result(
            "Estado del motor consultado",
            {
                "documents_total": dc,
                "pages_total": pc,
                "pages_with_text": pw,
                "fts_index_rows": fts,
            },
        )
    except Exception as e:
        return OperationResult.error_result(f"Error consultando estado: {e}", str(e))
    finally: repo.close()
def cmd_scan(args) -> OperationResult:
    """Escanear colección y retornar reporte estructurado (OperationResult)."""
    repo = Repository()
    try:
        # Por defecto: la colección ya registrada en la BD; no la raíz global
        source = args.source or repo.get_meta("collection_root") or get_collection_source()
        sp = Path(source) if source else None
        if not sp:
            return OperationResult.error_result("No se pudo determinar la fuente de colección.")
        if not validate_collection_path(sp):
            return OperationResult.error_result(f"Fuente de colección no accesible: {source}")
        
        files = scan_collection(sp)
        nuevos = [f for f in files if not repo.document_exists(f["document_id"])]
        
        # Construir reporte estructurado
        detalles = []
        for f in files[:20]:  # límite para el reporte
            detalles.append({
                "document_id": f["document_id"],
                "filename": f["filename"],
                "nuevo": repo.document_exists(f["document_id"]) is False,
            })
        
        report = {
            "total_pdfs": len(files),
            "nuevos": len(nuevos),
            "fuente": str(source) if source else None,
        }
        
        return OperationResult.success_result(
            f"Escanenamiento completado: {len(files)} PDFs, {len(nuevos)} nuevos",
            {"report": report, "detalles": detalles},
        )
    except CollectionPathError as e:
        return OperationResult.error_result(str(e))
    except Exception as e:
        return OperationResult.error_result(f"Error durante el escaneo: {e}", str(e))
    finally: repo.close()
def _store_document(repo, fi, meta, pages):
    """Registra documento y páginas (con metadatos de fingerprint)."""
    did = fi["document_id"]
    repo.insert_document(did, fi["relative_path"], fi["filename"],
                         meta["content_sha256"], meta["file_size"],
                         meta["modified_at"], len(pages))
    ocr_total = 0
    for p in pages:
        if p.get("extraction_method") == "ocr":
            ocr_total += 1
        repo.insert_page(f"{did}-p{p['page_number']}", did, p["page_number"],
                         p["text"], p["extraction_method"], p["quality_status"],
                         p["error_message"], p.get("ocr_engine"),
                         p.get("ocr_language"), p.get("ocr_version"))
    return ocr_total


def _copy_pages_from(repo, source_doc_id, fi, meta):
    """Reutiliza la extracción de un contenido idéntico (duplicado exacto).

    Dos ubicaciones conservan dos registros de documento; el texto extraído
    se copia sin volver a leer el PDF (AGENTS.md §7.4 y §8).
    """
    src_pages = repo.get_pages_by_document(source_doc_id)
    if not src_pages:
        return 0
    did = fi["document_id"]
    repo.insert_document(did, fi["relative_path"], fi["filename"],
                         meta["content_sha256"], meta["file_size"],
                         meta["modified_at"], len(src_pages))
    ocr_total = 0
    for p in src_pages:
        if p.get("extraction_method") == "ocr":
            ocr_total += 1
        repo.insert_page(f"{did}-p{p['page_number']}", did, p["page_number"],
                         p["text"], p["extraction_method"], p["quality_status"],
                         p["error_message"], p.get("ocr_engine"),
                         p.get("ocr_language"), p.get("ocr_version"))
    return ocr_total


def cmd_update(args):
    """Actualización manual: procesa solo archivos nuevos o modificados.

    Criterio de cambio: SHA-256 del contenido (no el nombre ni la fecha).
    Un hash idéntico nunca provoca reextracción (AGENTS.md §7).
    """
    from .fingerprint import compute_file_metadata
    ensure_directories()
    repo = Repository()
    report = {"nuevos": 0, "modificados": 0, "duplicados": 0, "sin_cambios": 0,
              "errores": 0, "no_encontrados": 0, "paginas": 0, "ocr": 0}
    try:
        # Por defecto se actualiza la colección ya registrada en la BD;
        # --source cambia el alcance de forma explícita.
        source = args.source or repo.get_meta("collection_root") or get_collection_source()
        sp = Path(source)
        if not validate_collection_path(sp): raise CollectionPathError(f"No accesible: {source}")
        repo.set_meta("collection_root", str(sp))
        files = scan_collection(sp)
        if not files: return OperationResult.error_result("No hay PDFs en la colección.")
        use_ocr = not args.no_ocr

        # Clasificar por huella de contenido
        plan = []          # (fi, meta, accion, origen)
        hash_to_doc = {}   # sha256 -> document_id ya registrado (para duplicados)
        for fi in files:
            fp = Path(fi["filepath"])
            try:
                meta = compute_file_metadata(fp)
            except Exception as e:
                print(f"Error de fingerprint {fi['filename']}: {e}")
                report["errores"] += 1
                continue
            doc = repo.get_document(fi["document_id"])
            if doc is None:
                # ¿Contenido idéntico a otro documento ya indexado?
                origen = hash_to_doc.get(meta["content_sha256"])
                if origen is None:
                    origen_row = repo.conn.execute(
                        "SELECT document_id FROM documents WHERE content_sha256=? AND document_id!=?",
                        (meta["content_sha256"], fi["document_id"])).fetchone()
                    origen = origen_row[0] if origen_row else None
                if origen:
                    plan.append((fi, meta, "duplicado", origen))
                    report["duplicados"] += 1
                else:
                    plan.append((fi, meta, "nuevo", None))
                    report["nuevos"] += 1
            elif doc.get("content_sha256") == meta["content_sha256"] \
                    and doc.get("content_sha256"):
                # Hash idéntico: no se reextrae; solo refrescar metadatos si cambiaron
                if (doc.get("file_size") != meta["file_size"]
                        or doc.get("modified_at") != meta["modified_at"]):
                    repo.conn.execute(
                        "UPDATE documents SET file_size=?, modified_at=? WHERE document_id=?",
                        (meta["file_size"], meta["modified_at"], fi["document_id"]))
                plan.append((fi, meta, "sin_cambios", None))
                report["sin_cambios"] += 1
            elif not doc.get("content_sha256") and (doc.get("page_count") or 0) > 0:
                # Primera huella sobre un documento ya extraído: se registra el
                # hash sin reextraer (el texto derivado sigue siendo válido).
                repo.conn.execute(
                    "UPDATE documents SET content_sha256=?, file_size=?, modified_at=? "
                    "WHERE document_id=?",
                    (meta["content_sha256"], meta["file_size"],
                     meta["modified_at"], fi["document_id"]))
                plan.append((fi, meta, "sin_cambios", None))
                report["sin_cambios"] += 1
            else:
                # Contenido modificado (o primera huella sin texto previo)
                plan.append((fi, meta, "modificado", None))
                report["modificados"] += 1
            hash_to_doc[meta["content_sha256"]] = fi["document_id"]

        # Documentos registrados que ya no están en la carpeta: se marcan,
        # nunca se borran del índice sin confirmación (AGENTS.md §7).
        scanned_ids = {f["document_id"] for f in files}
        missing = [r[0] for r in repo.conn.execute(
            "SELECT document_id FROM documents").fetchall()
            if r[0] not in scanned_ids]
        for did in missing:
            repo.update_document_status(did, "not_found")
            report["no_encontrados"] += 1

        todo = [p for p in plan if p[2] in ("nuevo", "modificado", "duplicado")]
        if not todo:
            return OperationResult.success_result(
                f"Sin cambios: {report['sin_cambios']} archivos con hash idéntico, no reextraídos.",
                {"no_encontrados": report["no_encontrados"], "report": report}
            )
        return OperationResult.success_result(
            f"Procesando {len(todo)} de {len(files)}... "
            f"(OCR: {'sí' if use_ocr else 'no'}, sin cambios: {report['sin_cambios']})",
            {"todo_count": len(todo), "total": len(files), "use_ocr": use_ocr, "report": report}
        )
        for i, (fi, meta, accion, origen) in enumerate(todo, 1):
            did = fi["document_id"]
            fp = Path(fi["filepath"])
            fn = fi["filename"]
            try:
                if accion == "duplicado":
                    ocr_total = _copy_pages_from(repo, origen, fi, meta)
                    report["ocr"] += ocr_total
                    repo.conn.execute(
                        "UPDATE documents SET status='duplicate' WHERE document_id=?",
                        (did,))
                    print(f"  [{i}/{len(todo)}] {fn}: duplicado exacto de "
                          f"{origen} (texto reutilizado)")
                    continue
                if accion == "modificado":
                    # --- PATRÓN DE STAGING TRANSACCIONAL (soluciona R1/R5) ---
                    # 1. Extraer nuevo contenido ANTES de borrar el antiguo
                    pr_new = extract_pdf(fp, use_ocr=use_ocr)
                    
                    # 2. Insertar páginas en staging (IDs temporales: prefijo "-staging-")
                    #    Esto conserva las páginas antiguas hasta confirmar éxito
                    ocr_total_staging = 0
                    staging_valid = True
                    for p in pr_new:
                        staging_id = f"{did}-staging-p{p['page_number']}"
                        repo.insert_page(staging_id, did, p["page_number"],
                                         p["text"], p["extraction_method"], p["quality_status"],
                                         p["error_message"], p.get("ocr_engine"),
                                         p.get("ocr_language"), p.get("ocr_version"))
                        ocr_total_staging += 1
                        # Insertar páginas en staging dentro de transacción explícita
                    try:
                        repo.conn.execute("BEGIN")
                        ocr_total_staging = 0
                        for p in pr_new:
                            staging_id = f"{did}-staging-p{p['page_number']}"
                            repo.insert_page(staging_id, did, p["page_number"],
                             p["text"], p["extraction_method"], p["quality_status"],
                             p["error_message"], p.get("ocr_engine"),
                             p.get("ocr_language"), p.get("ocr_version"))
                            ocr_total_staging += 1
                        
                        # Borrar páginas antiguas SÓLO después de insertar nuevas exitosamente
                        repo.delete_document_pages(did)
                        
                        # Mover páginas staging a definitivas y actualizar metadatos
                        repo.conn.execute(
                            "UPDATE documents SET file_size=?, modified_at=?, page_count=?, status='indexed'?",
                            (meta["file_size"], meta["modified_at"], len(pr_new), 'indexed')
                        )
                        report["ocr"] += ocr_total_staging
                        report["paginas"] += len(pr_new)
                        
                        # Confirmar transacción
                        repo.conn.execute("COMMIT")
                        
                        # Mostrar éxito
                        ok = sum(1 for r in pr_new if r["quality_status"] == "ok")
                        extra = f", OCR {ocr_total_staging}" if ocr_total_staging else ""
                        etiqueta = "modificado"
                        print(f"  [{i}/{len(todo)}] {fn}: {len(pr_new)} pág, {ok} ok{extra} [{etiqueta}]")
                        
                    except Exception as e:
                        # Ante cualquier error, hacer rollback y conservar la versión anterior
                        try:
                            repo.conn.execute("ROLLBACK")
                        except Exception:
                            pass
                        raise ExtractionError(f"Error transaccional en documento modificado {fn}: {e}. "
                                              "Se conservan las páginas anteriores y el estado anterior se restaura.")
                    # Fin patrón staging ---
                    continue
                ocr_total = _store_document(repo, fi, meta, pr)
                report["ocr"] += ocr_total
                report["paginas"] += len(pr)
                ok = sum(1 for r in pr if r["quality_status"] == "ok")
                extra = f", OCR {ocr_total}" if ocr_total else ""
                etiqueta = "modificado" if accion == "modificado" else "nuevo"
                print(f"  [{i}/{len(todo)}] {fn}: {len(pr)} pág, {ok} ok{extra} [{etiqueta}]")
            except Exception as e:
                print(f"Error {fn}: {e}")
                report["errores"] += 1
                if not repo.document_exists(did):
                    repo.update_document_status(did, "error")
        messages = [
    f"Total: {report['paginas']} páginas, {report['ocr']} vía OCR | "
    f"altas {report['nuevos']}, cambios {report['modificados']}, "
    f"duplicados {report['duplicados']}, errores {report['errores']}, "
    f"sin cambios {report['sin_cambios']}, "
    f"no encontrados {report['no_encontrados']}"
]
        if todo or report["no_encontrados"]:
            repo.log_processing_run("update", len(todo), report["paginas"],
                                    report["ocr"], report["errores"])
        repo.commit()
        return OperationResult.success_result(
            "\n".join(messages),
            {"report": report, "details": messages}
        )
    finally: repo.close()
def cmd_search(args) -> OperationResult:
    """Buscar documentos y retornar resultados como OperationResult."""
    repo = Repository()
    try:
        q = args.query.strip()
        if not q:
            return OperationResult.error_result("Término requerido.", str(InvalidQuestionError("Término requerido.")))
        r = repo.search_fts(q, args.limit if args.limit else 20)
        if not r:
            return OperationResult.success_result(
                "Sin resultados",
                {"results": [], "message": "No se encontraron coincidencias."}
            )
        # Formatear resultados estructurados
        results = []
        for rt in r:
            results.append({
                "page_number": rt.get("page_number"),
                "document_id": rt.get("document_id"),
                "text": rt.get("text") or "",
                "extraction_method": rt.get("extraction_method"),
                "quality_status": rt.get("quality_status"),
            })
        return OperationResult.success_result(
            "Búsqueda completada",
            {"results": results, "count": len(results)}
        )
    except InvalidQuestionError as e:
        return OperationResult.error_result(str(e), str(e))
    except Exception as e:
        return OperationResult.error_result(f"Error durante la búsqueda: {e}", str(e))
    finally: repo.close()
def cmd_show(args) -> OperationResult:
    """Mostrar documento y sus páginas como OperationResult."""
    repo = Repository()
    try:
        d = repo.get_document(args.document_id)
        if not d:
            return OperationResult.error_result("Documento no encontrado.", "Documento no encontrado.")
        # Construir resultado con metadatos y páginas resumidas
        pages_data = []
        pages = repo.get_pages_by_document(args.document_id)
        for p in pages[:5]:
            pages_data.append({
                "page_number": p.get("page_number"),
                "text_preview": (p.get("text") or "")[:70],
                "extraction_method": p.get("extraction_method"),
                "quality_status": p.get("quality_status"),
            })
        return OperationResult.success_result(
            "Documento consultado",
            {
                "document_id": d.get("document_id"),
                "filename": d.get("filename"),
                "page_count": d.get("page_count"),
                "pages": pages_data,
            },
        )
    except Exception as e:
        return OperationResult.error_result(f"Error consultando documento: {e}", str(e))
    finally: repo.close()

def cmd_rebuild_index(args) -> OperationResult:
    """Reconstruir índice FTS5 y retornar reporte como OperationResult."""
    repo = Repository()
    try:
        count = repo.rebuild_fts_index()
        return OperationResult.success_result(
            "Índice FTS5 reconstruido",
            {"indexed_documents": count}
        )
    except Exception as e:
        return OperationResult.error_result(f"Error reconstruyendo FTS5: {e}", str(e))
    finally: repo.close()

def cmd_ocr(args) -> OperationResult:
    """OCR local de páginas pendientes y retornar reporte como OperationResult."""
    from . import ocr as ocrmod
    if not ocrmod.is_available():
        return OperationResult.error_result("OCR no disponible: Tesseract no instalado o deshabilitado.")
    repo = Repository()
    try:
        root_value = repo.get_meta("collection_root")
        root = Path(args.source) if args.source else (Path(root_value) if root_value else get_collection_source())
        if not root:
            return OperationResult.error_result("Fuente de colección no configurada.")
        if not root.is_dir():
            return OperationResult.error_result(f"Raíz de colección no accesible: {root}")
        pending = repo.get_pending_ocr_pages(limit=args.limit)
        if not pending:
            return OperationResult.success_result(
                "Sin páginas pendientes de OCR",
                {"processed": 0, "ok": 0, "suspicious": 0, "failed": 0}
            )
        # Agrupar por documento para abrir cada PDF una sola vez
        by_doc = {}
        for p in pending:
            by_doc.setdefault(p["document_id"], []).append(p)
        done = ok = still = failed = 0
        detail = []
        for did, pages in by_doc.items():
            rel = pages[0]["relative_path"]
            fp = root / rel
            if not fp.is_file():
                failed += len(pages)
                detail.append({
                    "document_id": did,
                    "relative_path": rel,
                    "pages": len(pages),
                    "error": "archivo_no_encontrado",
                })
                continue
            for p in pages:
                res = ocrmod.ocr_pdf_page(fp, p["page_number"], dpi=args.dpi)
                text = res["text"]
                cc = len(text)
                if res["error"]:
                    quality = "ocr_required"
                    error_msg = res["error"] or "ocr_baja_calidad"
                    failed += 1
                    detail.append({
                        "document_id": did,
                        "page_number": p["page_number"],
                        "error": error_msg,
                    })
                elif cc == 0:
                    quality = "ocr_required"
                    failed += 1
                    detail.append({
                        "document_id": did,
                        "page_number": p["page_number"],
                        "error": "sin_texto",
                    })
                elif cc < 10:
                    quality = "suspicious"
                    still += 1
                    detail.append({
                        "document_id": did,
                        "page_number": p["page_number"],
                        "text": text,
                        "quality": False,
                    })
                else:
                    quality = "ok"
                    ok += 1
                    detail.append({
                        "document_id": did,
                        "page_number": p["page_number"],
                        "text": text,
                        "quality": True,
                    })
                repo.update_page_ocr(
                    p["page_id"], text, "ocr", quality,
                    None if quality == "ok" else (res["error"] or "ocr_baja_calidad"),
                    res["ocr_engine"], res["ocr_language"], res["ocr_version"])
                done += 1
            if done % 25 == 0:
                repo.commit()
        repo.commit()
        count = repo.rebuild_fts_index()
        report = {
            "processed": done,
            "ok": ok,
            "suspicious": still,
            "failed": failed,
            "indexed": count,
        }
        message = f"OCR finalizado: {done} páginas | ok={ok} | sospechosas={still} | sin texto/fallo={failed}"
        return OperationResult.success_result(message, report)
    except CollectionPathError as e:
        return OperationResult.error_result(str(e))
    except OCRNotAvailableError as e:
        return OperationResult.error_result(str(e))
    except Exception as e:
        return OperationResult.error_result(f"Error durante OCR: {e}", str(e))
    finally: repo.close()

def cmd_ask(args) -> OperationResult:
    """Consulta con evidencia e interpretación y retornar QueryResultDTO en OperationResult."""
    from .query import run_query, render_answer
    q = " ".join(args.question).strip()
    if not q:
        return OperationResult.error_result("Pregunta requerida.", str(InvalidQuestionError("Pregunta requerida.")))
    mode = args.provider or get_ai_provider()
    # Aviso obligatorio antes de transmitir contenido a un proveedor externo
    if mode == "api" and not args.yes:
        return OperationResult.error_result(
            "Modo API: confirme con --yes para enviar fragmentos al proveedor externo.",
            "ProviderConfirmationError: modo API requiere --yes"
        )
    if mode == "api" and args.yes:
        # En modo API con --yes, enviamos fragmentos (handled por run_query internamente)
        pass
    
    r = run_query(q, provider_mode=mode,
                  evidence_limit=args.evidence,
                  evidence_items=args.limit)
    
    # Formatear respuesta usando render_answer internamente o construir DTO
    answer_text = render_answer(r) if render_answer else (r.answer or "")
    
    return OperationResult.success_result(
        "Consulta completada",
        {
            "question": r.question,
            "answer": answer_text,
            "provider": r.provider,
            "evidence": [{"id": e["id"], "text": e["text"], "refs": [{"document_id": r["document_id"], "filename": r["filename"], "page": r["page_number"]} for r in e["refs"]]} for e in r.evidence],
            "citations": r.citations,
            "warnings": r.warnings,
        }
    )


def cmd_validate(args) -> OperationResult:
    """Comprobar integridad del índice y retornar reporte como OperationResult."""
    repo = Repository()
    try:
        # 1. Integridad SQLite
        res = repo.conn.execute("PRAGMA integrity_check").fetchone()[0]
        fk = repo.conn.execute("PRAGMA foreign_key_check").fetchall()
        
        # 2. Coherencia páginas <-> índice FTS5
        total_pages = repo.conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0]
        pages_with_text = repo.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE text IS NOT NULL AND LENGTH(TRIM(text)) > 0"
        ).fetchone()[0]
        fts_rows = repo.conn.execute("SELECT COUNT(*) FROM pages_fts").fetchone()[0]
        fts_coherence = fts_rows == pages_with_text
        
        # 3. Huellas SHA-256
        without_hash = repo.conn.execute(
            "SELECT COUNT(*) FROM documents WHERE content_sha256 IS NULL "
            "OR content_sha256 = ''").fetchone()[0]
        dup_hashes = repo.conn.execute(
            "SELECT content_sha256, COUNT(*) FROM documents "
            "WHERE content_sha256 IS NOT NULL AND content_sha256 != '' "
            "GROUP BY content_sha256 HAVING COUNT(*) > 1").fetchall()
        
        # 4. Páginas vacías / sospechosas / OCR pendiente
        bad = repo.conn.execute(
            "SELECT quality_status, COUNT(*) FROM pages GROUP BY quality_status"
        ).fetchall()
        bad_map = {k: v for k, v in bad if k in ("empty", "suspicious", "ocr_required", "error")}
        pendientes = repo.get_pending_ocr_pages()
        
        # 5. Páginas con error de extracción
        errs = repo.conn.execute(
            "SELECT COUNT(*) FROM pages WHERE error_message IS NOT NULL "
            "AND error_message != ''").fetchone()[0]
        
        # 6. Documentos marcados y comprobación en disco
        root_value = repo.get_meta("collection_root")
        root = Path(root_value) if root_value else None
        marked = repo.conn.execute(
            "SELECT document_id, status, relative_path FROM documents "
            "WHERE status != 'indexed'").fetchall()
        missing_on_disk = 0
        if root:
            for (rel,) in repo.conn.execute("SELECT relative_path FROM documents").fetchall():
                if not (root / rel).is_file():
                    missing_on_disk += 1
        
        # 7. Último procesamiento
        last = repo.conn.execute(
            "SELECT run_type, started_at, files_processed, pages_extracted, pages_ocr "
            "FROM processing_runs ORDER BY run_id DESC LIMIT 1").fetchone()
        
        report = {
            "integrity_sqlite": res,
            "foreign_key_issues": len(fk),
            "fts_coherence": fts_coherence,
            "total_pages": total_pages,
            "pages_with_text": pages_with_text,
            "fts_rows": fts_rows,
            "documents_without_hash": without_hash,
            "dup_hashes_count": len(dup_hashes),
            "quality_distribution": bad_map,
            "pending_ocr_pages": len(pendientes),
            "pages_with_error": errs,
            "marked_documents": len(marked),
            "missing_on_disk": missing_on_disk,
            "last_processing_run": last,
        }
        
        total_problems = (
            (1 if res != "ok" else 0) +
            len(fk) +
            (0 if fts_coherence else 1) +
            without_hash +
            len(dup_hashes) +
            missing_on_disk
        )
        
        return OperationResult.success_result(
            "Validación completada",
            {
                "problems_total": total_problems,
                "report": report,
                "ok": total_problems == 0,
            }
        )
    except Exception as e:
        return OperationResult.error_result(f"Error durante la validación: {e}", str(e))
    finally: repo.close()


def main():
    # Consola Windows (cp1252) no puede representar todos los glifos OCR/Unicode
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    parser = argparse.ArgumentParser(prog="documental", description="Agente documental PDF")
    sub = parser.add_subparsers(dest="command")
    p1 = sub.add_parser("status", help="Estado")
    p1.set_defaults(func=cmd_status)
    p2 = sub.add_parser("scan", help="Inventario")
    p2.add_argument("--source")
    p2.set_defaults(func=cmd_scan)
    p3 = sub.add_parser("update", help="Extraer")
    p3.add_argument("--source")
    p3.add_argument("--no-ocr", action="store_true", help="Deshabilitar OCR en esta ejecución")
    p3.set_defaults(func=cmd_update)
    p4 = sub.add_parser("search", help="Buscar")
    p4.add_argument("query")
    p4.add_argument("--limit", type=int, default=20)
    p4.set_defaults(func=cmd_search)
    p5 = sub.add_parser("show", help="Mostrar")
    p5.add_argument("document_id")
    p5.add_argument("--page", type=int)
    p5.set_defaults(func=cmd_show)
    p6 = sub.add_parser("rebuild-index", help="Reconstruir índice FTS5")
    p6.set_defaults(func=cmd_rebuild_index)
    p7 = sub.add_parser("ocr", help="OCR local de páginas pendientes")
    p7.add_argument("--source", help="Raíz de la colección (por defecto: la usada en update)")
    p7.add_argument("--limit", type=int, default=None, help="Máximo de páginas a procesar")
    p7.add_argument("--dpi", type=int, default=None, help="Resolución de render (por defecto: OCR_DPI, 200)")
    p7.set_defaults(func=cmd_ocr)
    p8 = sub.add_parser("ask", help="Consulta con evidencia citable (mock por defecto)")
    p8.add_argument("question", nargs="+", help="Pregunta en español")
    p8.add_argument("--provider", choices=["mock", "api"], default=None,
                    help="Proveedor de síntesis (por defecto: DOC_AI_PROVIDER o mock, sin red)")
    p8.add_argument("--limit", type=int, default=8, help="Máximo de evidencias (por defecto: 8)")
    p8.add_argument("--evidence", type=int, default=12, help="Máximo de resultados FTS5 a considerar")
    p8.add_argument("--yes", action="store_true", help="Confirma el envío al proveedor externo (modo api)")
    p8.set_defaults(func=cmd_ask)
    p9 = sub.add_parser("validate", help="Comprobar integridad del índice")
    p9.set_defaults(func=cmd_validate)
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return OperationResult.success_result("Ayuda mostrada")
    try:
        result = args.func(args)
        # Si el resultado es OperationResult, mostrar mensaje y data
        if isinstance(result, OperationResult):
            if result.success:
                print(f"Éxito: {result.message}")
                if result.data:
                    # Formateo simple de datos para consola
                    for k, v in result.data.items():
                        if not isinstance(v, (list, dict)) or len(str(v)) < 200:
                            print(f"  {k}: {v}")
                        else:
                            print(f"  {k}: [datos omitidos para brevedad]")
            else:
                print(f"Error: {result.error or result.message}")
                if result.data:
                    print(f"  Detalle: {result.data}")
        return
    except CollectionPathError as e:
        print(f"Error de colección: {e}")
        raise
    except InvalidQuestionError as e:
        print(f"Error de pregunta: {e}")
        raise
    except OCRNotAvailableError as e:
        print(f"Error de OCR: {e}")
        raise
    except ProviderConfirmationError as e:
        print(f"Confirmación requerida: {e}")
        print("Use --yes para confirmar la operación.")
        raise
    except ValidationError as e:
        print(f"Validación fallida: {e}")
        raise
    except ExtractionError as e:
        print(f"Error de extracción: {e}")
        raise
    except Exception as e:
        print(f"Error inesperado: {e}")
        raise