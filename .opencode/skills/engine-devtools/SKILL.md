---
name: engine-devtools
description: Diagnóstico seguro y de solo lectura del motor documental (SQLite, FTS5, tests, validación). Reemplaza el MCP techcyan-devtools propuesto.
---

# engine-devtools

Cargar solo en tareas de diagnóstico/validación del motor. Principios heredados de la spec del MCP: solo lectura, rutas allowlisted, tiempos y salidas limitados, sin secretos en stdout/stderr.

Comandos permitidos (desde la raíz del repo):
- Estado del motor: vía adapter en Python con DB temporal — `DocumentEngineAdapter(db_path=...).get_engine_status()`.
- Inspección SQLite: `sqlite3 "file:<ruta>?mode=ro" "SELECT ..."` — siempre URI `mode=ro` y `PRAGMA query_only=ON`.
- Rechazar SQL mutante (INSERT/UPDATE/DELETE/DDL) en cualquier inspección.
- Tests: `python -m pytest tests/audits -q` — solo rutas bajo `tests/`; nunca contra DB o colección real.
- Validación: `python -m pytest tests/audits -q -k validate`.

Prohibido:
- Escritura en la DB del motor fuera de transacciones del propio motor.
- Rutas fuera del workspace/temp; seguir symlinks que escapen.
- Ejecutar scripts heredados con rutas absolutas.

Mientras no exista `scripts/ops/`, usar el adapter en Python; no abrir la DB real sin autorización explícita.
