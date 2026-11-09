# Tech Cyan Desktop Advanced

Documentación base para una aplicación Windows 11 x64 de investigación documental PDF, en español, con Python y CustomTkinter. Este paquete es una especificación inicial, no una implementación funcional.

## Decisiones confirmadas
- `preserve`: conservar ubicaciones actuales de colección PDF y base documental; no migrar automáticamente.
- `embedded`: integrar el motor en la distribución, pero mantenerlo independiente detrás de `DocumentEngineAdapter`.
- `safe`: backup obligatorio, confirmación explícita y validación posterior para operaciones destructivas.
- PDF originales estrictamente de solo lectura.
- Dos SQLite independientes: Tech Cyan y motor documental.
- OCR local con Tesseract; FTS5 existente; no duplicar extracción, OCR ni búsqueda.
- IA multiproveedor; Mock para desarrollo sin coste; secretos en Windows Credential Manager.
- Local-first/offline-first; sin nube en la primera versión.
- PyInstaller `onedir`; PowerShell 7 principal y WSL Bash alternativo.

## Inicio
1. Abrir OpenCode desde la raíz del proyecto.
2. Leer `AGENTS.md`, `PROMPT_MAESTRO.md` y `docs/PROJECT_STATUS.md`.
3. Hacer auditoría no destructiva del repositorio y motor.
4. Confirmar rutas reales antes de conectar datos.
5. No ejecutar limpiezas, migraciones ni reindexaciones sin respaldo y autorización.
