#!/usr/bin/env python
import sys

with open('vendor/document_engine/src/documental/config.py', 'r', encoding='utf-8', errors='replace') as f:
    content = f.read()

# Mejorar la documentación de OCR_LANGUAGES, OCR_DPI, OCR_ENABLED, AI_PROVIDER
old_ocr_lang = 'OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "spa")   # principal: spa; eng opcional via entorno'
new_ocr_lang = 'OCR_LANGUAGES = os.getenv("OCR_LANGUAGES", "spa")  # Idioma principal OCR (spa/eng). Configurable via DOC_OCR_LANGUAGES'

old_ocr_dpi = 'OCR_DPI = int(os.getenv("OCR_DPI", "200"))'
new_ocr_dpi = 'OCR_DPI = int(os.getenv("OCR_DPI", "200"))  # Resolución DPI para OCR Tesseract (estándar 200dpi). Configurable via DOC_OCR_DPI'

old_ocr_enabled = 'OCR_ENABLED = os.getenv("OCR_ENABLED", "1") == "1"'
new_ocr_enabled = 'OCR_ENABLED = os.getenv("OCR_ENABLED", "1") == "1"  # 1=habilitado, 0=deshabilitado. Modo seguro por defecto. Configurable via DOC_OCR_ENABLED'

old_ai_provider = 'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")   # mock | api'
new_ai_provider = 'AI_PROVIDER = os.getenv("DOC_AI_PROVIDER", "mock")  # mock | api. Modo mock (seguro por defecto). Cambiar a API requiere DOC_AI_PROVIDER=api'

if old_ocr_lang in content:
    content = content.replace(old_ocr_lang, new_ocr_lang)
if old_ocr_dpi in content:
    content = content.replace(old_ocr_dpi, new_ocr_dpi)
if old_ocr_enabled in content:
    content = content.replace(old_ocr_enabled, new_ocr_enabled)
if old_ai_provider in content:
    content = content.replace(old_ai_provider, new_ai_provider)

with open('vendor/document_engine/src/documental/config.py', 'w', encoding='utf-8', errors='replace') as f:
    f.write(content)

print('config.py documentada actualizada')
# Mostrar la parte modificada
lines = content.split('\n')
for i in range(28, 42):
    if i < len(lines):
        print(f'L{i+1}: {lines[i]}')
PYEND