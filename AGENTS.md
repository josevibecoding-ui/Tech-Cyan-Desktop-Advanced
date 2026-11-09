# AGENTS.md — Tech Cyan Desktop Advanced

Idioma: español. Entorno: Windows 11 x64, PowerShell 7 (WSL alternativo). Sin rutas absolutas de equipo.

## Decisiones confirmadas (no re-preguntar; detalle en docs/adr/)
`preserve` · `embedded` · `safe` · PDF originales solo lectura · dos SQLite separadas · sin nube/sync · sin embeddings.

## Flujo de trabajo
1. Inspecciona (estructura, git, dependencias, tests) antes de editar.
2. Distingue existente / propuesto / pendiente.
3. Cambios pequeños, reversibles, probados; plan primero en tareas amplias.
4. Autorización para: migraciones, borrados, cambios arquitectónicos, operaciones sensibles.
5. Reporta solo pruebas realmente ejecutadas y su resultado.

## Fronteras
- UI → servicios → `DocumentEngineAdapter` → motor. Nunca SQL, HTTP ni CLI desde UI.
- Secretos solo en Windows Credential Manager. A IA: solo evidencia limitada y autorizada, nunca documentos completos. Sin fallback silencioso.
- Destructivo: backup verificable → confirmación → staging → validación. Si el backup falla, abortar.
- Tests solo con `tmp_path` y PDFs sintéticos; nunca contra colección real.

## Detalles bajo demanda (no cargar por defecto)
- Arquitectura: `ARCHITECTURE.md` · Motor: `DOCUMENT_ENGINE.md` · Datos: `DATA_MODEL.md` · Remediación: `ENGINE_REMEDIATION_PLAN.md` · Seguridad: `SECURITY.md`.
- Skills: cargar solo las de la tarea (`testing-quality`, `sqlite-data-safety`, `document-engine-integration`, `python-desktop`, `architecture`, `ai-provider-integration`, `packaging-windows`, `engine-devtools`, `docs-lookup`, `github-ops`).
