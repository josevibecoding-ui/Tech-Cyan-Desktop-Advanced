# Seguridad y privacidad

PDF originales inmutables. DB documental propiedad del motor. DB Tech Cyan para settings, perfiles, jobs, auditoría y backups. Secretos en Windows Credential Manager.

IA externa: no enviar documentos completos por defecto; solo fragmentos recuperados, limitados y autorizados. No fallback silencioso. Redactar secretos y evitar prompts/documentos completos en logs. Mostrar proveedor/modelo.

Mantenimiento: diagnóstico → vista previa y conteos → backup obligatorio verificable → confirmación → staging/transacción → ejecución → validación → auditoría. Si backup falla, abortar.

Sin SQL arbitrario, shell arbitrario ni filesystem irrestricto desde UI/MCP. Validar rutas, evitar path traversal, limitar tamaño/salida y usar datos temporales en tests.
