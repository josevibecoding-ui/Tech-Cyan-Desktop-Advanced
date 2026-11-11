# Documentación para Levantamiento Temporal de Restricciones de Testing

**AVISO:** Este documento contiene instrucciones para levantar restricciones
prohibitivas (`preserve` y `safe` policies) y debe ser manejado solo con
autorización explícita del usuario correspondiente.

## 1. Propósito
Permitir testing específico contra colección real y bases SQLite persistentes
mientras se mantienen políticas de seguridad y se documenta todo el proceso.

## 2. Estado Actual
- **Políticas vigentes:** `preserve`, `safe`, sin nube/sync, sin embeddings
- **Testing actual:** Solo con `tmp_path` y PDFs sintéticos
- **Estado de levantamiento:** Cerrado (requiere autorización)

## 3. Autorización Requerida

### 3.1. Firma de Autorización
El usuario debe proporcionar firma escrita (email, documento firmado, etc.) que incluya:
- Nombre completo
- Fecha
- Declaración de haber leído y entendido los riesgos
- Aceptación de responsabilidad sobre datos

### 3.2. Checklist de Pre-autorización
- [ ] Backup verifiable de colección PDF creada y verificada
- [ ] Entorno de testing aislado configurado
- [ ] Plan de rollback documentado y practicado
- [ ] Usuario consciente de riesgos de datos
- [ ] Supervisión programada durante testing

## 4. Levantamiento de Restricciones

### 4.1. Variables de Entorno a Configurar
```bash
# Colección y workspace
export DOC_COLLECTION_SOURCE="/ruta/absoluta/al/coleccion"
export DOC_WORKSPACE_ROOT="/ruta/absoluto/al/workspace"

# Tesseract (si se testea OCR)
export TESSERACT_CMD="/ruta/ejecutable/tesseract"
export TESSDATA_PREFIX="/ruta/datos/tessdata"

# Configuración de testing
export DIGITAL_TEXT_THRESHOLD="10"
export OCR_ENABLED="1"
export OCR_LANGUAGES="spa"
```

### 4.2. Estructura de Directorios Requerida
```
/ruta/raíz/testing/
├── collection/          # PDFs reales a testear (solo lectura)
│   ├── documento1.pdf
│   └── ...
├── backup/              # Mismo árbol que collection (copia seguridad)
├── db/                  # Base SQLite de testing
├── extracted/           # Texto extraído temporal
├── logs/                # Logs de ejecución
└── reports/             # Reports generados
```

### 4.3. Procedimiento de Levantamiento
1. Crear backup de colección: `cp -r /ruta/colección /ruta/colección.backup`
2. Configurar variables de entorno (ver arriba)
3. Verificar integridad: `sqlite3 db.sqlite "PRAGMA integrity_check"` → debe retornar `ok`
4. Ejecutar testing con autorización
5. Aplicar rollback si es necesario: `rsync -r /ruta/backup/ /ruta/colección/`
6. Verificar restauración: `sqlite3 db.sqlite "PRAGMA integrity_check"` → debe retornar `ok`
7. Generar reporte y limpiar entorno

## 5. Procedimiento de Testing con Restricciones Levantadas

### 5.1. Testing contra Colección Real
```bash
# Ejemplo de ejecución
python -m pytest tests/audits/     --DOC_COLLECTION_SOURCE="/ruta/colección"     --DOC_WORKSPACE_ROOT="/ruta/workspace"     -v     --tb=short
```

### 5.2. Testing contra BD Persistente
```bash
# Ejecutar tests específicos
python -m pytest tests/audits/test_database.py -v     --db-path="/ruta/bbdd/persistente.sqlite"     ...
```

### 5.3. Validaciones Post-Testing
```bash
# Integridad SQLite
sqlite3 /ruta/bbdd/persistente.sqlite "PRAGMA integrity_check;"

# Comparar con backup
diff -r /ruta/colección /ruta/backup/ | wc -l  # Debería ser 0

# Generar reporte
# (Ver estructura de reporte en documentación)
```

## 6. Procedimiento de Rollback

### 6.1. Cuándo Aplicar Rollback
Aplicar rollback si se detecta alguna anomalía:
- `PRAGMA integrity_check` retorna distinto de `ok`
- Hashts de PDFs originales no coinciden con backup
- Errores inesperados en >20% de PDFs testeados
- Mensajes de error críticos en logs
- Solicitud explícita del usuario autorizado

### 6.2. Pasos de Rollback
```bash
# 1. Detener procesos de testing en ejecución
pkill -f "python.*test"  # o el comando específico

# 2. Restaurar colección desde backup
rsync -r /ruta/backup/ /ruta/colección/

# 3. Verificar restauración
prueba_integridad() {
    resultado=$(sqlite3 /ruta/colección/db.sqlite "PRAGMA integrity_check;")
    if [ "$resultado" = "ok" ]; then
        echo "Restauración exitosa"
    else
        echo "ERROR: Colección dañada después de rollback"
        exit 1
    fi
}
prueba_integridad

# 4. Verificar PDFs
md5sum /ruta/colección/*.pdf > /tmp/hashts_actuales.md5
md5sum /ruta/backup/*.pdf > /tmp/hashts_backup.md5
diff /tmp/hashts_actuales.md5 /tmp/hashts_backup.md5
# Debería mostrar diferencias solo si hubo cambios intencionales
```

## 7. Generación de Reportes

### 7.1. Estructura del Reporte
El reporte debe incluir:
- Fecha y hora del testing
- Usuario autorizado
- Configuración usada (variables de entorno)
- PDFs procesados y resultados
- Integridad SQLite y PDFs
- Anomalias detectadas
- Acción de rollback (S/N y motivo)
- Firmado por usuario autorizado

### 7.2. Template de Email de Resultados
```
Asunto: Resultados Testing Colección Real - [Fecha]

Hola [Nombre],

A continuación, los resultados del testing contra colección real:

[Insertar resumen del reporte adjunto]

Hallazgos principales:
- [Punto 1]
- [Punto 2]
- [Punto 3]

Rollback: [S/N] - [Descripción si aplica]

Próximos pasos:
- [Paso 1]
- [Paso 2]

Que tengas buen día,

[Firma]
```

## 8. Checklist de Seguridad

### 8.1. Pre-Testing
- [ ] Backup verifiable creado y verificado
- [ ] Variables de entorno configuradas y testeadas
- [ ] Entorno aislado verificado (no afecta producción)
- [ ] Usuario autorizado identificado y notificado
- [ ] Rollback plan leído y entendido
- [ ] Tiempo estimado calculado y bloqueado en calendario
- [ ] Herramientas de rollback probadas
- [ ] Forma de reporte definida y plantilla lista
- [ ] Límites de tiempo y recursos establecidos (ej. máximo 4 horas)
- [ ] Usuario de contacto en caso de emergencia identificado

### 8.2. Post-Testing
- [ ] Rollback ejecutado (si fue necesario)
- [ ] Integridad de colección verificada (`PRAGMA integrity_check = ok`)
- [ ] Hashts de PDFs comparados con backup (idénticos)
- [ ] Reporte generado y guardado
- [ ] Notificación al usuario autorizado completada
- [ ] Entorno limpiado (remover variables temporales, limpiar temp files)
- [ ] Documentación actualizada con hallazgos
- [ ] Lección aprendida registrada para futuros testing

## 9. Comunicación de Resultados

### 9.1. Destinatarios
- Usuario autorizado que solicitó el testing
- Equipo de desarrollo (para conocimiento general)
- Equipo de QA (para incorporación de hallazgos)

### 9.2. Canales de Comunicación
- Email directo
- Reunión presencial o videoconferencia
- Actualización en tracker de proyectos (Jira, Trello, Asana, etc.)

### 9.3. Template de Email de Resultados
```
Asunto: Resultados Testing Colección Real - [Fecha]

Hola [Nombre],

A continuación, los resultados del testing contra colección real:

[Insertar resumen del reporte adjunto]

Hallazgos principales:
- [Punto 1]
- [Punto 2]
- [Punto 3]

Rollback: [S/N] - [Descripción si aplica]

Próximos pasos:
- [Paso 1]
- [Paso 2]

Que tengas buen día,

[Firma]
```

## 9.1. Limitaciones que Siguen Vigentes
Aunque se levanten restricciones temporales, estas políticas NO se suspenden:

- **`preserve`**: PDFs originales solo lectura. Cualquier modificación está prohibida sin autorización escrita específica para ese PDF.
- **`safe`**: Testing debe completarse y resultados documentados antes de finalizar sesión.
- **Sin nube/sync**: Los datos de testing no deben subir a ningún servicio en la nube.
- **Sin embeddings**: No se generarán embeddings vectoriales durante testing.

## 9.2. Limitaciones Técnicas
- **No se puede modificar esquema de BD** El motor `agente-documental` tiene esquema fijo
- **No se pueden agregar campos nuevos** Rompería compatibilidad con versiones existentes
- **No se pueden crear nuevas tablas** Mismo motivo anterior
- **Testing paralelo no recomendado** Puede causar bloqueos SQLite
- **No se pueden compartir BDs entre tests** Cada test necesita su propio contexto

## 9.3. Limitaciones de Seguridad
- **Sin credenciales guardadas** Las variables de entorno son temporales
- **Sin logging permanente** Los logs se purgan después del testing
- **Sin rastreo de usuario** Más allá del usuario autorizado registrado
- **Sin integración con sistemas externos** Testing aislado, sin conectar a producción

## 9.4. Checklist de Seguridad Pre-Testing
- [ ] Backup verifiable creado y verificado
- [ ] Variables de entorno configuradas y testeadas
- [ ] Entorno aislado verificado (no afecta producción)
- [ ] Usuario autorizado identificado y notificado
- [ ] Rollback plan leído y entendido
- [ ] Tiempo estimado calculado y bloqueado en calendario
- [ ] Herramientas de rollback probadas
- [ ] Forma de reporte definida y plantilla lista
- [ ] Límites de tiempo y recursos establecidos (ej. máximo 4 horas)
- [ ] Usuario de contacto en caso de emergencia identificado

## 9.2. Checklist de Seguridad Post-Testing
- [ ] Rollback ejecutado (si fue necesario)
- [ ] Integridad de colección verificada (`PRAGMA integrity_check = ok`)
- [ ] Hashts de PDFs comparados con backup (idénticos)
- [ ] Reporte generado y guardado
- [ ] Notificación al usuario autorizado completada
- [ ] Entorno limpiado (remover variables temporales, limpiar temp files)
- [ ] Documentación actualizada con hallazgos
- [ ] Lección aprendida registrada para futuros testing

## 10. Comunicación de Resultados

### 9.1. Destinatarios
- Usuario autorizado que solicitó el testing
- Equipo de desarrollo (para conocimiento general)
- Equipo de QA (para incorporación de hallazgos)

### 9.2. Canales de Comunicación
- Email directo
- Reunión presencial o videoconferencia
- Actualización en tracker de proyectos (Jira, Trello, Asana, etc.)

### 9.3. Template de Email de Resultados
```
Asunto: Resultados Testing Colección Real - [Fecha]

Hola [Nombre],

A continuación, los resultados del testing contra colección real:

[Insertar resumen del reporte adjunto]

Hallazgos principales:
- [Punto 1]
- [Punto 2]
- [Punto 3]

Rollback: [S/N] - [Descripción si aplica]

Próximos pasos:
- [Paso 1]
- [Paso 2]

Que tengas buen día,

[Firma]
```

## 9.2. Limitaciones que Siguen Vigentes
Aunque se levanten restricciones temporales, estas políticas NO se suspenden:

- **`preserve`**: PDFs originales solo lectura. Cualquier modificación está prohibida sin autorización escrita específica para ese PDF.
- **`safe`**: Testing debe completarse y resultados documentados antes de finalizar sesión.
- **Sin nube/sync**: Los datos de testing no deben subir a ningún servicio en la nube.
- **Sin embeddings**: No se generarán embeddings vectoriales durante testing.

## 9.3. Consideraciones Finales
- **Filosofía del proyecto:** Las políticas `preserve` y `safe` existen por una razón:
  - `preserve`: Los PDFs son patrimonio documental; no deben arriesgarse inadvertidamente
  - `safe`: Los tests deben ser repetibles y seguros, no arriesgar datos existentes
- **Cuándo levantar restricciones:** Solo cuando haya:
  - Autorización explícita del usuario con responsabilidad sobre los datos
  - Backup verifiable creado y verificado
  - Rollback plan documentado y practicado
  - Necesidad real (no "por probar qué tal funciona")
  - Supervisión adecuada programada
- **Alternativas recomendadas** en lugar de testing contra colección real:
  - PDFs sintéticos generados con pymupdf (ya permitido)
  - Mocks y stubs para patrones de consumo
  - Testing de integración sintética (simular comportamiento sin datos reales)
  - Testing en entorno de staging con copia de seguridad completa
  - Revisiones de código estáticas en lugar de testing dinámico

## 10. Siguiente Acción
Este documento permanecerá activo hasta que se complete el testing con autorización y se restauren todas las políticas originales. Una vez completado, las restricciones `preserve` y `safe` vuelven a su estado activo automáticamente.

*Documento generado para autorización de testing específico.
No ejecutar sin autorización firmada y configuración adecuada.*
