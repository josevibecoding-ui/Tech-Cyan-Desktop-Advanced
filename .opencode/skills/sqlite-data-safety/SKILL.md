---
name: sqlite-data-safety
description: Diseña SQLite, migraciones, backups y mantenimiento seguro.
compatibility: opencode
---

# sqlite-data-safety

Cargar solo cuando la tarea corresponda. Leer AGENTS.md y ADRs. Trabajar en español, inspeccionar código real y distinguir existente/propuesto. Hacer cambios pequeños, probar con fixtures temporales y documentar resultados.

Dos DB separadas. Secretos fuera de SQLite. Backup verificable antes de operaciones destructivas; si falla, abortar. Transacciones y migraciones. No modificar originales.
