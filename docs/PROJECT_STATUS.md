# Estado inicial

Documentación base preparada; no implica que Tech Cyan ya esté implementado.

## Decisiones
Windows 11 x64; Python/CustomTkinter; arquitectura por capas; DB Tech Cyan separada; motor embedded e independiente; ubicación documental preserve; PDF solo lectura; backup obligatorio; Tesseract local; IA multiproveedor y Mock; sin nube inicial; PyInstaller onedir; español; PowerShell 7/WSL Bash.

## Auditoría heredada (verificar contra repo actual)
Rama recomendada: `agente_documental_nuevo`. CLI: status, scan, update, search, show, rebuild-index, ocr, ask, validate. DB: documents, pages, meta, artifacts, processing_runs y pages_fts FTS5. Riesgos: inicialización no crea directorio padre; reemplazo de páginas en documento modificado no es transaccional/staging; CLI no apta para GUI; sin progreso/cancelación estructurada; scripts ad hoc con rutas absolutas; Tesseract exe no incluido en ZIP; revisar licencia PyMuPDF.

## Próximos hitos
1 reconocimiento; 2 estabilizar motor; 3 adapter; 4 SQLite Tech Cyan; 5 servicios/jobs; 6 UI; 7 IA; 8 mantenimiento; 9 QA y empaquetado.
