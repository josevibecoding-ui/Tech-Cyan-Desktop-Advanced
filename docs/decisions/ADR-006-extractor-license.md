# ADR-006: Licencia del extractor PyMuPDF/PyPDF

## Decisión

La decisión final es: **Mantener el uso dual de PyMuPDF y PyPDF**, manteniendo la opción de cambiar a solo PyPDF si cambian las circunstancias de distribución.

## Contexto

El motor de extracción actual (`vendor/document_engine/src/documental/extractor.py`) utiliza ambos extractores:

- **PyMuPDF (fitz)**: bajo licencia **AGPL-3.0**
- **PyPDF**: bajo licencia **BSD-3-Clause**

## Análisis de licencias

### PyMuPDF (AGPL-3.0)

- **Requerimiento**: El usuario que recibe el software binario debe tener acceso al código fuente
- **Impacto en distribución PyInstaller onedir**: Si la aplicación se distribuye como una aplicación cerrada (sin código fuente visible), la licencia AGPL requiere que se proporcione el código fuente a los usuarios
- **Riesgo**: No compatible con distribución de código cerrado sin proporcionar el fuente

### PyPDF (BSD-3-Clause)

- **Licencia permisiva**: Puede usarse en software cerrado sin restricciones
- **Compatibilidad**: Total compatibilidad con distribución PyInstaller onedir sin restricciones
- **Ventaja**: No requiere compartir código fuente

## Opciones consideradas

| Opción | Descripción | Impacto |
|--------|-----------|---------|
| **Mantener PyMuPDF actual** | Mantener el código actual con soporte de PyMuPDF como respaldo | Compatible con uso actual, pero requiere atención a la licencia |
| **Cambiar a solo PyPDF** | Eliminar la dependencia de PyMuPDF, usar solo PyPDF | Elimina el problema de licencia, pero podría perder capacidades de fallback |
| **Dual licensing** | Mantener ambos, pero documentar claramente la excepción | Complejidad administrativa, pero preserva opciones |

## Decisión

Mantener el uso dual actual (PyMuPDF + PyPDF) con la siguiente estrategia:

1. **PyMuPDF se usa como fallback** cuando PyPDF falla (como se implementa actualmente en `extractor.py`)
2. **No se elimina PyMuPDF arbitrariamente** - la decisión de cambiar requiere evaluación explícita
3. **Documentar la excepción** en `docs/decisions/ADR-006-extractor-license.md`
4. **Monitorear cambios de licencia** - si PyMuPDF cambia su licencia, reevaluar la decisión

## Próximos pasos

1. **No modificar el código del extractor** - la decisión actual no requiere cambios en el código
2. **Documentar la decisión** en `docs/REFERENCES.md` si es necesario
3. **Reevaluar si cambian las circunstancias** de distribución o licencia

**Fecha:** 13/11/2026  
**Decisión por:** Equipo de desarrollo Tech Cyan Desktop Advanced  
**Estado:** Definido (no requiere cambio de código inmediato)
HEADER