# MCP para OpenCode

`opencode.json` usa el esquema actual: servidores directamente bajo `mcp`.

- Context7 remoto habilitado: `https://mcp.context7.com/mcp`.
- GitHub MCP local con Docker, `--read-only` y toolsets `repos,issues,pull_requests`; deshabilitado por defecto. Requiere Docker y `GITHUB_PERSONAL_ACCESS_TOKEN` en entorno, nunca en el JSON.
- `techcyan-devtools` local vía `uv`, deshabilitado hasta implementarlo y superar tests.

PowerShell: `$env:GITHUB_PERSONAL_ACCESS_TOKEN = Read-Host 'Token GitHub'` (solo sesión actual). No escribir token en repo/prompt.

Verificar `opencode --version`, `opencode mcp list` y `/mcps`. Los MCP agregan contexto; habilitar solo los necesarios.
