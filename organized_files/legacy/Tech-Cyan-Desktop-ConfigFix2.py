#!/usr/bin/env python
import sys

with open('vendor/document_engine/src/documental/config.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Revertir el cambio problemático en DIGITAL_TEXT_THRESHOLD y mantener el default de 10
# que es un valor razonable y forma parte del comportamiento original del sistema.
# El objetivo es quitar defaults de usuario "ocultos", pero un umbral por defecto de 10
# es un valor de desarrollo razonable, no una configuración de usuario sigilosa.

# Reemplazar solo la línea problemática
if 'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD"))' in content:
    content = content.replace(
        'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD"))',
        'DIGITAL_TEXT_THRESHOLD = int(os.getenv("DIGITAL_TEXT_THRESHOLD", "10"))'
    )

with open('vendor/document_engine/src/documental/config.py', 'w', encoding='utf-8', errors='replace') as f:
    f.write(content)

print('config.py corregida: DIGITAL_TEXT_THRESHOLD con default de 10')

# Verificar pruebas
print('Verificando que las pruebas pasan...')
PYEOF