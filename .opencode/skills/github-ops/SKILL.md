---
name: github-ops
description: Operaciones Git/GitHub vía CLI git/gh locales, sin servidor MCP ni Docker. Reemplaza el MCP de GitHub (github-mcp-server).
---

# github-ops

Cargar solo para tareas de issues/PRs/repos remotos.

- Estado local: `git status --short`, `git log --oneline -10`, `git diff`.
- Remoto (si existe `gh`): `gh issue list`, `gh pr view <n>`, `gh pr diff <n>` — solo lectura por defecto.
- Autenticación: credential helper de git o `gh auth login`; nunca tokens en comandos, logs ni archivos del repo.

Reglas:
- Prohibido `push --force`, rebase de ramas compartidas y edición de historial sin autorización.
- No abrir/editar issues ni PRs sin confirmación del usuario.
- Reemplaza al MCP `github` (contenedor Docker con `--read-only`): mismo alcance, sin contenedor.
