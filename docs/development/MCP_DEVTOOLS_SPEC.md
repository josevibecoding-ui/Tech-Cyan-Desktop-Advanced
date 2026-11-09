# Especificación techcyan-devtools (propuesto, no implementado)

Python 3.11+, SDK oficial MCP Python, stdio, uv. Tools: `get_project_report`, `check_environment`, `inspect_sqlite` (solo lectura), `inspect_fts_index`, `validate_document_engine`, `run_pytest` (targets allowlisted), `run_lint`, `run_build_check`, `get_test_report`.

No crear `run_command` genérico. Allowlist de rutas bajo workspace/temp; bloquear path traversal y symlinks que escapen; SQLite URI `mode=ro`, `query_only=ON`; rechazar SQL mutante; allowlist de tests; límites de tiempo/salida; no secretos en stdout/stderr. Respuestas estructuradas pequeñas. Mantener `enabled:false` hasta pruebas de seguridad e integración.
