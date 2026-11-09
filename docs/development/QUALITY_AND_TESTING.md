# Calidad y pruebas

Pirámide: unitarias, integración, aceptación, UI y empaquetado Windows limpio. Usar pytest, tmp_path, DB temporales y PDFs sintéticos/no sensibles. Separar tests de scripts operativos. Nunca ejecutar tests contra colección real.

Casos críticos: directorio DB inexistente; extracción fallida conserva páginas previas; FTS5 consistente; cancelación cooperativa; backup inválido aborta; restore valida; secretos no aparecen en logs; fallback no autorizado bloqueado; citas apuntan a páginas reales; Mock no finge síntesis; UI permanece responsiva. Reportar solo pruebas ejecutadas.
