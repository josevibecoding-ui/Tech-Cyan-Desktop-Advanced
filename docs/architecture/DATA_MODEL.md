# Modelo de datos

## Dos bases separadas

### Tech Cyan SQLite (propuesta)
| Tabla | Propósito |
|---|---|
| app_meta | versión/instalación |
| settings | preferencias |
| provider_profiles | configuración no secreta |
| maintenance_history | operaciones |
| backup_history | respaldos y verificación |
| job_history | trabajos/estados |
| audit_log | eventos redactados |
| schema_migrations | migraciones |

Credenciales fuera de SQLite, en Windows Credential Manager. El esquema final requiere ER y migraciones aprobadas.

### Motor documental
Auditoría identificó `documents`, `pages`, `meta`, `artifacts`, `processing_runs` y `pages_fts` (FTS5). No replicar ni modificar desde Tech Cyan directamente.

Usar transacciones, foreign_keys en DB propia, conexiones por hilo, busy timeout y migraciones versionadas. Evaluar WAL con pruebas. No cambiar el journal mode de la DB del motor sin autorización/compatibilidad. Backup consistente mediante mecanismos SQLite adecuados.
