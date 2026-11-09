# Integración del motor documental

La auditoría del ZIP recomendó `agente_documental_nuevo`; verificar coincidencia con el código actual.

CLI auditada: status, scan, update, search, show, rebuild-index, ocr, ask, validate. `update` procesa nuevos/modificados; `rebuild-index` reconstruye FTS5 desde textos guardados; `ocr` procesa páginas pendientes. No hay comando público de reindexación completa ni de eliminación/limpieza general. `delete_document_pages` es interno.

Contratos propuestos de `DocumentEngineAdapter`: `get_engine_status`, `scan_collection`, `update_collection`, `search_documents`, `get_document`, `rebuild_search_index`, `process_pending_ocr`, `ask_document_question`, `validate_engine`, `remove_document_index` (nuevo), `clean_derived_data` (nuevo), `reindex_collection` (nuevo).

Cada operación larga devolverá DTO tipado, errores estructurados, progreso y cancelación cooperativa. No parsear stdout ni invocar CLI desde GUI.

Correcciones antes de GUI: crear directorios antes de abrir DB; staging para reemplazar documento modificado; añadir `__init__.py` si falta; separar servicios de CLI; parametrizar rutas/Tesseract; tests aislados. La validación actual de IDs de cita no equivale a soporte semántico. Revisar licencias PyMuPDF antes de distribuir.
