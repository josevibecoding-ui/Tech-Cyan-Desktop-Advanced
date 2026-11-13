# Checklist de Pre-Autorización E1 - Levantamiento de Restricciones Temporales

**Documento:** docs/audits/E1_AUTHORIZATION_CHECKLIST.md  
**Propósito:** Recopilación estructurada de los requisitos previos para levantar las restricciones `preserve` y `safe` en las pruebas de testing contra colección real y bases SQLite persistentes.  
**Estado:** Pendiente de autorización explícita del usuario.  
**Fecha de creación:** 13/11/2026  

---

## 1. Datos del Usuario Autorizado

| Campo | Valor |
|-------|-------|
| **Nombre completo:** | *Por llenar por el usuario autorizado* |
| **Fecha:** | *Por llenar por el usuario autorizado* |
| **Correo electrónico:** | *Por llenar por el usuario autorizado* |
| **Cargo/rol:** | *Por llenar por el usuario autorizado* |

**Declaración del usuario:**  
*Firma escrita (email, documento firmado, etc.) que incluye: nombre completo, fecha, declaración de haber leído y entendido los riesgos, aceptación de responsabilidad sobre datos.*  
*El usuario debe proporcionar firma escrita (email, documento firmado, etc.) que incluya los campos arriba mencionados.*

---

## 2. Checklist de Pre-Autorización (Sección 3.2 del TESTING_REAL_RESTRICTIONS_RELEASE.md)

| # | ítem | Estado | Comentarios |
|---|------|--------|-------------|
| 1 | ✅ **Backup verifiable de colecciÓn PDF creada y verificada** | **PENDIENTE** | *No se ha creado backup verificable. Se requiere: `cp -r /ruta/colecciÓn /ruta/colecciÓn.backup` y `sqlite3 db.sqlite "PRAGMA integrity_check" -> ok*` |
| 2 | ✅ **Entorno de testing aislado configurado** | **PENDIENTE** | *No configurado. Requiere: exportar DOC_COLLECTION_SOURCE, DOC_WORKSPACE_ROOT, TESSERACT_CMD, TESSDATA_PREFIX, DIGITAL_TEXT_THRESHOLD, OCR_ENABLED, OCR_LANGUAGES* |
| 3 | ✅ **Plan de rollback documentado y practicado** | **PENDIENTE** | *No documentado. Requiere: pasos de rollback con rsync -r /ruta/backup/ /ruta/colecciÓn/ y verificación con PRAGMA integrity_check* |
| 4 | ✅ **Usuario consciente de riesgos de datos** | **PENDIENTE** | *El usuario debe declarar haber leído y entendido los riesgos de datos (pérdida potencial de PDFs, modificación de SQLite, etc.)* |
| 5 | ✅ **SupervisiÓn programada durante testing** | **PENDIENTE** | *Se requiere definir horario y usuario de contacto en caso de emergencia* |

---

## 3. Estructura de Directorios Requerida (Sección 4.2 del documento base)

```text
/ruta/raíz/testing/
└── collection/              # PDFs reales a testear (solo lectura)
   ├── documento1.pdf
   ├── documento2.pdf
   └── ... 
├── backup/                  # Mismo árbol que collection (copia seguridad)
│   ├── documento1.pdf
│   ├── documento2.pdf
│   └── ... 
├── db/                      # Base SQLite de testing
│   └── documents.db
├── extracted/               # Texto extraído temporal
│   ├── documento1.txt
│   └── ... 
├── logs/                    # Logs de ejecución
│   └── testing.log
└── reports/                 # Reports generados
    └── testing_report.pdf
```

**Estado actual:** *Por definir por el usuario autorizado. El directorio `testing/collection/` existe en el repositorio pero contiene archivos de muestra, no una colección completa para testing.*

---

## 4. Procedimiento de Levantamiento (Sección 4.3 del documento base)

### 4.1. Backup de Colección
**Comando propuesto (NO ejecutado):**
```bash
cp -r /ruta/colecciÓn /ruta/colecciÓn.backup
```
**Verificación:**
```bash
sqlite3 /ruta/colecciÓn/db.sqlite "PRAGMA integrity_check"  # Debe retornar "ok"
```

**Estado:** *NO EJECUTADO. El usuario debe autorizar la creación del backup antes de proceder.*

### 4.2. Configuración de Variables de Entorno
```bash
# Colección y workspace
export DOC_COLLECTION_SOURCE="/ruta/absoluta/al/colección"
export DOC_WORKSPACE_ROOT="/ruta/absoluta/al/workspace"

# Tesseract (si se testea OCR)
export TESSERACT_CMD="/ruta/ejecutable/tesseract"
export TESSDATA_PREFIX="/ruta/datos/tessdata"

# Configuración de testing
export DIGITAL_TEXT_THRESHOLD="10"
export OCR_ENABLED="1"
export OCR_LANGUAGES="spa"
```

**Estado:** *Por configurar por el usuario autorizado.*

### 4.3. Verificación de Integridad
```bash
sqlite3 /ruta/colecciÓn/db.sqlite "PRAGMA integrity_check"  # Debe retornar "ok"
```

**Estado:** *Por verificar después del backup.*

### 4.3. Procedimiento Completo
1. Crear backup de colección: `cp -r /ruta/colecciÓn /ruta/colecciÓn.backup` *(NO EJECUTADO)*
2. Configurar variables de entorno *(PENDIENTE)*
3. Verificar integridad: `sqlite3 db.sqlite "PRAGMA integrity_check"` → debe retornar `ok` *(PENDIENTE)*
4. Ejecutar testing con autorización *(PENDIENTE - requiere firma del usuario)*
5. Aplicar rollback si es necesario: `rsync -r /ruta/backup/ /ruta/colecciÓn/` *(PENDIENTE)*
6. Verificar restauraciÓn: `sqlite3 db.sqlite "PRAGMA integrity_check"` → debe retornar `ok` *(PENDIENTE)*
7. Generar reporte y limpiar entorno *(PENDIENTE)*

---

## 5. Plan de Rollback (Sección 6 del documento base)

### 5.1. Cuándo Aplicar Rollback
Aplicar rollback si se detecta alguna anormalidad:
- `PRAGMA integrity_check` retorna distinto de `ok`
- Hashts de PDFs originales no coinciden con backup
- Errores inesperados en >20% de PDFs testeados
- Mensajes de error crí­ticos en logs
- Solicitud explícita del usuario autorizado

### 5.2. Pasos de Rollback

```bash
# 1. Detener procesos de testing en ejecución
pkill -f "python.*test"  # o el comando especí­fico

# 2. Restaurar colección desde backup
rsync -r /ruta/backup/ /ruta/colecciÓn/

# 3. Verificar restauraciÓn
prueba_integridad() {
    resultado=$(sqlite3 /ruta/colecciÓn/db.sqlite "PRAGMA integrity_check;")
    if [ "$resultado" = "ok" ]; then
        echo "Restauraci¢n exitosa"
    else
        echo "ERROR: Colección dañada despuÉs de rollback"
        exit 1
    fi
}

prueba_integridad

# 4. Verificar PDFs
md5sum /ruta/colecciÓn/*.pdf > /tmp/hashts_actuales.md5
md5sum /ruta/backup/*.pdf > /tmp/hashts_backup.md5
diff /tmp/hashts_actuales.md5 /tmp/hashts_backup.md5
# Debería mostrar diferencias solo si hubo cambios intencionales
```

**Estado:** *Plan documentado pero no practicado. El usuario debe autorizar el procedimiento.*

---

## 6. Limitaciones que Siguen Vigentes (Aún con restricciones levantadas)

**Políticas invariantes (aunque se levanten restricciones temporales):**

- **`preserve`**: PDFs originales solo lectura. Cualquier modificación está prohibida sin autorización escrita especí­fica para ese PDF.
- **`safe`**: Testing debe completarse y resultados documentados antes de finalizar sesión.
- **Sin nube/sync**: Los datos de testing no deben subir a ningú­n servicio en la nube.
- **Sin embeddings**: No se generarán embeddings vectoriales durante testing.

**Limitaciones técnicas:**
- No se puede modificar esquema de BD El motor `agente-documental` tiene esquema fijo
- No se pueden agregar campos nuevos Romperá compatibilidad con versiones existentes
- No se pueden crear nuevas tablas Mismo motivo anterior
- Testing paralelo no recomendado Puede causar bloqueos SQLite
- Testing cada test necesita su propio contexto

**Limitaciones de seguridad:**
- Sin credenciales guardadas Las variables de entorno son temporales
- Sin logging permanente Los logs se purgan después del testing
- Sin rastreo de usuario Más allá del usuario autorizado registrado
- Sin integra¢n con sistemas externos Testing aislado, sin conectar a producción

---

## 7. Checklist de Seguridad Pre-Testing (Repeated from §9.1)

| # | ítem | Estado | Acciones pendientes |
|---|------|--------|--------------------|
| 1 | ✅ Backup verifiable creado y verificado | **PENDIENTE** | *Requiere autorización y ejecución del comando `cp -r`* |
| 2 | ✅ Variables de entorno configuradas y testeadas | **PENDIENTE** | *Por configurar con valores absolutos* |
| 3 | ✅ Entorno aislado verificado (no afecta producción) | **PENDIENTE** | *Por definir directorios y verificar separación* |
| 4 | ✅ Usuario autorizado identificado y notificado | **PENDIENTE** | *Falta nombre y firma del usuario* |
| 5 | ✅ Rollback plan leído y entendido | **PENDIENTE** | *Falta lectura y aceptación del plan de rollback arriba descrito* |
| 5 | ✅ Tiempo estimado calculado y bloqueado en calendario | **PENDIENTE** | *Por definir (máximo 4 horas sugerido)* |
| 6 | ✅ Herramientas de rollback probadas | **PENDIENTE** | *No se han practicado los pasos de rollback* |
| 7 | ✅ Forma de reporte definida y plantilla lista | **PENDIENTE** | *Falta definir formato y plantilla de reporte* |
| 7 | ✅ Límites de tiempo y recursos establecidos (máximo 4 horas) | **PENDIENTE** | *Por definir* |
| 8 | ✅ Usuario de contacto en caso de emergencia identificado | **PENDIENTE** | *Por llenar* |

---

## 7. Checklist de Seguridad Post-Testing

| # | ítem | Estado | Acciones |
|---|------|--------|----------------|
| 1 | ✅ Rollback ejecutado (si fue necesario) | **PENDIENTE** | *Si se detectó anormalidad, aplicar pasos de rollback arriba* |
| 2 | ✅ Integridad de colección verificada (`PRAGMA integrity_check = ok`) | **PENDIENTE** | *Ejecutar `sqlite3 db.sqlite "PRAGMA integrity_check"`* |
| 3 | ✅ Hashts de PDFs comparados con backup (idénticos) | **PENDIENTE** | *Ejecutar `md5sum` y comparar con backup* |
| 4 | ✅ Reporte generado y guardado | **PENDIENTE** | *Falta generar reporte estructurado* |
| 5 | ✅ Notificación al usuario autorizado completada | **PENDIENTE** | *Falta notificar al usuario los resultados* |
| 6 | ✅ Entorno limpiado (remover variables temporales, limpiar temp files) | **PENDIENTE** | *Limpiar variables de entorno y files temporales* |
| 7 | ✅ Documentación actualizada con hallazgos | **PENDIENTE** | *Factualizar docs/audits/ con hallazgos del testing* |
| 8 | ✅ Lección aprendida registrada para futuros testing | **PENDIENTE** | *Falta registrar aprendizajes en documentación* |

---

## 8. Limitaciones que Siguen Vigentes (Sempre)

Aunque se levanten restricciones temporales, estas políticas **NO se suspenden**:

- **`preserve`**: PDFs originales solo lectura. Cualquier modificación está prohibida sin autorización escrita especí­fica para ese PDF.
- **`safe`**: Testing debe completarse y resultados documentados antes de finalizar sesión.
- **Sin nube/sync**: Los datos de testing no deben subir a ningú­n servicio en la nube.
- **Sin embeddings**: No se generarán embeddings vectoriales durante testing.

**Limitaciones técnicas:**
- No se puede modificar esquema de BD El motor `agente-documental` tiene esquema fijo
- No se pueden agregar campos nuevos Romperá compatibilidad con versiones existentes
- No se pueden crear nuevas tablas Mismo motivo anterior
- Testing paralelo no recomendado Puede causar bloqueos SQLite
- Testing cada test necesita su propio contexto

**Limitaciones de seguridad:**
- Sin credenciales guardadas Las variables de entorno son temporales
- Sin logging permanente Los logs se purgan después del testing
- Sin rastreo de usuario Más allá del usuario autorizado registrado
- Sin integra¢n con sistemas externos Testing aislado, sin conectar a producción

---

## 8. Siguiente Acción

Este documento permanecerá activo hasta que se complete el testing con autorización y se restauren todas las políticas originales. Una vez completado, las políticas `preserve` y `safe` vuelven a su estado activo automáticamente.

**No ejecutar testing contra colección real sin:**
1. Firma escrita del usuario autorizado
2. Backup verificable creado y verificado
3. Plan de rollback documentado y practicado
4. Usuario consciente de riesgos de datos
5. Supervisión programada durante testing

**Documento generado para autorización de testing especí­fico.**  
**No ejecutar sin autorización firmada y configuración adecuada.**

---
Fin del documento E1_AUTHORIZATION_CHECKLIST.md