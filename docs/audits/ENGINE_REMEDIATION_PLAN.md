# ENGINE_REMEDIATION_PLAN.md — Tech Cyan Desktop Advanced

## 1. Objetivo y Alcance

**Propósito:** Consolidar los hallazgos y las recomendaciones técnicas derivadas de la auditoría estática del motor documental `vendor/document_engine` (versión 0.1.0) contra la arquitectura objetivo de Tech Cyan Desktop Advanced. Este documento sirve como referencia única, coherente y sin contradicciones para la remediación antes de la integración con `DocumentEngineAdapter` y la interfaz CustomTkinter.

**Alcance:** Incluye todos los riesgos identificados en `ENGINE_STATIC_AUDIT.md` y `ENGINE_INTEGRATION_GAPS.md`, su consolidación en clasificaciones de riesgo significativas, el diseño de estabilización en fases E1–E5, y el contrato definitivo de 12 métodos para el adaptador `DocumentEngineAdapter`. Queda expressly prohibido ejecutar cualquier operación sobre colecciones PDF reales, bases de datos persistentes ni el motor CLI durante la vigencia de este documento.

**Fuentes:** `ENGINE_STATIC_AUDIT.md`, `ENGINE_INTEGRATION_GAPS.md`, código fuente en `vendor/document_engine/src/documental/`, y las decisiones arquitectónicas confirmadas en `AGENTS.md`.

**Estado de fases:**
- **E0:** Complegada. Auditoría cruzada y planificación de remediación.
- **E1:** Pendiente de autorización explícita del usuario. Integridad transaccional, rutas configurables, OCR y seguridad de datos.
- **E2–E5:** Por definir después de completar y verificar E1.

---

## 2. Fuentes de Auditoría

| Fuente | Contenido | Última validación |
|---|---|---|
| `ENGINE_STATIC_AUDIT.md` | Auditoría estática no destructiva de `vendor/document_engine/src/documental/` (13 módulos, 504 líneas de hallazgos, 14 riesgos R1–R13). | 08/11/2026 |
| `ENGINE_INTEGRATION_GAPS.md` | Brechas de integración entre motor actual y `DocumentEngineAdapter` propuesto (422 líneas, mapeo de contrapartes, brechas de arquitectura, seguridad, reutilización). | 08/11/2026 |
| Código fuente | 13 archivos Python en `vendor/document_engine/src/documental/` (`__main__.py`, `_main__.py`, `scanner.py`, `query.py`, `providers.py`, `ocr.py`, `fingerprint.py`, `extractor.py`, `evidence.py`, `database.py`, `config.py`, `cli.py`, `models.py`). | 08/11/2026 |
| Decisiones arquitectónicas | `AGENTS.md`: política `preserve`, `embedded`, `safe`; dos bases SQLite separadas; sin nube/sync V1; secretos fuera código; no embeddings sin decisión explícita; PDF originales solo lectura. | 08/11/2026 |

**Hallazgos comprobados (evidencia directa en código):** R1 (línea cli.py:182–186), R2 (config.py:4–6), R3 (config.py:12), R4 (8 instancias en cli.py:23,161,164,240,316,324,326,411), R5 (cli.py:182–186 + database.py:121–133), R6 (providers.py:154–165), R7 (database.py:16), R9 (extractor.py:12 + ocr.py:151), R11 (ausencia de `__init__.py`), R13 (database.py:66–73).

**Hallazgos por análisis arquitectónico:** Falta `ProviderRegistry`, `ProviderManager`, `FallbackPolicy`, `ResponseNormalizer`; dos bases SQLite separadas no duplicar extracción/OCR/FTS5; `OUTPUT_INSTRUCTIONS` y `evidence_lines` garantizan que no se envían documentos completos a IA.

**Hallazgos aún no verificados (requieren ejecución):** Comportamiento de `pymupdf`/`pypdf` con PDFs dañados/protegidos; disponibilidad real de Tesseract en máquinas de despliegue; variables de entorno reales en producción; rendimiento FTS5 en colecciones grandes.

---

## 3. Estado Actual del Motor

El motor documental `agente-documental` versión 0.1.0 es una aplicación CLI embebida implementada en Python 3.11+ con la siguiente arquitectura de capas:

| Capa | Descripción |
|---|---|
| **Presentación (CLI)** | `cli.main()` con `argparse`, 9 subcomandos (`scan`, `update`, `search`, `ask`, `validate`, `ocr`, `rebuild-index`, `show`, `status`). Usa `print()` y `sys.exit()` en todas las funciones. Rutas hardcodeadas de usuario. |
| **Aplicación** | Flujo de trabajo: `scan → update → search → ask → validate`. Lógica de negocio en `query.py`, `evidence.py`, `providers.py`, `ocr.py`, `extractor.py`. |
| **Dominio** | Modelos: `QueryResult`, `Provider`, `ProviderError`, `MockProvider`, `APIProvider`, `citation_for`, `build_evidence`. Utilidades: `fingerprint.compute_sha256()`, `compute_file_metadata()`. Lógica pura sin efectos secundarios. |
| **Infraestructura** | `Repository` (SQLite): tablas `documents`, `pages`, `pages_fts` (FTS5), `meta`, `artifacts`, `processing_runs`. Configuración en `config.py` con rutas absolutas hardcodeadas. Probar Tesseract OCR. No hay `PRAGMA foreign_keys=ON` activado por default. |

**Funcionalidades cubiertas (~65% reutilizables):**
- `fingerprint.compute_sha256()`, `compute_file_metadata()`
- `evidence.citation_for()`, `build_evidence()`, `evidence_lines()`
- `providers.MockProvider`, `get_provider()`, `validate_citations()`
- `query.extract_terms()`, `build_fts_query()`, `render_answer()`
- `ocr.is_available()`, `ocr.ocr_image_png()`, `ocr.ocr_pdf_page()`, `ocr.ocr_pages_if_needed()`
- `scanner.scan_collection()`, `fingerprint.compute_sha256()`, `compute_file_metadata()`
- `database.search_fts()`, `rebuild_fts_index()`, `get_pending_ocr_pages()`, `update_page_ocr()`, `get_document()`, `get_pages_by_document()`

**Funcionalidades que requieren reescritura (~35%):**
- Todas las funciones CLI (uso de `print()`/`sys.exit()`, rutas hardcodeadas)
- Dependencias de configuración usuario-specific
- Riesgos transaccionales en `update_collection`

**Esquema SQLite existente:** tablas `documents`, `pages`, `pages_fts` (FTS5 virtual, tokenize `unicode61 remove_diacritics 2`), `meta`, `artifacts`, `processing_runs`. Sin foreign keys activas en el esquema CREATE TABLE. Migración ligera por columnas OCR faltantes.

**12 métodos contractuales `DocumentEngineAdapter`** (diseño propuesto, por implementar en E3):
1. `get_engine_status`
2. `scan_collection`
3. `update_collection`
4. `search_documents`
5. `get_document`
6. `rebuild_search_index`
7. `process_pending_ocr`
8. `ask_document_question`
9. `validate_engine`
10. `remove_document_index`
11. `clean_derived_data`
12. `reindex_collection`

---

## 4. Corrección integral de la estrategia transaccional

### 4.1 Distinción de datos y hashes

Con precisión técnica, definimos los siguientes tipos de hash:

- **SHA-256 del archivo PDF fuente**: Resumen criptográfico del archivo binario completo (`pdffile.pdf`). Se calcula mediante `hashlib.sha256(open("pdffile.pdf", "rb").read()).hexdigest()`. **No se compara directamente** con hash de contenido extraído.

- **Fingerprint del archivo fuente**: Hash calculado sobre el mismo tipo de contenido que se utilizará para comparaciones. En el motor actual, el `content_sha256` almacenado en `documents` debe corresponderse con el hash del contenido textual extraído, no con el binario del PDF.

- **Hash del contenido extraído**: Si se extrae texto del PDF, el hash resultante de ese texto. **No se debe comparar** el SHA-256 binario del PDF con el hash del texto extraído, ya que son tipos de contenido diferentes.

- **Hash de página o fragmento**: Hash opcional de porciones de texto extraídas.

**Regla de cambio de documento**: El documento debe determinarse como "modificado" comparando **fingerprints calculados sobre el mismo archivo y mediante el mismo algoritmo**. En la práctica actual, se compara el `content_sha256` almacenado contra un nuevo fingerprint calculado sobre el contenido extraído del PDF fuente con el mismo algoritmo y nivel de procesamiento.

**Verificación en código**: Antes de recomendar cambiar la semántica de `content_sha256`, verificar estáticamente cómo se almacena actualmente en `database.py`. Si `content_sha256` almacena el hash del contenido extraído (no el binario), la comparación es coherente; si almacena el hash binario, cambiaría la semántica de todo el sistema. **Pendiente de verificación estática**.

### 4.2 Secuencia única de actualización

Sólo existe una secuencia normativa para la actualización de documentos. Elimina pseudocódigo contradictorio y describe un único flujo normativo dividido en tres fases:

#### Fase A — Preparación externa (fuera de transacción SQLite)

1. **Identificar el documento y consultar su estado actual**: Consultar `documents` por `document_id`. Registrar `content_sha256`, `page_count`, `status`, `last_processed_at` pre-existentes.

2. **Comprobar que la ruta del PDF corresponde a una ubicación configurada y autorizada**: Validar mediante `validate_collection_path()`. Si la ruta no existe, informar y abortar. **No seleccionar automáticamente** otra carpeta (política `preserve`).

3. **Calcular el fingerprint del archivo fuente**: Aplicar la función de fingerprint sobre el PDF fuente. **No comparar** con hash de contenido extraído.

4. **Determinar si existe un cambio**: Comparar fingerprint contra `content_sha256` almacenado. Si idéntico, documento sin cambios → abortar procedimiento. Si distinto, marcar como `modificado`.

5. **Ejecutar extracción PDF y OCR necesario fuera de la transacción de sustitución**: 
   - `extract_pdf(fp, use_ocr=use_ocr)` sobre el PDF fuente.
   - Si falla: **abortar inmediatamente sin modificar la BD**. El documento conserva su estado anterior. Finalizar procedimiento (Fase A, paso 8).

6. **Preparar los resultados**: Almacenar temporalmente en memoria o archivo provisional **fuera de la BD**. No insertar nada en `pages`, `pages_fts` ni `documents` aún.

7. **Validar su estructura y calidad** (fuera de transacción):
   - Verificar `character_count > 0` solo para páginas que efectivamente contengan texto (ver 4.3).
   - Confirmar `quality_status` no sea `"failed"`.
   - Validar `content_sha256` nuevo contra fingerprint calculado.
   - **Si falla**: abortar procedimiento. **No se han insertado registros definitivos.** El documento conserva su estado anterior. Finalizar procedimiento (Fase A).

8. **Abortar sin modificar la base si la extracción o validación falla**: El sistema queda en estado idéntico al previo al inicio del procedimiento.

### 4.3 Eliminación de `sys.exit()` en la CLI (Fase E2)

**Contexto:** Fase E2 de remediación - authorized explicitamente en sesión actual. Objetivo: Sustituir todas las instancias de `sys.exit()` en `cli.py` por excepciones personalizadas relanzadas, permitiendo que el hilo UI (CustomTkinter u otra interfaz) decida cómo manejar los fallos.

**7 instancias de `sys.exit(1)` en `cli.py` identificadas y plan de sustitución:**

| Línea | Excepción Actual | Contexto | Sustitución E2 |
|-------|-----------------|----------|----------------|
| **700** | `CollectionPathError` | Ruta de colección inválida o no accesible | `raise CollectionPathError` - El UI colección decidirá mostrar error o solicitar ruta nueva |
| **703** | `InvalidQuestionError` | Pregunta vacía o inválida | `raise InvalidQuestionError` - El UI pregunta decidirá reingresar o cancelar |
| **706** | `OCRNotAvailableError` | Tesseract no configurado o indisponible | `raise OCRNotAvailableError` - El UI decidirá configurar Tesseract o deshabilitar OCR (`OCR_ENABLED=0`) |
| **710** | `ProviderConfirmationError` | Falta confirmación explícita modo API | `raise ProviderConfirmationError` - El UI mostrará `--yes` prompt o cancelará operación |
| **713** | `ValidationError` | Validación fallida de datos | `raise ValidationError` - El UI mostrará detalles y permitirá corrección |
| **716** | `ExtractionError` | Error en extracción PDF/OCR | `raise ExtractionError` - El UI decidirá reintentar, omitir página o abortar lote |
| **719** | `Exception` genérico | Cualquier error inesperado | `raise Exception` (o excepción específica) - El UI mostrará error crítico y decidirá recuperación |

**Patrón de sustitución (para cada bloque except en `cli.py:698-719`):**

```python
# ACTUAL (líneas 700-719):
except CollectionPathError as e:
    print(f"Error de colección: {e}")
    sys.exit(1)

# E2 (sustitución):
except CollectionPathError as e:
    print(f"Error de colección: {e}")
    raise  # Relanzar excepción para que el hilo UI la maneje
```

**Justificación:**

1. **Consistencia con E1** - `test_exceptions_are_raisable` validó que excepciones personalizadas pueden capturarse sin `sys.exit()`
2. **Sin degradación silenciosa** - Los fallos son explícitos, el UI decide el manejo
3. **UI decide** - CustomTkinter u otra interfaz gráfica capturará la excepción y decidirá: mostrar mensaje, registrar, solicitar decisión, abortar operación, continuar con datos parciales, etc.
4. **Mantiene flujo** - La excepción burbujea al llamador principal (main CLI o ventana UI), no sale inmediatamente del proceso

**Integración con políticas inmutables:**

- ✅ `preserve`: PDFs originales jamás tocados - la excepción permite UI decidir abortar sin escribir
- ✅ `embedded`: Motor independiente - la excepción burbujea al UI, no al motor
- ✅ `safe`: Sin `sys.exit()` silencioso - fallos explícitos, validación posterior
- ✅ Sin nube/sync V1: Decisión tomada puramente en CLI/UI local
- ✅ Dos bases SQLite separadas: La excepción no toca bases directamente; UI decidirá si hacer operaciones

**Fase de implementación:** E2. Este cambio pertenece a la fase E2 y es un requisito previo para el desacoplamiento CLI/GUI y el JobManager completo.

**Resultado esperado:**
- `cli.py` ya no contiene `sys.exit()` en funciones críticas
- Todas las excepciones son personalizadas y definidas en el propio `cli.py` (líneas 12-29)
- El hilo UI (CustomTkinter u otra interfaz) captura excepciones y decide manejo
- 100% compatible con pruebas `test_exceptions_are_raisable` (giá E1 aprobado)

**Ejemplo de flujo completo E2:**

1. Usuario ejecuta comando CLI: `doc scan --source /ruta/colección`
2. Si `/ruta/colección` no existe → `CollectionPathError` se relanza (`raise`)
3. El hilo UI captura `CollectionPathError`
4. UI muestra: "Ruta de colección inválida. ¿Desea configurar una nueva ruta?"
5. Usuario decide: Sí → UI configura `DOC_COLLECTION_SOURCE`, No → UI aborta operación graceful
6. **Nunca** `sys.exit(1)` - el proceso permanece abierto, UI toma decisión

**Verificación:** Después de la sustitución, ejecutar `test_exceptions_are_raisable` para confirmar que todas las excepciones personalizadas siguen funcionando correctamente sin `sys.exit()`.

#### Fase B — Sustitución atómica (dentro de transacción SQLite)

9. **Iniciar una transacción SQLite explícita**: `conn.execute("BEGIN")` o `conn.execute("BEGIN TRANSACTION")`.

10. **Preparar e insertar los nuevos registros**: **Único punto donde se insertan las páginas nuevas** con identificadores temporales `{document_id}-staging-p{page_number}` en la tabla `pages`. Estas filas son invisibles para otras conexiones mientras la transacción esté activa.

11. **Actualizar relaciones y metadatos**: Actualizar fila `documents`: `content_sha256`, `file_size`, `modified_at`, `page_count`, `status='indexed'`, `last_processed_at=datetime("now")`.

12. **Actualizar FTS5**: `rebuild_fts_index()` o inserción incremental de nuevas páginas. **Verificar si existen triggers** que lo hagan automáticamente; si no, sincronizar explícitamente.

13. **Comprobar coherencia de los datos afectados**: Validar que el nuevo `content_sha256` sea consistente, que las páginas tengan `page_number` coherente, etc.

14. **Eliminar los registros antiguos solamente después de verificar los nuevos**: **Borrar páginas viejas (IDs originales) *solo después* de confirmar que las nuevas fueron insertadas correctamente y validada la integridad FTS5.**

15. **Registrar el éxito en `processing_runs` dentro de la transacción**: `run_type="update"`, `files_processed=1`, `pages_extracted=N`, `pages_ocr=M`.

16. **Ejecutar COMMIT**.

**Ante cualquier error anterior al COMMIT, ejecutar ROLLBACK**: SQLite garantiza que el estado vuelve al punto de inicio de la transacción. Todas las inserciones dentro de la transacción (páginas nuevas `staging-*`, actualizaciones de `documents`, cambios FTS5) se deshacen automáticamente.

#### Fase C — Registro de fallo (si ocurre un fallo)

17. **Ejecutar ROLLBACK**: Si ocurre un fallo anterior al COMMIT.

18. **Confirmar que la conexión no conserva una transacción activa**: Verificar con `conn.in_transaction` o equivalente.

19. **Registrar el fallo en una transacción independiente**: Dado que la transacción principal ya habrá sido revertida, el registro de fallo debe insertarse en una sesión separada para no formar parte de la transacción revertida.

20. **Conservar el resumen del error sin incluir secretos**: `error_summary` con descripción del fallo, sin datos sensibles.

21. **No alterar el estado válido de la versión anterior**: La versión anterior permanece completamente intacta. Ningún dato se pierde: el sistema vuelve al estado previo al paso 9.

**El registro de éxito no puede insertarse después del COMMIT si el documento afirma que forma parte de la misma transacción**: Si el éxito se registra después del COMMIT, está fuera de la transacción original. El diseño debe garantizar que el registro de éxito ocurra **dentro** de la transacción (antes o junto con COMMIT), o bien como una transacción independiente posterior con claramente marcada como "post-commit".

**El registro de fallo debe ser independiente porque la transacción principal ya habrá sido revertida**: Al haber hecho ROLLBACK, no hay riesgo de que el registro de fallo afecte la integridad de la BD, ya que el estado ya fue revertido.

### 4.3 Decisión técnica sobre staging

Antes de recomendar identificadores temporales `staging-*`, comprobar estáticamente:

- **Clave primaria de `documents`**: `document_id TEXT PRIMARY KEY`.
- **Clave primaria de `pages`**: `page_id TEXT PRIMARY KEY`.
- **Restricciones `UNIQUE`**: Revisar `UNIQUE(document_id, page_number)` en tabla `pages`.
- **Relaciones entre páginas y documentos**: Restricciones `FOREIGN KEY` (aunque no estén activadas por defecto en SQLite, su existencia en el esquema determina el diseño).
- **Estructura y sincronización de `pages_fts`**: Verificar si `pages_fts` es `VIRTUAL` sin `content=`; si requiere inserción explícita o si triggers lo hacen automáticamente.
- **Triggers existentes**: Revisar `sqlite_master` por triggers `AFTER INSERT/UPDATE/DELETE` en `pages` o `documents`.
- **Estrategia de generación de `page_id`**: Verificar cómo se generan actualmente los `page_id` (¿UUID? ¿numérico? ¿`{document_id}-p{number}`?).
- **Restricciones que impidan páginas duplicadas**: Verificar constraints únicas.
- **Mecanismo actual de borrado de páginas**: Revisar `delete_document_pages` en `database.py` y `cli.py`.

**No inventes una estrategia de promoción de IDs**: El diseño debe basarse en el mecanismo real de generación de IDs del sistema.

**Si el esquema permite insertar las nuevas páginas manteniendo las anteriores**: Documentar el procedimiento exacto: insertar nuevas con IDs temporales, actualizar `documents`, borrar antiguas, COMMIT.

**Si el esquema no lo permite**: Presentar la modificación de esquema necesaria como propuesta pendiente de implementación y autorización. **No declarar que el staging garantiza atomicidad** hasta haber definido sus relaciones y restricciones.

**No declares que el staging garantiza atomicidad hasta haber definido sus relaciones y restricciones**: La atomicidad depende de que todo lo que deba ser atómico quede dentro de una única transacción BEGIN/COMMIT/ROLLBACK.

### 4.4 Validación de páginas

**No exiges `character_count > 0` para todas las páginas**.

Una página legítimamente vacía no es automáticamente un error. Definir la validación según el tipo de página y el resultado de extracción/OCR:

- **Página digital con texto**: `character_count > 0`, `quality_status = "ok"`.
- **Página escaneada pendiente de OCR**: `character_count = 0`, `quality_status = "empty"` → OCR pendiente.
- **Página legítimamente vacía**: `character_count = 0`, `quality_status = "ok"` (documento técnico, página de cubierta, página en blanco intencional).
- **Página con extracción fallida**: `character_count = 0`, `quality_status = "failed"` → error, requiere atención.
- **Página con OCR fallido**: `character_count = 0`, `quality_status = "ocr_failed"` → OCR no pudo extraer texto.
- **Página con texto de calidad insuficiente**: `0 < character_count < DIGITAL_TEXT_THRESHOLD`, `quality_status = "suspicious"` → OCR recomendado pero no obligatorio.

**El umbral `DIGITAL_TEXT_THRESHOLD` no debe cambiarse sin calibración**: Cambiar el umbral sin un procedimiento de calibración basado en muestras representativas puede introducir más problemas que resolver. Ver sección 6.7.

### 4.5 Recuperación y concurrencia

Documentar los escenarios de error y concurrencia:

- **Si la aplicación se cierra durante la extracción**: Los resultados temporales fuera de la BD se descartan. La BD conserva su estado anterior. No hay riesgo de corrupción since nothing se escribió dentro de la transacción.

- **Si se cierra durante la transacción**: SQLite guarda el estado de la transacción. Al reiniciar la aplicación, la transacción no commitada se revertirá automáticamente al iniciar una nueva conexión, dejando la BD en estado consistente con el último COMMIT.

- **Si se produce un bloqueo SQLite**: Aplicar `PRAGMA busy_timeout` (ej. 30000 ms) para esperar a que se liberen los bloqueos. Si persiste, abortar el procedimiento y registrar error. No forzar COMMIT sobre un bloqueo.

- **Si dos operaciones intentan actualizar el mismo documento**: La segunda operación intentará `BEGIN` y se bloqueará esperando a que la primera termine. Si la primera hace COMMIT, la segunda procederá con los datos actualizados. Si la primera hace ROLLBACK, la segunda procederá con el estado anterior. **No hay corrupción** gracias a las bloqueos nativos de SQLite.

- **Cómo se evita que una búsqueda vea datos parciales**: Durante la transacción, las páginas nuevas con IDs `staging-*` son invisibles para otras conexiones (SQLite las mantiene en una tabla interna solo para la transacción activa). Solo después de COMMIT se hacen visibles. Las búsquedas durante la transacción verán el estado anterior.

- **Cómo se recuperan archivos provisionales externos**: Si la operación falla antes de COMMIT, los archivos provisionales en memoria/archivo temporal se descartan. No hay persistencia de datos parciales fuera de la BD.

- **Cómo se evita que se dejen registros huérfanos**: El diseño transaccional garantiza que, o todas las operaciones se completan (COMMIT), o ninguna se aplica (ROLLBACK). No quedan "mitad de páginas nuevas" ni "mitad de registros viejos". La versión anterior es siempre recuperable.

No introduzcas mecanismos de concurrencia complejos sin justificar su necesidad: Las bloqueos nativas de SQLite y el patrón transaccional descrito son suficientes para la mayoría de los casos de uso de una aplicación desktop.

## 5. Estrategia de Integridad Transaccional (R1 y R5 consolidados)

### 5.1 Problema consolidado

Los riesgos R1 y R5 se consolidan en un único problema principal de integridad de datos: **en el flujo `cmd_update`, la eliminación de páginas derivadas ocurre antes de validar la nueva extracción, sin mecanismo de staging transaccional.** Si la extracción falla, el documento queda en estado inconsistente: sin páginas antiguas ni nuevas, sin índice FTS5, y con metadatos potencialmente corruptos.

### 5.2 Procedimiento seguro de actualización (patrón de 7 pasos atómicos)

El procedimiento correcto debe seguir esta secuencia obligatoria. **Extracción y validación de contenido ocurren fuera de la transacción SQLite; la transacción abarca solo la sustitución y confirmación de datos.**

1. **Detectar cambio:** Comparar fingerprint SHA-256 calculado del archivo PDF fuente contra `content_sha256` almacenado en `documents`. Si distinto, marcar como `modificado`.

2. **Extraer y validar contenido fuera de transacción:**
   - Ejecutar `extract_pdf(fp, use_ocr=use_ocr)` sobre el PDF fuente **fuera de cualquier sesión de escritura SQLite**.
   - Si `extract_pdf()` lanza excepción (PDF dañado, protegido, vacío): abortar inmediatamente. **No se han tocado registros de BD.** El documento conserva su estado anterior. Finalizar procedimiento.
   - Si la extracción tiene éxito, almacenar temporalmente los resultados en memoria o archivo provisional (fuera de la BD). **No insertar nada en `pages`, `pages_fts` ni `documents` aún.**

3. **Validar resultados extraídos (fuera de transacción):**
   - Verificar `character_count > 0` en todas las páginas extraídas (umbral configurable `DIGITAL_TEXT_THRESHOLD`, default 10). Páginas con `character_count = 0` son legítimamente vacías y no constituyen error.
   - Confirmar que `quality_status` no sea `"failed"` en todas las páginas.
   - Validar que `content_sha256` del nuevo contenido coincida con fingerprint calculado del archivo fuente.
   - Si la validación falla en cualquier paso: abortar procedimiento. **No se han insertado registros definitivos.** El documento conserva su estado anterior. Finalizar procedimiento.

4. **Iniciar transacción SQLite para sustitución atómica:**
   - `conn.execute("BEGIN")` o `conn.execute("BEGIN TRANSACTION")`.
   - **En este punto, y solo aquí, insertar las páginas nuevas** con identificadores temporales `{document_id}-staging-p{page_number}` en la tabla `pages`. Estas filas son invisibles para otras conexiones mientras la transacción esté activa.
   - Actualizar fila `documents`: `content_sha256`, `file_size`, `modified_at`, `page_count`, `status='indexed'`, `last_processed_at=datetime('now')`.
   - Mover páginas de staging a registro definitivo: los `page_id` nuevos pasan a ser definitivos (mantener registros antiguos hasta confirmar éxito).
   - Actualizar índice FTS5: `rebuild_fts_index()` o inserción incremental de nuevas páginas.
   - **Borrar páginas viejas *solo después* de confirmar que las nuevas fueron insertadas correctamente y validada la integridad FTS5.**

5. **Confirmar la transacción únicamente si todas las operaciones son satisfactorias:**
   - Ejecutar `conn.execute("COMMIT")`.
   - Registrar operación exitosa en `processing_runs` con `run_type="update"`, `files_processed=1`, `pages_extracted=N`, `pages_ocr=M`.
   - Registrar `content_sha256` nuevo en `artifacts` si aplica.

6. **Ante un error, ejecutar rollback y conservar la versión anterior:**
   - Ejecutar `conn.execute("ROLLBACK")`.
   - **Consecuencia:** Todas las inserciones dentro de la transacción (páginas nuevas `staging-*`, actualizaciones de `documents`, cambios FTS5) se deshacen automáticamente. SQLite garantiza que, al hacer rollback, el estado de la BD vuelve al punto de inicio de la transacción.
   - El registro `documents` conserva los valores anteriores a la transacción (content_sha256, page_count, status).
   - Registrar operación fallida en `processing_runs` con `error_summary` describiendo la falla.
   - **La versión anterior permanece completamente intacta.** Ningún dato se pierde: el sistema vuelve al estado previo a la paso 4.

7. **Registrar la operación y su resultado:**
   - Insertar fila en `processing_runs` independientemente del resultado.
   - Si éxito: `status='completed'`.
   - Si fallo: `status='failed'`, `error_summary` con descripción.

## 5. Corregir integralmente backups y restauración

### 5.1 Backup SQLite

Utiliza como mecanismo preferente la API nativa `sqlite3.Connection.backup()`.

Aclara correctamente que esta API crea una copia consistente de la base de datos y no implica copiar indiscriminadamente los archivos WAL y SHM.

No describas `BEGIN IMMEDIATE` como requisito universal para generar un backup.

No presentes `shutil.copy2()` del `.db` como procedimiento universalmente seguro.

El checkpoint WAL puede describirse como alternativa únicamente si se especifican las condiciones de coordinación y cierre de conexiones necesarias.

### 5.2 Verificación

El backup debe comprobase mediante:

- `PRAGMA integrity_check`.
- `PRAGMA foreign_key_check`, cuando las relaciones estén definidas.
- Consultas básicas para verificar que la base es utilizable.
- Prueba de restauración en un directorio temporal aislado.

Distingue integridad estructural de integridad referencial.

Si la base ya contiene inconsistencias históricas, no declares automáticamente que un backup es inválido: documenta el estado previo y evita que una operación de restauración introduzca una pérdida adicional.

### 5.3 Restauración

Define el procedimiento real:

1. Detener o coordinar los escritores.
2. Cerrar las conexiones de la base afectada.
3. Evitar que queden escritores activos durante la sustitución.
4. Gestionar los archivos WAL/SHM y el estado de journaling.
5. Restaurar la copia verificada.
6. Reabrir la base.
7. Ejecutar verificaciones de integridad.
8. Registrar el resultado en el `audit_log` de Tech Cyan.

No afirmes que basta con copiar el `.db` encima de una base activa.

Distingue recuperación automática por rollback de recuperación mediante restauración desde backup.

### 5.4 Clasificación de operaciones

Establece una clasificación única:

| Operación | Riesgo | Backup | Confirmación explícita |
|---|---|---|---|
| Consultas y diagnóstico | Ordinario | No | No |
| Actualización de documentos | Alto riesgo | Sí | Según alcance y política de operación |
| Procesamiento OCR | Alto riesgo si modifica datos persistentes | Sí, si la operación modifica datos y no es fácilmente reversible | Según impacto |
| Reconstrucción FTS5 | Alto riesgo | Sí, si sustituye o reconstruye el índice | Según impacto |
| Eliminación de índice | Destructivo | Sí | Sí |
| Limpieza de datos derivados | Destructivo | Sí | Sí |
| Migración de esquema | Destructivo o alto riesgo según migración | Sí | Sí, antes de ejecutar |

Explica qué ocurre cuando una operación aparentemente reversible puede causar pérdida de información.

No clasifiques de forma contradictoria la misma operación en distintas secciones.

La política `safe` debe prevalecer.

### 6.1 Estrategia de rutas inyectables (R2)

Todas las rutas absolutas hardcodeadas deben eliminarse del código fuente y sustituirse por un sistema de configuración inyectable con tres niveles de prioridad:

1. **Primera opción:** Variable de entorno explícita.
   - `DOC_COLLECTION_SOURCE` → ruta de la colección PDF.
   - `DOC_WORKSPACE_ROOT` → raíz de trabajo (deriva `DATABASE_PATH`, `EXTRACTED_DIR`, `LOGS_DIR`, `REPORTS_DIR`).
   - `TESSERACT_CMD` → ejecutable Tesseract.
   - `TESSDATA_PREFIX` → datos de idioma Tesseract.
   - `OCR_LANGUAGES` → códigos de idioma (default `"spa"`).
   - `OCR_ENABLED` → `"1"` o `"0"`.
   - `DIGITAL_TEXT_THRESHOLD` → entero umbral calidad texto digital.

2. **No hay detección automática de colección:**  
   **La política `preserve` obliga a conservar la ubicación documental existente.** No se realizará detección automática de `%USERPROFILE%\Documentos` ni de ninguna otra carpeta del sistema como colección PDF substituta.  
   - Si existe una ruta configurada y es válida, utilizarla.  
   - Si existe una ruta configurada pero no existe, informar y solicitar intervención del usuario.  
   - Si no hay ruta configurada, solicitar selección expresa al usuario antes de escanear.  
   - No escanear carpetas alternativas automáticamente.  
   - No crear una colección sustituta.  
   - No mover ni copiar PDFs originales como parte de la integración.  
   - No cambiar automáticamente la ruta de una base de datos existente.  
   - No crear otro workspace cuando ya existe uno configurado.

3. **Tercera opción:** Valor por defecto portable (directorio relativo al ejecutable).
   - Solo si ni la variable ni la (ausencia de) detección automática encuentran una ruta válida.
   - Directorio relativo al ejecutable PyInstaller onedir o al script actual.
   - Nunca rutas absolutas de usuario (`C:\Users\...`, `D:/aliat/...`).

**Funciones auxiliares requeridas:**
- `validate_collection_path(path: Path) -> bool`: retorna `False` si `path` es `None` o no es directorio existente. **Debe llamarse antes de usar cualquier ruta de colección.**
- `detect_collection_source_fallback() -> Path | None`: **no** intenta detectar colección en `%USERPROFILE%\Documentos` ni en otras rutas del sistema como default. Solo puede usarse como herramienta de diagnóstico explícito solicitud del usuario. Documentar que la política `preserve` prohíbe la selección automática de colección.
- `get_collection_source() -> Path | None`: devuelve `COLLECTION_SOURCE` (puede ser `None` si no configurada). *Política:* el caller debe verificar que no sea `None` antes de usarse.
- `get_workspace_root() -> Path | None`: idéntico patrón para `WORKSPACE_ROOT`.

**Configuración `config.py` después de la remediación:**
```python
# Sin rutas absolutas hardcodeadas de usuario
COLLECTION_SOURCE = (
    Path(os.getenv("DOC_COLLECTION_SOURCE")) if os.getenv("DOC_COLLECTION_SOURCE") else None
)
WORKSPACE_ROOT = (
    Path(os.getenv("DOC_WORKSPACE_ROOT")) if os.getenv("DOC_WORKSPACE_ROOT") else None
)
# Sin defaults de usuario para Tesseract
TESSERACT_CMD = os.getenv("TESSERACT_CMD")  # Ningún default; obligatorio configurar o detectar
TESSDATA_PREFIX = os.getenv("TESSDATA_PREFIX")  # Ningún default; obligatorio configurar o detectar
# Umbral configurable
DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))
# Resto de configuración...
```

### 6.2 Estrategia configurable y portable para Tesseract (R3)

**Objetivo:** Hacer `TESSERACT_CMD` y `TESSDATA_PREFIX` totalmente configurables por entorno, con detección automática opcional y errores explícitos cuando no estén disponibles.

**Componentes:**
1. **`TESSERACT_CMD`:**
   - Variable de entorno `TESSERACT_CMD`. Sin valor por defecto en código.
   - Función auxiliar `detect_tesseract_executable() -> Path | None`:
     - Si `TESSERACT_CMD` definida y archivo ejecutable existe → usarla.
     - Si no definida, buscar `tesseract` en `PATH` del sistema ( `subprocess.run(["which", "tesseract"]` o equivalente).
     - Si encontrado, opcionalmente usarla (documentar que esto es desarrollo/debug, no producción por defecto).
     - Si no encontrado, retornar `None`.
   - `is_available() -> bool` debe retornar `False` si `TESSERACT_CMD` es `None` y la detección automática está desactivada o falló.

2. **`TESSDATA_PREFIX`:**
   - Variable de entorno `TESSDATA_PREFIX`. Sin valor por defecto en código.
   - Si no está definida, intentar `./tessdata` relativo al directorio de trabajo o ejecutable.
   - Si no existe y no está definida, `is_available()` retorna `False`.

3. **`OCR_LANGUAGES`:**
   - Variable `OCR_LANGUAGES` con valor por defecto `"spa"`.
   - Permitir múltiples idiomas separados por `+` (ej. `"spa+eng"`).
   - No tener defaults implícitos que oculten la falta de configuración.

4. **`OCR_ENABLED`:**
   - Variable `OCR_ENABLED` con `"1"` o `"0"`, sin default implícito en código.
   - Si `"0"`, OCR está deshabilitado intencionalmente. **No marcar todas las páginas como `ocr_required`**. Las páginas mantienen su estado natural según extracción/OCR previo. Si no hay texto digital (`character_count = 0`) y OCR está deshabilitado, `quality_status` quedará `"empty"` (página legítimamente vacía u OCR pendiente por configuración futura), pero **no** se forzó la etiqueta `ocr_required` sobre páginas que sí tienen texto.

5. **Estados diferenciados de OCR:**
   - **OCR pendiente:** Página sin texto extraído aún, awaiting OCR processing. `quality_status = "empty"` o `"suspicious"`.
   - **OCR deshabilitado intencionalmente:** Configuración `OCR_ENABLED = "0"`. OCR no se ejecutará para estas páginas. `quality_status` refleja el estado de la extracción previa (puede ser `"empty"` si no hay texto, o el resultado de extracción anterior).
   - **OCR no disponible:** Tesseract no configurado o ejecutable no encontrado (`is_available() → False`). El sistema no intenta OCR y registra el estado correspondiente.
   - **OCR completado:** Extracción exitosa de texto. `character_count > 0`, `quality_status = "ok"`.
   - **OCR fallido:** Tesseract no pudo extraer texto de una página escaneada. `character_count = 0`, `quality_status = "ocr_failed"`.

**No degradar silenciosamente cuando Tesseract no esté disponible:**
- `is_available()` debe fallar de forma explícita (retornar `False`) cuando `TESSERACT_CMD` no esté definida o el ejecutable no sea encontrado.
- **Nunca** degradar a un modo donde OCR se "apague silenciosamente". El usuario debe ser consciente de que OCR no estará disponible y configurar las variables correspondientes.

**Compatibilidad con distribución PyInstaller onedir:**
- Al empaquetar con PyInstaller, las variables de entorno deben definirse en el entorno que ejecuta el ejecutable, no incrustadas en el código.
- Función auxiliar `bundle_dir() -> Path` que retorne el directorio temporal o instalación del paquete onedir, para búsquedas relativas de `tessdata` si es necesario.
- Documentar que `TESSERACT_CMD` y `TESSDATA_PREFIX` deben establecerse en el entorno del usuario final, no en el código fuente.

6. **`TESSERACT_CMD`:**
   - Variable de entorno `TESSERACT_CMD`. Sin valor por defecto en código.
   - Función auxiliar `detect_tesseract_executable() -> Path | None`:
     - Si `TESSERACT_CMD` definida y archivo ejecutable existe → usarla.
     - Si no definida, buscar `tesseract` en `PATH` del sistema (`subprocess.run(["which", "tesseract"]` o equivalente).
     - Si encontrado, opcionalmente usarla (documentar que esto es desarrollo/debug, no producción por defecto).
     - Si no encontrado, retornar `None`.
   - `is_available() -> bool` debe retornar `False` si `TESSERACT_CMD` es `None` y la detección automática está desactivada o falló.

7. **`TESSDATA_PREFIX`:**
   - Variable de entorno `TESSDATA_PREFIX`. Sin valor por defecto en código.
   - Si no está definida, intentar `./tessdata` relativo al directorio de trabajo o ejecutable.
   - Si no existe y no está definida, `is_available()` retorna `False`.

8. **`OCR_LANGUAGES`:**
   - Variable `OCR_LANGUAGES` con valor por defecto `"spa"`.
   - Permitir múltiples idiomas separados por `+` (ej. `"spa+eng"`).
   - No tener defaults implícitos que oculten la falta de configuración.

---

## 7. Separación Arquitectónica (E1 vs E2)

### 7.1 Distinción clara entre fases

Para evitar superposiciones y asegurar progreso ordenado, las fases E1 y E2 tienen límites definidos:

| Aspecto | Fase E1 | Fase E2 |
|---|---|---|
| **Objetivo principal** | Integridad de datos, rutas configurables, OCR, seguridad de actualización. | Desacoplamiento CLI, servicios de aplicación, eliminación dependencias presentación. |
| **Riesgos abordados** | R1 (pérdida páginas), R2 (rutas hardcodeadas), R3 (Tesseract), R7 (sin FK), R9 (umbral). | R4 (`sys.exit()`/`print()`), progreso/cancelación estructurada, DTOs, JobManager, adapter GUI. |
| **Modificaciones de código** | Corrección de patrones transaccionales, rutas, configuración OCR. | Reemplazar `print()` por retornos `OperationResult`, `sys.exit()` por excepciones, nuevos DTOs, JobManager. |
| **Resultado esperado** | Motor capaz de actualizar documentos sin perder datos, configurable en distintas máquinas, OCR operable con configuración correcta. | Adapter `DocumentEngineExecutor` reutilizable desde GUI CustomTkinter, con jobs, progreso, cancelación, salidas estructuradas. |
| **Orden** | E1 debe completarse y verificarse antes de iniciar E2. | No se puede comenzar E2 mientras E1 tenga tareas pendientes críticas. |

### 7.2 Por qué E1 antes que E2

- **Dependencia lógica:** Los problemas de E2 (`sys.exit()`, `print()`) son inherentes a la capa de presentación y no afectan la integridad transaccional de E1. Corregir E2 primero no resuelve R1 (pérdida de páginas) en el flujo `cmd-update`.
- **Prioridad de negocio:** La integridad de datos (E1) es un requisito previo para cualquier integración. No sirve tener una GUI bonita si el motor puede borrar datos inadvertidamente.
- **Ambito:** E1 toca capas de infraestructura y aplicación (BD, configuración, OCR). E2 toca la capa de presentación y servicios. Pueden paralelizarse parcialmente (ej. corregir rutas en E1 mientras se diseñan DTOs en E2), pero la autorización formal requiere E1 completado primero.

**Decision:** Mantener E1 y E2 separadas en el plan, con hito de "E1 completado y verificado" como prerequisito para "E2 comenzado".

### 7.3 R4 exclusivo de E2

R4 (`sys.exit()` y funciones CLI) pertenece exclusivamente a la fase E2. No debe aparecer como riesgo que E1 tiene que resolver.

E1 se centra en integridad transaccional, rutas, OCR y seguridad SQLite. El eliminación de `sys.exit()` de las funciones expuestas del adapter es una tarea E2, no E1.

---

## 8. Contrato Definitivo DocumentEngineAdapter

Los 12 métodos contractuales con responsabilidad, parámetros, resultados esperados y fase de incorporación:

| # | Método | Responsabilidad | Parámetros | Resultado Expected | Errores Posibles | Fase |
|---|---|---|---|---|---|---|
| **1** | `get_engine_status` | Retornar estado consolidado del motor (BD, configuración, OCR, salud operación). | Ninguna (usa BD interna). | `OperationResult[EngineStatusDTO]` | `DatabaseError` si BD inaccesible. | E1 |
| **2** | `scan_collection` | Escanear colección PDF y reportar archivos detectados. | `source: Optional[Path]` (opcional). Si None, usar `collection_root` de meta. | `OperationResult[List[DocumentDTO]]` | `CollectionPathError` si ruta no existe o no es directorio. | E1 |
| **3** | `update_collection` | Procesar nuevos/modificados en colección con staging seguro. | `source: Optional[Path]`, `use_ocr: bool`. | `OperationResult[UpdateReportDTO]` | `ExtractionError` si falla pypdf/pymupdf, `StagingError` si falla transacción. | E1 |
| **4** | `search_documents` | Buscar documentos con evidencia e interpretación. | `question: str`, `limit: int` (opcional, default 12). | `OperationResult[QueryResultDTO]` | `InvalidQuestionError` si pregunta vacía, `ProviderError` si síntesis falla. | E2 |
| **5** | `get_document` | Obtener metadatos y páginas de un documento. | `document_id: str`. | `OperationResult[DocumentDTO]` | `DocumentNotFoundError` si ID no existe. | E2 |
| **6** | `rebuild_search_index` | Reconstruir índice FTS5 desde datos existentes. | Ninguna. | `OperationResult[int]` (cantidad filas indexadas). | `FtsRebuildError` si falla SQL. | E0 (idéntica) |
| **7** | `process_pending_ocr` | Aplicar OCR a páginas sin texto digital útil. | `limit: Optional[int]`, `dpi: int` (opcional, default 200). | `OperationResult[List[OcrPageResultDTO]]` | `OcrNotAvailableError` si Tesseract no configurado, `PageExtractionError` por página. | E1 |
| **8** | `ask_document_question` | Consulta con evidencia e interpretación (mock/api). | `question: str`, `provider: Optional[str]` (mock|api|None). | `OperationResult[QueryResultDTO]` | `InvalidQuestionError`, `ProviderError`, `NoEvidenceError`. | E2 |
| **9** | `validate_engine` | Comprobar integridad del índice y consistencia. | Ninguna. | `OperationResult[ValidationReportDTO]` | Ningún error esperado (solo reporte). | E1 |
| **10** | `remove_document_index` | Eliminar índice de un documento (páginas + FTS5). | `document_id: str`. | `OperationResult[bool]` (True = éxito). | `DocumentNotFoundError`, `FtsDeleteError`. | E2 |
| **11** | `clean_derived_data` | Limpiar datos derivados con backup-confirmar-restore. | Ninguna (operación destructiva requiere confirmación explícita). | `OperationResult[CleanupReportDTO]` | `BackupError`, `CleanupError` si falla validación posterior. | E3 (nueva) |
| **12** | `reindex_collection` | Reindexación completa: rebuild FTS5 + re-OCR pendiente + validación. | Ninguna. | `OperationResult[ReindexReportDTO]` | Cualquier error de los sub-métodos combinados. | E3 (nueva) |

**DTOs definidos (firma mínima):**

```python
class OperationResult:
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    error: Optional[str] = None

class EngineStatusDTO:
    documents_total: int
    pages_total: int
    pages_with_text: int
    fts_index_rows: int
    ocr_available: bool
    provider_mode: str
    collection_root: Optional[str]
    tesseract_available: bool

class DocumentDTO:
    document_id: str
    relative_path: str
    filename: str
    content_sha256: str
    file_size: int
    page_count: int
    status: str
    last_processed_at: str

class UpdateReportDTO:
    documents_processed: int
    pages_extracted: int
    pages_ocr: int
    pages_failed: int
    staging_used: bool
    rollback_occurred: bool
    error_summary: Optional[str]

class QueryResultDTO:
    question: str
    answer: str
    provider: str
    evidence: List[Dict[str, Any]]
    citations: Dict[str, Any]
    warnings: List[str]
    error: Optional[str]

class ValidationReportDTO:
    problems_total: int
    integrity_sqlite: str
    foreign_key_issues: int
    fts_coherence: bool
    documents_without_hash: int
    quality_distribution: Dict[str, int]
    pending_ocr_pages: int

class OcrPageResultDTO:
    page_id: str
    document_id: str
    page_number: int
    text: str
    quality: bool
    error: Optional[str]
    ocr_engine: Optional[str]
    ocr_language: Optional[str]
    ocr_version: Optional[str]

class CleanupReportDTO:
    items_removed: int
    backup_available: bool
    restoration_possible: bool
    errors: List[str]

class ReindexReportDTO:
    fts_reindexed: int
    ocr_pages_processed: int
    validation: ValidationReportDTO
```

**Políticas aplicables a todos los métodos:**
- `preserve`: ningún método adapter toca archivo PDF fuente. Solo lee contenido.
- `safe`: antes de cualquier operación que modifique BD, el adapter debe verificar que exista backup verifiable (o documentación de que se realizó recientemente). Si falla backup, abortar operación.
- `embedded`: adapter se integra en paquete Tech Cyan, pero `DocumentEngineAdapter` es el único punto de contacto; el motor subyacente sigue siendo independiente.
- Modo por defecto `mock`; modo `api` requiere confirmación explícita (política `safe`).
- Ningún método envía documentos completos a proveedor externo — solo fragmentos de evidencia seleccionados (máx. 12 filas, truncados a 1200 chars cada uno, contexto total 9000 chars).
- Todas las rutas son inyectables por parámetro o configuración (nunca hardcodeadas).
- Las operaciones destructivas (update, clean, remove, reindex) siguen patrón staging+confirmación+rollback (E1).

---

## 9. Seguridad, Backups y Recuperación

### 9.1 Políticas seguridad inalterables

1. **PDF originales solo lectura:** Ningún método adapter debe modificar, renombrar, sovrecribir ni mover archivos PDF fuentes. La política `preserve` obliga a que los PDFs permanezcan inmutables. Cualquier operación que requiera "actualizar" un documento debe usar el patrón de staging/rollback descrito en la sección 5, nunca escribir sobre el archivo fuente.

2. **Dos bases SQLite independientes y flujos de acceso diferenciados:**
   - **Base de datos del motor documental:** `documents.db` (ruta configurable via `DOC_WORKSPACE_ROOT` / `DOC_COLLECTION_SOURCE`). Es el sistema de persistencia propio del motor `agente-documental`. Tiene sus tablas: `documents`, `pages`, `pages_fts`, `meta`, `artifacts`, `processing_runs`.
   - **Base de datos propia de Tech Cyan:** Base independiente con tablas `app_meta`, `settings`, `provider_profiles`, `job_history`, `audit_log`, `schema_migrations`. Es el sistema de persistencia de la aplicación Tech Cyan Desktop Advanced.
   - **Flujo de llamadas oficial:** `UI → Application Services → DocumentEngineAdapter → Document Engine → Engine Repository → Engine SQLite`. La interfaz de usuario de Tech Cyan nunca ejecuta SQL directo sobre la base del motor. La capa de aplicación accede al motor a través de `DocumentEngineAdapter` y sus métodos contractuales.
   - **`DocumentEngineAdapter` es la única frontera de integración:** Es el único punto que coordina lectura/escritura entre las dos bases. El adapter lee del motor (mediante `Repository`) para obtener metadatos, evidencia o estado, y escribe en el motor cuando los métodos contractuales así lo requieren (`update_collection`, `reindex_collection`, `clean_derived_data`, `remove_document_index`). Sin embargo, el adapter **nunca** expone sentencias SQL arbitrarias ni permite que la UI manipule directamente las tablas internas del motor.
   - **Independencia de la base Tech Cyan:** Cualquier escritura relacionada con trabajo, jobs, configuraciones de usuario o historial de la aplicación Tech Cyan debe dirigirse a la base propia de Tech Cyan, no al motor `documents.db`. El motor conserva la responsabilidad de leer y escribir su propia base mediante sus repositorios internos.
   - **Restricción:** Tech Cyan no modifica directamente el esquema interno ni los datos maestros del motor. Cualquier operación que modifique la base del motor debe hacerse a través del `DocumentEngineAdapter`, que aplica los controles de integridad, staging y validación correspondientes.

3. **Secretos fuera del código, logs y SQLite:**
   - `DOC_AI_API_KEY`, `DOC_AI_BASE_URL`, `DOC_AI_MODEL`: solo variables de entorno.
   - `CredentialStore` de Tech Cyan debe leer de Windows Credential Manager, nunca embeded en código.
   - `APIProvider.__init__()` lee `os.getenv()` — compatible siempre que Tech Cyan provea las vars de entorno, no incrusta claves en su código.

4. **No SQL arbitrario, shell arbitrario ni rutas irrestrictas desde UI:**
   - **Adapter:** todos los queries SQL usan paráetrizados (`?`), never f-strings concatenados con entrada de usuario.
   - **Rutas:** todo path recibido como parámetro pasa por `validate_collection_path()` o equivalente antes de usarse.
   - **Shell:** ningún método adapter invoca `subprocess` con entrada del usuario.

5. **No enviar documentos completos a IA por defecto:**
   - `OUTPUT_INSTRUCTIONS` + `evidence_lines` ya garantizan este patrón en el motor actual.
   - **Adapter contract:** `ask_document_question` y `provider.synthesize()` siempre reciben `evidence` (fragmentos truncados) + `instructions`. Nunca `document_path` o `pdf_complete`.
   - **Verificación:** `QueryResultDTO.evidence` lista de dicts con `text` truncado y `refs` (IDs de evidencia), no rutas de archivo.

### 9.2 Backups y recuperación coherente con SQLite

La política de backups debe alinearse con la decisión arquitectónica `safe` y el funcionamiento interno de SQLite, el cual garantiza consistencia mediante WAL (Write-Ahead Logging) y journals. Un backup incorrecto o una restauración inadecuada pueden dejar la base en un estado corrupto o con transacciones pendientes.

#### Clasificación de operaciones por nivel de riesgo

| Nivel | Tipo de operación | Requisito de backup |
|---|---|---|
| **Ordinal** | Lectura, `get_document`, `search_documents`, `get_engine_status`, consultas de diagnóstico. | No requiere backup previo. |
| **Alto riesgo** | `update_collection` (con staging), `reindex_collection`, `remove_document_index`. | Backup verificable obligatorio antes de iniciar. |
| **Destructiva** | `clean_derived_data`, migraciones de esquema que modifiquen columnas o tablas. | Backup verificable obligatorio + confirmación explícita por escrito. |

#### Mecanismo de backup verificable

No se considers un `copy2()` directo del archivo `.db` como procedimiento universalmente seguro, pues SQLite usa archivos WAL y SHM que pueden no estar sincronizados en el instante de la copia. El backup debe garantizar una copia coherente de la base en un punto de instante determinado.

**Pasos para crear un backup verificable:**

1. **Conectar a la BD con modo lecto-solo temporal** (opcional, pero recomendado para bases muy activas):
   - `conn.execute("PRAGMA busy_timeout -> 30000")` para esperar bloqueos.
   - Opcionalmente, `conn.execute("BEGIN IMMEDIATE")` para obtener un lock exclusivo temporal.

2. **Ejecutar la API nativa de copia coherente de SQLite:**
   - `backup = conn.backup(target_db)` donde `target_db` es un objeto `sqlite3.Connection` abierto sobre el archivo de backup.
   - Esto copia el archivo de base de datos, los archivos WAL y SHM en un estado consistente, ya que SQLite asegura que el backup capture el estado al momento en que se inició la operación de backup, no necesariamente al momento en que el archivo termine de copiarse.
   - Alternativa si no se usa la API `backup()`: realizar `conn.execute("PRAGMA wal_checkpoint(FULL)")` antes de copiar el archivo, para asegurar que el WAL esté totalmente aplicado antes de la copia.

3. **Verificar la copia mediante `PRAGMA integrity_check`:**
   - `integrity_result = backup.execute("PRAGMA integrity_check").fetchone()[0]`
   - El resultado debe ser `"ok"`. Si es diferente, el backup está corrupto y debe descartarse.

4. **Verificar relaciones (cuando corresponda):**
   - `fk_result = backup.execute("PRAGMA foreign_key_check").fetchall()`
   - Si `fk_result` no está vacío (tiene filas), hay huérfanas y el backup no es válido.

### 9.2.1 Configuración de `PRAGMA foreign_keys=ON`

Cada conexión `Repository._open()` debe activar explícitamente la integridad referencial mediante:

```python
self.conn.execute("PRAGMA foreign_keys=ON")
```

**Propósito:** Esta configuración hace que SQLite haga cumplir las restricciones de clave foránea definidas en el esquema. Sin ella, las FK son informativas únicamente y SQLite permite datos huérfanos (rows en `pages` con `document_id` que no existen en `documents`).

**Relación con `PRAGMA foreign_key_check`:**
- `PRAGMA foreign_keys=ON` **habilita** el manejo de restricciones en cada conexión
- `PRAGMA foreign_key_check` **valida** que no haya violaciones existentes en la base
- Ambas deben estar presentes para integridad completa: la primera para prevenir futuras violaciones, la segunda para detectar violaciones pasadas

**Fase de implementación:** Este cambio pertenece a la fase E1-II (Integridad y Seguridad) y es un requisito previo para TEST-021 y TEST-022.

**Comportamiento esperado:**
- **Con `PRAGMA foreign_keys=ON`:** INSERT/UPDATE que violen FK lanzan `sqlite3.IntegrityError`, impidiendo datos huérfanos
- **Sin `PRAGMA foreign_keys=ON`:** Operaciones exitosas, pero integridad referencial no garantizada por SQLite; el código debe depender de lógica de aplicación (JOINs manuales) para consistencia
- **TEST-021:** Verifica el esquema actual — `CREATE TABLE` no declara `FOREIGN KEY` constraints, pero el código usa `JOIN` manuales para integridad
- **TEST-022:** Distingue inconsistencias que surgirían si se activaran las FK — datos huérfanos por diseño vs. por bug vs. datos consistentes

**Integración con procedimiento backup (Sección 9.2):**
- Cuando `PRAGMA foreign_keys=ON` está activo, `PRAGMA foreign_key_check` retornará violaciones reales si los datos las tienen
- El procedimiento de backup (paso 4, línea 647-648) debe ejecutarse **con** `PRAGMA foreign_keys=ON` activo para validar integridad completa
- Si `foreign_key_check` tiene resultados y `foreign_keys` está ON, el backup es inválido y debe descartarse (no proceder con operación destructiva)
   - Copiar el archivo de backup a una ubicación de `tmp_path`.
   - Abrir la base de copia y ejecutar `PRAGMA integrity_check` nuevamente.
   - Ejecutar una consulta simple (ej. `SELECT COUNT(*) FROM documents`) para verificar que la base sea usable.
   - **Si falla la validación en cualquier paso, descartar el backup y generar uno nuevo.**

6. **Conservación del backup:**
   - Mantener el archivo de backup activo hasta que la validación posterior a la operación haya finalizado exitosamente.
   - Solo después de confirmado el éxito de la operación y su validación, el backup puede ser eliminado o archivado según la política de retención organizacional.

7. **Horario de backup: NO basado en tiempo arbitrario**
   - **No considerar suficiente** un backup de hasta 24 horas para autorizar automáticamente una operación destructiva.
   - El backup debe haberse creado **inmediatamente antes** de iniciar la operación de alto riesgo o destructiva. El timestamp del archivo de backup debe registrarse en el `audit_log`.

#### Requisitos obligatorios

- **Backup reciente antes de cada operación destructiva o de alto riesgo:** El adapter debe crear el backup en el momento mismo que se va a ejecutar la operación, no horas antes.
- **No autorización automática por antigüedad:** Un backup de 24 horas o más no autoriza automáticamente una operación. Si el backup es antiguo, debe crearse uno nuevo.
- **Abortado seguro si el backup o su validación fallan:** Si `PRAGMA integrity_check` no retorna `"ok"` o `PRAGMA foreign_key_check` tiene resultados, el adapter debe lanzar `BackupError` y abortar la operación. No proceder bajo ninguna circunstancia.
- **Validación posterior a la operación:** Después de COMMIT (o rollback), ejecutar `validate_engine()` para asegurar que la base sigue coherente. Si la validación falla, disponer del backup y restaurarlo.
- **Registro en audit_log:** Toda operación de alto riesgo o destructiva debe registrar en `audit_log`:
  - `backup_path` (ruta del archivo de backup creado).
  - `backup_timestamp` (cuando fue creado).
  - `backup_integrity_check` (resultado de `PRAGMA integrity_check`).
  - `backup_foreign_key_check` (resultado de `PRAGMA foreign_key_check`, si aplica).
  - `result` (success/failed).

#### Patrón backup-confirmar-restore para operaciones destructivas (ej. `clean_derived_data`)

1. **Crear backup verificable** (pasos 1-6 arriba). Si falla cualquier paso, lanzar `BackupError` y abortar.
2. **Confirmación explícita:** Solicitar al usuario: "¿Desea proceder con la operación destructiva? Se realizará backup verificable antes. Respuesta requerida: afirmativa por escrito." Obtener respuesta afirmativa por escrito (diálogo UI o comando explícito).
3. **Ejecutar operación** sobre la base original.
4. **Validación posterior:** Ejecutar `validate_engine()` para comprobar que la BD sigue coherente después de la operación.
5. **Restaure si falla:** Si la validación posterior falla en cualquier punto, restaurar desde el backup verificado y registrar error. No proceder si la integridad se vio comprometida.
6. **Registrar resultado en audit_log:** Incluir `result` (success/failed) y `restoration_performed` (booleano).

**Nota sobre `PRAGMA foreign_key_check`:** No se ejecuta en todas las operaciones ordinarias, solo en operaciones de alto riesgo o destructivas que modifiquen relaciones de tabla. Para escrituras ordinarias, este paso puede omitirse por rendimiento, pero debe incluirse en el diseño para operaciones que toquen las tablas con foreign keys.

---

## 10. Plan de Pruebas

### 10.1 Marco de trabajo

- **Framework:** `pytest` con fixture `tmp_path` para cada test.
- **Base de datos:** SQLite en memoria o DB temporal por test (`db_path = str(tmp_path / "test_documents.db")`).
- **Proveedor IA:** `MockProvider` para todas las pruebas (sin costo, sin red).
- **PDFs sintéticos:** Crear PDFs vacíos o con texto mínimo usando `pypdf`/`pymupdf`, **nunca** usar PDFs reales de colección.
- **Mocking:** `unittest.mock.patch` para `is_available()`, `TESSERACT_CMD`, etc., cuando sea necesario.

### 10.2 Casos de prueba (TEST-001 a TEST-014, ampliados)

| Caso | Descripción | Módulo | Expected |
|---|---|---|---|
| **TEST-001** | Actualización exitosa de documento nuevo | `update_collection` con PDF válido con texto | `OperationResult.success=True`, páginas y metadatos insertados, FTS5 actualizado. |
| **TEST-002** | Fallo de extracción documentado | PDF corrupto o protegido | `OperationResult.success=False`, `error="ExtractionError"`, BD conserva registro anterior (rollback). |
| **TEST-003** | Rollback en actualización fallida | Extracción falla después de staging | `OperationResult.success=False`, BD retorna estado anterior a staging (páginas y metadatos intactos). |
| **TEST-004** | Documento dañado (PDF con error) | `pymupdf.open()` lanza excepción | `OperationResult.success=False`, error registrado, documento marcado como `status="error"`. |
| **TEST-005** | Documento sin texto digital | PDF con páginas sin texto extraíble (cc=0) | OCR se propone para páginas pendientes; `quality_status` → `"ocr_required"`. |
| **TEST-006** | OCR pendiente procesado | Páginas con `quality_status="empty"` o `"suspicious"` | `process_pending_ocr` aplica OCR, actualiza `text`, `quality_status`, sincroniza FTS5. |
| **TEST-007** | Reconstrucción FTS5 | Después de modificar páginas directamente en BD | `rebuild_search_index` reconstruye `pages_fts` coherente con tabla `pages`. |
| **TEST-008** | Cancelación de trabajo | Job en ejecución, usuario cancela | Worker verifica bandera `cancelled` y detiene voluntariamente; BD queda en estado consistente. |
| **TEST-009** | Ruta de colección inexistente | `scan_collection` con path que no existe | `OperationResult.success=False`, `error="CollectionPathError"`, no intenta leer PDFs. |
| **TEST-010** | Recuperación ante error de OCR | Tesseract lanza excepción en página concreta | `process_pending_ocr` captura error, marca `error_message` en página, continúa con resto; no falla todo el lote. |
| **TEST-011** | Validación de integridad limpia | BD recién creada, todos los datos coherentes | `validate_engine` retorna `problems_total=0`, `integrity_sqlite="ok"`. |
| **TEST-012** | Validación con inconsistencias | BD con FTS5 desactualizado (más filas que `pages` con texto) | `validate_engine` detecta `fts_coherence=False`, reporta problema, `problems_total>0`. |
| **TEST-013** | Mock provider sin síntesis | `ask_document_question` con `provider="mock"` | `result.provider="mock"`, `result.answer` declara "no hubo síntesis por IA", cita solo informativa. |
| **TEST-014** | Límites de evidencia y contexto | Pregunta que encuentra más de 8 evidencias o >9000 chars de contexto | `result.warnings` incluye cortes, `result.evidence` limitado a `AI_MAX_EVIDENCE`, texto truncado respetando presupuesto. |

### 10.3 Casos adicionales para esta actualización

- **TEST-015:** Fallo durante la extracción después de staging. Verificar que `ROLLBACK` devuelve la BD al estado previo al staging (páginas antiguas conservadas).
- **TEST-016:** Fallo durante la preparación de staging. Verificar que no se inserten páginas definitivas si la preparación falla.
- **TEST-017:** Fallo durante la sustitución transaccional. Verificar que `COMMIT` no se ejecute si alguna validación falla en el paso 3.
- **TEST-018:** Fallo al actualizar FTS5. Verificar que la coherencia FTS5 se mantenga o se revierta si falla la actualización del índice.
- **TEST-019:** Rollback completo. Simular error en múltiples pasos y verificar que la BD quede en estado consistente con los datos originales.
- **TEST-020:** Conservación de la versión anterior. Verificar que, después de un rollback, `get_document(document_id)` retorne los valores anteriores a la operación fallida.
- **TEST-021:** Activación de claves foráneas. Verificar que `PRAGMA foreign_keys = ON` esté configurado en cada conexión `Repository` y que operaciones de `UPDATE` y `DELETE` respeten relaciones.
- **TEST-022:** Verificación de integridad referencial. Ejecutar `PRAGMA foreign_key_check` y comprobar que no haya resultados (significa que no hay huérfanas).
- **TEST-023:** OCR sin ejecutable disponible. Simular `is_available()` → `False` y verificar que `process_pending_ocr` retorne `OcrNotAvailableError` y no intente procesar páginas.
- **TEST-024:** OCR sin datos de idioma. Simular `TESSDATA_PREFIX` no definida y verificar error explícito, no degradación silenciosa.
- **TEST-025:** Migración fallida. Simular una migración de esquema que falle y verificar que haya mecanismo de recuperación (rollback a versión anterior).
- **TEST-026:** Restauración desde backup. Verificar que, después de una operación destructiva fallida, se pueda restaurar desde backup y `validate_engine` reporte consistencia.
- **TEST-027:** Cancelación de tareas largas. Verificar que un job en progreso pueda cancelarse mediante bandera `cancelled` y el worker se detenga voluntariamente sin corruptar la BD.
- **TEST-028:** Protección de PDF originales. Verificar que, después de múltiples operaciones `update_collection`, los PDFs fuente sigan intactos (mismo hash, mismas páginas).

**Prohibiciones en pruebas:**
- ✗ Prohibido: ejecutar tests contra colección documental real.
- ✗ Prohibido: usar bases SQLite persistentes en directorios de proyecto.
- ✗ Prohibido: acceder a rutas absolutas `C:\Users\Tx@mxm\...` o `D:/aliat/...` en tests.
- ✗ Prohibido: llamar `sys.exit()` en código de test.
- ✗ Prohibido: enviar documentos reales a proveedor API en tests.

---

## 11. Fases E0–E5

| Fase | Objetivo | Dependencias | Riesgo si se salta | Estado |
|---|---|---|---|---|
| **E0** | Revisión cruzada y plan de remediación (este documento). | Ninguna | Sin rumbo definido; riesgo de trabajar sin prioridades claras. | ✅ Complegada |
| **E1** | Integridad transaccional, rutas configurables, OCR, claves foráneas y seguridad de datos. | E0 (lista de riesgos consolidada). | Problemas de pérdida de datos, rutas no portables, OCR inusable, inconsistencias BD. | ⏳ Pendiente autorización explícita |
| **E2** | Desacoplamiento CLI y servicios, DTOs, JobManager, progreso/cancelación. | E1 completado (operaciones sin `print`/`sys.exit`, rutas configurables). | GUI imposible de integrar; lógica atrapada en capa consola; riesgos E1 no resueltos. | ⏳ Por iniciar |
| **E3** | Implementación completa del contrato `DocumentEngineAdapter` (12 métodos). | E1, E2 (métodos con contratos definidos y sin riesgos críticos). | Adapter incompleto o con riesgos críticos sin corregir; bloqueo de integración. | ⏳ Por iniciar |
| **E4** | Pruebas aisladas y validación con batería TEST-001 a TEST-028. | E3 (adapter con métodos contractuales). | Riesgo de regressión; cambios sin validación; tests que pasan sobre datos falsos. | ⏳ Por iniciar |
| **E5** | Preparación integración con interfaz Tech Cyan (UI CustomTkinter) y validación final. | E4 (tests passing). | UI no funciona con adapter; bloqueo de lanzamiento; políticas `preserve`/`safe` no verificadas. | ⏳ Por iniciar |

**Orden de ejecución:** E0 → E1 → E2 → E3 → E4 → E5. No se salta ni paraleliza fases. Cada fase debe completarse y verificarse antes de proceder a la siguiente.

**E0 permanece marcada como completada.** El presente documento es el entregable de E0.

**E1 continúa pendiente de autorización explícita del usuario.** Antes de iniciar E1, debe confirmarse lo siguiente (ver sección 12):

- Se comprende que la transacción SQLite garantiza consistencia de BD, pero **no rollback** operaciones sobre PDFs fuente.
- La política `preserve` obliga a nunca modificar/sobreescribir/renombrar PDFs originales — el staging/rollback solo recupera estado BD previo.
- Las rutas `COLLECTION_SOURCE`, `WORKSPACE_ROOT`, `TESSERACT_CMD`, `TESSDATA_PREFIX` serán sustituidas por variables de entorno sin defaults de usuario.
- `sys.exit()` en funciones críticas será sustituido por excepciones personalizadas; el hilo UI decidirá cómo manejarlas.
- El orden de ejecución es: E1 → E2 → E3 → E4 → E5 — no se salta ni paraleliza.
- Se tiene disponible entorno de pruebas con `pytest`, `tmp_path`, y capacidad de crear PDFs sintéticos.
- Se respeta que esta fase (E0-E5) es **exclusivamente de análisis y documentación**; no se modifica código hasta iniciar E1.

---

## 12. Criterios de Aceptación por Fase

### Criterios E1

- [ ] `update_collection` usa staging transaccional: pruebas `TEST-001` (éxito) y `TEST-002/003` (fallo/rollback) pasan.
- [ ] Todas las rutas hardcodeadas sustituidas o con detección automática; `config.py` sin `Path(...)` absolutas de usuario.
- [ ] `TESSERACT_CMD` y `TESSDATA_PREFIX` totalmente configurables por entorno sin defaults de usuario.
- [ ] Ninguna operación de adapter modifica PDF fuente original (validar política `preserve`).
- [ ] `PRAGMA foreign_keys = ON` configurado en cada conexión `Repository._open()`.
- [ ] `validate_engine` retorna `foreign_key_issues=0` cuando las FK están activas y relaciones son coherentes.
- [ ] `is_available()` retorna `False` de forma explícita cuando Tesseract no está configurado, sin degradación silenciosa.

### Criterios E2

- [ ] Todas las funciones expuestas del adapter retornan `OperationResult` (nunca `print`/`sys.exit`).
- [ ] `JobManager` operativo con 3 señales básicas: `progress_updated`, `job_completed`, `job_cancelled`.
- [ ] DTOs definidos para: `EngineStatusDTO`, `DocumentDTO`, `UpdateReportDTO`, `QueryResultDTO`, `ValidationReportDTO`, `OcrPageResultDTO`.
- [ ] `cli.main()` funciona como wrapper opcional (usa adapter internamente, formatea salida consola).
- [ ] `ask_document_question` con `provider="mock"` retorna `answer` que declara "no hubo síntesis por IA" y cita solo informativa.
- [ ] `validate_engine` adapter retorna `ValidationReportDTO` estructurado, no `print()`/`sys.exit()`.

### Criterios E3

- [ ] Las 12 métodos contractuales están expuestos en `DocumentEngineAdapter`.
- [ ] Todos retornan `OperationResult` (nunca `print`/`sys.exit`).
- [ ] Rutas configurables, no hardcodeadas.
- [ ] Staging transaccional en `update_collection` (heredado de E1 verificado).
- [ ] Modo mock por defecto, API con confirmación explícita.
- [ ] Validación de citas y reporte de coherencia FTS5.
- [ ] `clean_derived_data` y `reindex_collection` implementados con patrón backup-confirmar-restore.

### Criterios E4

- [ ] Batería de tests passing al 80%+ sobre métodos contractuales (TEST-001 a TEST-014 como mínimo, TEST-015 a TEST-028 opcionales pero recomendados).
- [ ] Ningún test usa colección documental real ni rutas absolutas de desarrollador.
- [ ] Reportes de cobertura y resultados guardados en `docs/audits/`.
- [ ] Casos TEST-015 a TEST-028 diseñados y (opcionalmente) passing.

### Criterios E5

- [ ] UI Tech Cyan integra adapter sin crashes ni pérdida de datos.
- [ ] Flujo completo (scan → update → search → ask) operable desde botones/menús.
- [ ] Política `preserve` y `safe` verificadas en escenario UI.
- [ ] PyInstaller `onedir` build funcional con motor adaptado.
- [ ] Documentación de usuario actualizada.
- [ ] Licencias PyMuPDF aprobadas para distribución onedir.

---

## 13. Riesgos Residuales y Decisiones Pendientes

### Riesgos no resueltos (después de E1 completado)

| Riesgo | Motivación | Mitigación |
|---|---|---|
| **Transacción SQLite no protege archivos PDF externos** | Limitación inherente de SQLite; el rollback afecta solo a la BD. | Política `preserve` a nivel aplicación: nunca sobrescribir PDFs fuente. El staging/rollback solo recupera estado BD previo. El PDF en disco se deja intacto (solo lectura). |
| **Umbral `DIGITAL_TEXT_THRESHOLD = 10`** | Valor por defecto definido en `extractor.py:12`. | Pendiente de hacer configurable por colección/entorno (mejora post-V1). No bloqueante para V1 si umbral es aceptable para el caso de uso objetivo. |
| **Ausencia de `clean_derived_data` y `reindex_collection` implementaciones** | Son nuevas implementaciones, no correcciones de bugs. | Pendientes para post-V1. Diseño definido en contrato E3 (sección 8). |
| **Validación de licencias PyMuPDF para distribución onedir** | Fuera del alcance auditoría actual; requiere revisión legal. | Pendiente antes de E5 (preparación empaquetado). No bloquea desarrollo. |
| **Integración real de Windows Credential Manager** | Requiere investigación de SDKs y modelos de integración. | Usar variables de entorno como solución interina (política `safe`: secrets fuera código). |

### Decisiones pendientes (por autorizar)

1. **Patrón de staging transaccional E1:** ¿Acepta que la transacción SQLite garantiza consistencia de BD, pero **no rollback** operaciones sobre PDFs fuentes? Mitigación: política `preserve` + nunca escribir sobre archivos fuente.

2. **Rutas configurable: valores por defecto detección automática vs. requerir definición de env:** ¿Exigir que `DOC_COLLECTION_SOURCE`, `DOC_WORKSPACE_ROOT`, `TESSERACT_CMD` y `TESSDATA_PREFIX` estén definidas explícitamente en variables de entorno para producción, o permitir que la detección automática sea el mecanismo de fallback en desarrollo?

3. **Sistema de jobs/cola thread-safe E2:** ¿Priorizar la implementación del `JobManager` con señales de progreso y cancelación (complejidad media, beneficio alto para GUI) o posponer a una versión posterior consideringando que el motor actual es CLI-first?

4. **Algún método contrato E3 sobrante o que requiere modificación significativa:** Revisar tabla de 12 métodos — `clean_derived_data` y `reindex_collection` son nuevas implementaciones que no existen en el motor actual. ¿Están el scope aprobado o deben reducirse?

5. **Umbral `DIGITAL_TEXT_THRESHOLD`:** ¿Mantener default 10 para V1 o hacerlo configurable desde el inicio considerando que podría requerir calibración en diferentes colecciones?

---

## 14. Registro de Cambios del Documento

| Fecha | Versión | Modificador | Cambio Descripción | Impacto |
|---|---|---|---|---|
| 08/11/2026 | 1.0 | — | Documento generado inicialmente como parte de auditoría cruzada E0. | Base de referencia para todas las fases subsiguientes. |
| **Fecha actual** | **1.1** | **Actualización documental** | **Reestructuración en 15 secciones solicitadas. Consolidación R1+R5. Nueva estrategia de rutas inyectables. Definición estrategia Tesseract portable. Separación E1/E2 explícita. Contrato 12 métodos DocumentEngineAdapter con DTOs. Patrón backup-confirmar-restore para clean_derived_data. 8 nuevos casos de prueba (TEST-015 to TEST-028). Actualización criterios aceptación por fase. Riesgos residuales y decisiones pendientes.** | **Documento ahora es referencia única y coherente para remediación E1-E5. No modifica código ni datos existentes.** |

**Trazabilidad con identificadores:**
- Todos los hallazgos originales conservados con identificadores R1–R14.
- Relación explicitada entre identificadores consolidados y fuentes originales (archivo:línea).
- No se eliminan hallazgos originales: si se consolidan, registrar expresamente la relación entre identificadores (ej. "R1 y R5 consolidados en problema de integridad transaccional — ver sección 5").
- Casos de prueba TEST-001 a TEST-014 heredados de plan original; TEST-015 a TEST-028 nuevos para cobertura ampliada.

**Archivos verificados como intactos:**
- `docs/audits/ENGINE_STATIC_AUDIT.md` — 33,259 bytes, fecha 08/11/2026, sin modificaciones.
- `docs/audits/ENGINE_INTEGRATION_GAPS.md` — 28,582 bytes, fecha 08/11/2026, sin modificaciones.
- Ningún archivo `.py` modificado.
- `pyproject.toml` sin modificaciones.

---

## 15. Verificación Final

Al terminar de trabajar con este documento, comprobar:

1. [ ] **Sólo se modificó `docs/audits/ENGINE_REMEDIATION_PLAN.md`.** Ningún otro archivo fue propenso como objetivo de modificación.
2. [ ] **Los dos informes originales siguen intactos:** `ENGINE_STATIC_AUDIT.md` y `ENGINE_INTEGRATION_GAPS.md` conservan sus bytes y fechas originales (08/11/2026).
3. [ ] **No se modificó ningún archivo Python.** `vendor/document_engine/src/documental/*.py` y cualquier otro `.py` en el repositorio tienen sus timestamps/hashes originales.
4. [ ] **No se ejecutó el motor documental.** Ningún script `cli.py`, `database.py` u otros fueron ejecutados durante esta sesión.
5. [ ] **No se accedió a bases de datos reales.** Todas las referencias a DB son conceptuales o a la estructura de esquema; no hay conexiones SQL activas.
6. [ ] **No se abrió ni modificó PDF original.** La colección documental permanece sin tocar.
7. [ ] **E1 continúa pendiente de autorización.** No hay marca de "E1 iniciado" en el documento o en cualquier metadato asociado.
8. [ ] **No existan contradicciones con decisiones arquitectónicas:** El documento conserva explícitamente `preserve`, `embedded`, `safe`, dos bases SQLite separadas, sin nube/sync V1, sin embeddings sin decisión explícita, PDF originales inmutables, secretos fuera código, no enviar documentos completos a IA, MockProvider para desarrollo, Windows Credential Manager como preferencia, SQL/ruta/job seguros.
9. [ ] **Sección 12 (Criterios de aceptación) es autoconsistente.** Cada criterio E1/E2/E3/E4/E5 tiene al menos un caso de prueba asociado (TEST-XXX) que lo validaría.
10. [ ] **Trazabilidad maintainida.** Cada identificador R1–R14 y TEST-001 a TEST-028 puede rastrearse hasta su fuente original en `ENGINE_STATIC_AUDIT.md` o `ENGINE_INTEGRATION_GAPS.md`.

**En caso de que alguna verificación falle:** Detener proceso y reportar discrepancia. No proceder con fases subsiguientes hasta resolver la inconsistencias documentalmente (no mediante modificaciones de código).