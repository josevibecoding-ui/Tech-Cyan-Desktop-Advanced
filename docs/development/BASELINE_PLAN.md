# Línea Base de Planificación - Tech Cyan Desktop Advanced

## Estado Actual (a 13/11/2026)

| Fase | Estado | Criterios de Aceptación | Dependencias |
|------|--------|------------------------|--------------|
| 0. Reconocimiento no destructivo | ✅ **Completada** | • Auditoria estática completada • Riesgos identificados y categorizados | Ninguna |
| 1. E1: Aislamiento de configuración TCDA | **~80% completada** | • 27/27 tests passing • Migración DOC_* → TCDA_* completa • Observaciones de auditoría resueltas | Fase 0 |
| 2. E2: Estabilizar motor | **~60% completada** | • Motor estable • 27/27 tests passing • Configuración TCDA aislada | Fase 1 |
| 3. E3: DocumentEngineAdapter + CustomTkinter | **0% iniciada** | • Documentación del contrato completada • Pending: implementación UI | Fase 2 |
| 4. SQLite Tech Cyan | **0% iniciada** | • Definir esquema de 2 bases SQLite • Política de no migración automática | Pendiente de Fase 3 |
| 5. Servicios/Jobs | **0% iniciada** | • Definir arquitectura de jobs • Cola de tareas • Sin implementar | Pendiente de Fase 3 |
| 6. UI base | **0% iniciada** | • Definir componentes UI • Patrón no bloqueante • Pending de Fase 3 | Pendiente de Fase 3 |
| 7. IA | **0% iniciada** | • Definir proveedores • MockProvider por defecto • Pending de Fase 3 | Pendente de Fase 3 |
| 8. Mantenimiento | **0% iniciada** | • Plan de mantenimiento • Sin implementar | Pending de Fases anteriores |
| 9. QA y empaquetado | **0% iniciada** | • Suite de tests • Empaquetador PyInstaller • Pending de Fases anteriores | Pending de Fases anteriores |

## Dependencias entre fases

- **Fase 0** bloquea: Fases 1-9
- **Fase 1** (E1) bloquea: Fases 2-9
- **Fase 2** (E2) bloquea: Fases 3-9
- **Fase 2.5** (Adapter) bloquea: Fases 4-9

## Estimaciones de tiempo (relativas)

| Fase | Estimación semanal | Comentario |
|------|-------------------|------------|
| 0. Reconocimiento | 0.5 semana | Finalizada |
| 1. E1: Aislamiento TCDA | 1 semana | Completa (27/27 tests) |
| 2. E2: Estabilizar motor | 1 semana | 60% completada |
| 2.5. Adapter CustomTkinter | 1.5 semanas | Pendiente de inicio |
| 4. SQLite Tech Cyan | 1 semana | Pendiente de Fase 2.5 |
| 5. Servicios/Jobs | 1 semana | Pendiente de Fase 2.5 |
| 6. UI base | 1 semana | Pendiente de Fase 2.5 |
| 7. IA | 1 semana | Pendiente de Fase 2.5 |
| 8. Mantenimiento | 0.5 semana | Pendiente de Fases anteriores |
| 9. QA y empaquetado | 1 semana | Pendiente de Fases anteriores |

**Fecha de corte de datos:** 13/11/2026

**Metodología:** Estimaciones relativas basadas en la complejidad relativa de cada fase, sin plazos de negocio forzosos.
