---
name: docs-lookup
description: Consulta documentación oficial y versionada de librerías (pypdf, pymupdf, CustomTkinter, SQLite/FTS5, pytest, PyInstaller) sin MCP externo. Reemplaza Context7.
---

# docs-lookup

Cargar solo cuando haya duda real sobre la API de una librería externa.

1. Identifica la versión instalada: `python -c "import <pkg>; print(<pkg>.__version__)"` o `pip show <pkg>`.
2. Prefiere documentación local: `python -m pydoc <pkg>`, `help(objeto)` y los stubs `.pyi` del paquete en el venv.
3. Si hace falta web, busca la página oficial de la API para esa versión concreta; no foros ni tutoriales.
4. Verifica la firma real antes de usarla: `python -c "import inspect, <pkg>; print(inspect.signature(<pkg>.funcion))"`.

Reglas:
- Nunca pegues documentación completa en el contexto; cita solo la firma o sección usada.
- Sin red, queda cubierto con `pydoc`/`help`.
- No cargar para código propio del repo (usar lectura directa del código).
