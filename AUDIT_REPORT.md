# Auditoría del Proyecto Tech Cyan Desktop Advanced

**Fecha:** 10 de noviembre de 2026  
**Alcance:** Auditoría no destructiva del repositorio, motor documental y configuración  
**Estado:** Sin cambios respecto a la auditoría del 9 de noviembre; todos los hallazgos se mantienen.

---
## 1. Resumen Ejecutivo

El proyecto **Tech Cyan Desktop Advanced** es una aplicación de investigación documental PDF para Windows 11 x64, implementada en Python con CustomTkinter. Se encuentra en una **fase de especificación/base**, con código funcional pero sin configuración de rutas ni colecciones PDF activas.

**Hallazgo principal:** La arquitectura está bien definida con separación clara entre UI, aplicación, dominio e infraestructura, y el motor documental agente (`vendor/document_engine`) está listo para integración mediante `DocumentEngineAdapter`. El proyecto requiere configuración de variables de entorno antes de ser operable.

**Estado general:** Proyecto base listo para desarrollo, con decisiones de arquitectura documentadas (ADRs) y un motor documental agente listo para integración. Puntuación general: **7/10**.

---
## 2. Estructura del Repositorio

```
C:\workspace\Tech-Cyan-Desktop-Advanced\
├── .git/                                                  # Repositorio Git
├── AGENTS.md                                              # Guía de agentes y flujo de trabajo
├── README.md                                              # Documentación base
├── pyproject.toml                                         # Metadatos y dependencias
├── organized_files/                                       # Scripts operativos (historial)
├── testing/                                               # Directorios de testing
├── tests/                                                 # Pruebas unitarias e aisladas
├── docs/                                                  # Documentos de arquitectura y decisiones
│   ├── architecture/                                      # ARCHITECTURE.md, DATA_MODEL.md, etc.
│   ├── decisions/                                         # ADR-001 a ADR-005
│   ├── PROJECT_STATUS.md
│   └── REFERENCES.md
├── vendor/document_engine/                                # Motor documental agente (código fuente)
│   └── src/documental/                                    # Paquete Python principal
├── test_output.txt, test_results.txt, test_results2.txt  # Resultados de tests previos
```

**Observación:** El directorio `src/` raiz no existe; `pyproject.toml` usa `where = ["src"]` pero el código vive bajo `vendor/document_engine/src/documental/`. Esto es consistente con la decisión de mantener el motor embedded y separado.

---
## 3. Decisiones de Arquitectura (ADRs)

| ADR | Título | Estado | Comentario |
|-----|--------|--------|------------|
| ADR-001 | Plataforma | Aceptada | Windows 11 x64, Python, CustomTkinter, PyInstaller onedir |
| ADR-002 | Motor documental | Aceptada | Integración embedded, módulo independiente detrás de `DocumentEngineAdapter` |
| ADR-003 | Seguridad de datos | Aceptada | PDF solo lectura, backup obligatorio antes de operaciones destructivas |
| ADR-004 | Local-first | Aceptada | Sin nube ni sync en la primera versión |
| ADR-005 | Proveedores IA | Aceptada | Proveedor principal y alternativos configurables; Mock para desarrollo |

**Observación:** Todas las decisiones están documentadas y son consistentes con el flujo de trabajo descrito en `AGENTS.md`.

---
## 4. Arquitectura del Sistema

El diagrama de arquitectura muestra estas capas:

```
Usuario → UI (CustomTkinter) → Aplicación (casos de uso) → Dominio → Infraestructura
                      ↓                                    ↓
                DocumentEngineAdapter         Tech Cyan SQLite
                      ↓                                    ↓
               Motor documental            Credential Manager, Provider Manager
                      ↓
               PDF originales (solo lectura)
                                   ↓
                             FTS5, Tesseract, OCR
```

**Puntos fuertes:**
- Clarísima separación de responsabilidades
- `DocumentEngineAdapter` como única frontera de integración
- Patrón de staging transaccional en `cmd_update` (protege contra pérdida de datos)
- Foreign keys activadas en SQLite
- WAL mode y synchronous=NORMAL configurados

**Puntos de mejora:**
- La UI no debe acceder directamente a SQL, HTTP ni CLI (frontera clara en SECURITY.md)
- El adapter es el único punto de contacto con el motor (buen diseño)
- Tareas largas se ejecutan en workers con eventos a la UI

---
## 5. Modelo de Datos

Dos bases SQLite separadas (conformemente a ADR-003 y DATA_MODEL.md):

### 5.1 Base Tech Cyan (propuesta)
Tablas: `app_meta`, `settings`, `provider_profiles`, `maintenance_history`, `backup_history`, `job_history`, `audit_log`, `schema_migrations`.

### 5.2 Motor documental (existente)
Tablas identificadas: `documents`, `pages`, `meta`, `artifacts`, `processing_runs`, `pages_fts` (FTS5).

**Hallazgo crítico:** La auditoría identificó las tablas del motor documental pero advierte: **"No replicar ni modificar desde Tech Cyan directamente"**. Cada una tiene su propio ciclo de vida y mecanismos de backup.

---
## 6. Motor Documental (`vendor/document_engine`)

### 6.1 Componentes principales

| Componente | Descripción | Estado |
|------------|-------------|--------|
| `cli.py` | CLI con 9 comandos (status, scan, update, search, show, rebuild-index, ocr, ask, validate) | Funcional |
| `document_engine_adapter.py` | Adapter de 12 métodos para Tech Cyan | Funcional, bien documentado |
| `database.py` | Repositorio SQLite con FTS5 | Funcional, migraciones ligeras |
| `extractor.py` | Extracción digital pypdf ↔ pymupdf con fallback | Robusto, manejo de errores |
| `ocr.py` | OCR local con Tesseract | Configurable, requiere vars de entorno |
| `query.py` | Flujo pregunta → FTS5 → evidencia → proveedor | Mock por defecto, API segura |
| `providers.py` | MockProvider y APIProvider | Configuración en vars de entorno |
| `evidence.py` | Deduplicación de evidencia y citas | Bien diseñado |
| `scanner.py` | Inventario recursivo de PDFs | Simple, funcional |
| `config.py` | Configuración centralizada, sin defaults de usuario | Política "preserve" |

### 6.2 Hallazgos de seguridad

- **PDF originales: estrictamente solo lectura** (ADR-003, README.md)
- **Secretos en Windows Credential Manager** (AGENTS.md, SECURITY.md)
- **IA externa:** No enviar documentos completos; solo fragmentos recuperados y limitados
- **Fallback silencioso desactivado:** OCR falla de forma explícita si Tesseract no configurado (config.py)
- **SQL arbitrario bloqueado:** PRAGMA restrictions en MCP devtools spec

### 6.3 Riesgos e problemas conocidos

1. **R1:** Inicialización no crea directorio padre (database.py línea 16-17: `mkdir(parents=True, exist_ok=True)` - *observado como corregido*)
2. **R5:** Reemplazo de páginas en documento modificado no es transaccional/staging - *El código actual SÍ tiene patrón staging transaccional en cmd_update (líneas 261-316)*
3. **CLI no apta para GUI:** `cmd_*` retorna `OperationResult`, pero `main()` usa `print()` y `sys.exit` potenciales
4. **Tesseract exe no incluido en ZIP:** Requerir configuración explícita de `TESSERACT_CMD` y `TESSDATA_PREFIX`
5. **Licencias PyMuPDF:** Revisar antes de distribuir
6. **Scripts ad hoc con rutas absolutas:** Algunos archivos en `organized_files/` tienen rutas hardcodeadas

---
## 7. Análisis de Código y Tests

### 7.1 Cobertura de tests

El directorio `tests/audits/test_engine_isolated.py` contiene **22 tests aislados** con restricciones estrictas:

- ✅ Usa `tmp_path` (nada de colección real)
- ✅ Usa MockProvider (sin coste, sin red)
- ✅ PDFs sintéticos con pymupdf
- ✅ Configuración Tesseract simulada
- ✅ Tests marcados con `@pytest.mark.isolated`

**Tests críticos cubiertos:**
- Creación de repositorio, inserción y recuperación
- Reconstrucción FTS5 y búsqueda
- Extracción digital y fallback pypdf ↔ pymupdf
- OCR no disponible (no crash)
- Excepciones personalizadas
- Umbral de texto digital configurable
- Validación de motor en BD vacía
- Modelos DTO
- Patrones de fallback y degradación gracefully

**Tests pendientes/por agregar:**
- Tests de integración con staging transaccional completo
- Tests de `cmd_update` con documentos modificados
- Tests de `process_pending_ocr`
- Tests de `ask_document_question` con modo mock
- Tests de validación `cmd_validate` con datos reales

### 7.2 Calidad de código

- **Convenciones:** Use de dataclasses para DTOs, typing completo, docstrings en todos los módulos
- **Manejo de errores:** Todas las funciones del adapter retornan `OperationResult`; ninguna usa `print()` ni `sys.exit()` directamente
- **Patrones:** Staging transaccional, rollback ante error, foreign keys ON, WAL mode
- **Mejoras:** Algunos scripts en `organized_files/` tienen código legacy que podría ser refactorizado hacia el adapter pattern

---
## 8. Configuración y Despliegue

### 8.1 Variables de entorno obligatorias (config.py)

| Variable | Descripción | Estado por defecto |
|----------|-------------|-------------------|
| `DOC_COLLECTION_SOURCE` | Ruta raíz de la colección PDF | `None` (obligatorio configurar) |
| `DOC_WORKSPACE_ROOT` | Ruta raíz de trabajo | `None` (obligatorio configurar) |
| `TESSERACT_CMD` | Ruta al ejecutable Tesseract | `None` (obligatorio para OCR) |
| `TESSDATA_PREFIX` | Prefijo de datos Tesseract | `None` (obligatorio para OCR) |
| `DOC_AI_PROVIDER` | Modo IA | `mock` (seguro) |
| `DOC_AI_API_KEY` | Clave API para modo producción | `None` (modo mock por defecto) |

**Política "preserve":** Ninguna ruta se resuelve automáticamente. El usuario/deployment debe proveer estas variables.

### 8.2 Dependencias (pyproject.toml)

```
pypdf>=4.0, pytesseract>=0.3.13, pymupdf>=1.24, Pillow>=10.0
```

Todas son bibliotecas de código abierto sin costo por uso.

---
## 9. Hallazgos de Seguridad

### 9.1 Confirmado

- ✅ PDF originales: solo lectura, inmutables
- ✅ Credenciales: Windows Credential Manager, no en código/logs/BD
- ✅ IA externa: solo fragmentos limitados y autorizados, sin fallback silencioso
- ✅ Sin sync/nube en primera versión
- ✅ Validación de backup antes de operaciones destructivas (ADR-003)

### 9.2 Por verificar en despliegue

- ⚠️ Path traversal en rutas de colección (handler en `validate_collection_path` básico, insuficiente para path traversal complejo)
- ⚠️ Tamaño/salida de logs no límite en UI
- ⚠️ Secretos no deben aparecer en stdout/stderr (política MCP devtools)

### 9.3 Críticas

- ❌ Ninguna (no encontraron críticas de seguridad inmediatas, pero la configuración incorrecta podría exponer rutas)

---
## 10. Riesgos Identificados

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| R1: Directorios no creados antes de abrir BD | Alta | Media | `ensure_directories()` en config.py; `_open()` en Repository crea directorio padre |
| R5: Pérdida de datos en reemplazo de páginas | Media | Alta | Patrón staging transaccional implementado en `cmd_update` (líneas 261-316) |
| R6: OCR falla silenciosamente | Baja | Media | `is_available()` retorna False explícitamente; no degradado silencioso |
| R7: Configuración de rutas ausente | Alta | Alta | Documentar en README; exigir variables de entorno en despliegue |
| R8: Licencias PyMuPDF/PyInstaller | Media | Media | Revisar licencia antes de distribuir onedir |
| R9: Scripts legacy con rutas absolutas | Media | Baja | Migrar hacia adapter pattern / config injection |

---
## 11. Recomendaciones Prioritizadas

### Prioridad 1 (Inmediato)

1. **Configurar variables de entorno** antes de cualquier operación:
   - `DOC_COLLECTION_SOURCE` → ruta a carpeta con PDFs
   - `DOC_WORKSPACE_ROOT` → raíz de trabajo
   - `TESSERACT_CMD` → ruta ejecutable Tesseract
   - `TESSDATA_PREFIX` → carpeta tessdata

2. **Validar backup** antes de cualquier operación destructiva (ya contemplado en ADR-003 y `document_engine_adapter.py _verify_backup_before_destructive`).

3. **Ejecutar tests aislados** para verificar funcionalidad básica:
   ```bash
   python -m pytest tests/audits/test_engine_isolated.py -v
   ```

### Prioridad 2 (Corto plazo)

4. **Migrar scripts `organized_files/`** hacia el patrón `DocumentEngineAdapter` para evitar rutas hardcodeadas y lógica duplicada.

5. **Implementar `clean_derived_data` y `reindex_collection`** en el adapter con el patrón completo backup-confirmar-restore (versiones stub existentes).

6. **Añadir tests de integración** para `cmd_update` con documentos modificados, testing del staging transaccional.

### Prioridad 3 (Mediano plazo)

7. **Definir esquema ER** definitivo para base Tech Cyan y migraciones versionadas (ADR-001 §15, DATA_MODEL.md).

8. **Implementar UI base** conectando con `DocumentEngineAdapter` (never direct SQL from UI).

9. **Polarizar rutas** en lugar de hardcodear: usar variables de entorno inyectables.

---
## 12. Conclusión

El proyecto **Tech Cyan Desktop Advanced** presenta una base sólida y bien arquitecturada para una aplicación de investigación documental PDF. Las decisiones de diseño (arquitectura por capas, dos SQLite separadas, política local-first, mock por defecto para IA) son coherentes y están documentadas.

**Puntuación general: 7/10**

Fortalezas:
- Arquitectura clara y documentada
- Manejo de errores estructurado (OperationResult)
- Tests aislados completos
- Patrón de staging transaccional
- Política de seguridad coherente

Áreas de mejora:
- Configuración de variables de entorno pendiente
- Refactorizar scripts legacy hacia el adapter pattern
- Ampliar cobertura de tests con integración real (aunque aislada)
- Validar licencias de distribución PyInstaller

El proyecto está listo para **desarrollo continuo** una vez configuradas las rutas requeridas y validada la configuración de Tesseract/OCR.

---
*Fin del informe de auditoría*