---
name: file-organizer
description: Organiza y gestiona archivos en el repositorio, creando directorios necesarios y reubicando archivos sueltos.
---

# file-organizer

## Descripción
Skill para organizar y mantener la estructura de archivos del proyecto Tech Cyan Desktop Advanced. Este skill:

1. Crea directorios necesarios según la estructura del proyecto
2. Reubica archivos sueltos en sus directorios correspondientes
3. Mantiene la ordenación de archivos tras cada fase de desarrollo
4. Puede ser llamado automáticamente o manualmente mediante OpenCode

## Cuando usar este skill
- Después de completar cualquier fase de desarrollo (Fases 0-4, E1, E2, E3)
- Cuando se añadan nuevos archivos al repositorio y necesiten ser organizados
- Para limpiar la raíz del proyecto y mover archivos a sus directorios correspondientes
- Como paso de mantenimiento periódico

## Funcionalidad principal

### 1. Creación de directorios necesarios
El skill crea automáticamente los directorios estándar del proyecto si no existen:
- `testing/` - Directorios para testing (collection, backup, db, extracted, logs, reports)
- `organized_files/` - Directorio para archivos sueltos movidos
- Cualquier otro directorio estándar del proyecto

### 2. Reubicación de archivos sueltos
Mueve automáticamente archivos sueltos de la raíz del proyecto a sus directorios correspondientes:
- `TESTING_REAL_RESTRICTIONS_RELEASE.md` → `testing/`
- `fix_tests.patch` / `fix_extractor_fallback.patch` → Raíz del proyecto (parches)
- `opencode.json` - Se mantiene en raíz (configuración del agente)
- `AGENTS.md` - Se mantiene en raíz (documentación del proyecto)
- `pyproject.toml` - Se mantiene en raíz (configuración de build)
- `README.md` - Se mantiene en raíz
- `PROMPT_MAESTRO.md` - Se mantiene en raíz
- `test_*.txt` - Archivos de output de tests → `testing/reports/`
- `None` (archivo binario) → `organized_files/`

### 3. Verificación y mantenimiento
Verifica el estado actual del repositorio e informa sobre:
- Directorios faltantes que deberían crearse
- Archivos sueltos identificados y su ubicación sugerida
- Estado general de ordenación del repositorio

## Ejemplos de uso

### Llamada automática mediante OpenCode
```json
{
  "skill": "file-organizer",
  "action": "organize",
  "parameters": {}
}
```

### Llamada manual desde la línea de comandos
```bash
opencode -s file-organizer -a organize
```

### Ejemplos de uso específico

#### Después de completar una fase de desarrollo
```json
{
  "skill": "file-organizer",
  "action": "organize-after-phase",
  "parameters": {
    "phase": "E3",
    "focus": "reindex_collection-and-cleanup"
}
```

#### Verificar estado actual del repositorio
```json
{
  "skill": "file-organizer",
  "action": "check-status",
  "parameters": {}
}
```

## Estructura de directorios gestionada

El skill gestiona la siguiente estructura de directorios:

```
/Tech-Cyan-Desktop-Advanced/
├── .gitignore
├── AGENTS.md              # Se mantiene en raíz
├── opencode.json          # Se mantiene en raíz
├── pyproject.toml         # Se mantiene en raíz
├── TESTING_REAL_RESTRICTIONS_RELEASE.md  # Documentación de testing
├── fix_tests.patch        # Parche de tests
├── fix_extractor_fallback.patch  # Parche de fallback
├── organized_files/       # Archivos sueltos movidos
│   └── ...archivos diversos...
├── docs/                  # Documentación del proyecto
├── tests/                 # Tests del proyecto
│   └── testing/
│       ├── collection/          # PDFs de testing
│       ├── backup/              # Backup de colección
│       ├── db/                  # Base de datos de testing
│       ├── extracted/           # Texto extraído
│       ├── logs/                # Logs de ejecución
│       └── reports/             # Reports generados
├── vendor/                # Módulo documental
├── organized_files/       # Archivos sueltos movidos manualmente
├── opencode.json          # Configuración del agente
├── README.md
├── FIX_*.patch            # Parches de corrección
├── TECH_Cyan_*.py         # Scripts de ayuda
├── tech_test*.py          # Tests diversos
├── TECH_Cyan-Desktop-Advanced/
│   └── ... (código fuente)
├── organized_files/       # Moved files from root
├── TECH_Cyan-Desktop-Check.py
├── TECH_Cyan-Desktop-ConfigFix.py
├── TECH-Cyan-Desktop-E1.py a E3.py
├── organized_files/
│   └── ...scripts de ayuda...
├── TESTING_REAL_RESTRICTIONS_RELEASE.md
├── TECH_Cyan-Desktop-UpdateDoc.py
├── TECH_Cyan-Desktop-Fix.py
├── TECH_Cyan-Desktop-Inspect.py a Inspect9.py
├── TECH_Cyan-Desktop-ReleaseDoc.py
├── TECH_Cyan-Desktop-UpdateDoc.py
└── TECH_Cyan-Desktop-*.py
```

## Mejores prácticas

1. Ejecutar este skill después de cada fase de desarrollo importante
2. Revisar el reporte de qué archivos se movieron y por qué
3. Mantener la raíz del proyecto libre de archivos sueltos siempre que sea posible
4. Usar `organized_files/` para archivos que no tienen un lugar claro inicialmente
5. Ejecutar el skill al menos una vez por sprint o hito importante
6. **NUEVA REGLA: Verificar comandos CLI antes de generar scripts** (AGENTS.md §7, DOCUMENT_ENGINE.md §5)
   - Antes de generar cualquier script nuevo `TECH_Cyan-Desktop-*.py`, verificar si la funcionalidad ya está cubierta por los comandos CLI del motor documental:
     - `status` - estado del motor
     - `scan` - inventario de colección
     - `update` - extraer/actualizar documentos
     - `search` / `ask` - consultas con evidencia
     - `show` - mostrar documento y páginas
     - `rebuild-index` - reconstruir FTS5
     - `ocr` - OCR de páginas pendientes
     - `validate` - validar integridad del índice
   - **Patrón:** Si el CLI puede realizar la operación (retorna `OperationResult`, no usa `print()`/`sys.exit()` directamente), **preferir siempre el CLI** sobre crear un nuevo script
   - **Excepción:** Solo generar un nuevo script si:
     a) La operación requiere automatización compleja no cubierta por el CLI
     b) Se necesita una UI específica o integración particular
     c) El caso de uso es único y temporal (usar `organized_files/` en su lugar)
   - **Documentación:** Cada nuevo script debe incluir un comentario en la primera línea indicando:
     - `// CLI coverage: <command>` si cubre funcionalidad existente, o
     - `// CLI gap: <description>` si cubre un vacío no cubierto por el CLI
   - **Obsolete detection:** Revisar `organized_files/` y `docs/decisions/ADR-*` antes de crear; si el script ya existe o la decisión arquitectural lo desaconseja, no generarlo

## Limitaciones
- No mueve archivos críticos del sistema del proyecto (AGENTS.md, opencode.json, pyproject.toml)
- Estos archivos se mantienen en la raíz por diseño y propósito específico
- El skill está diseñado para el proyecto Tech Cyan Desktop Advanced y puede no ser compatible directamente con otros repositorios sin adaptación