#!/usr/bin/env python3
"""Проверка структуры выходного JSON DocumentParser"""

import json
from pathlib import Path

# Загружаем пример processed JSON
processed_path = Path(r"C:\Users\dimar\Desktop\BMSTU_IU5\Graduation-qualifying-work\processed\03-23-ОГР01.1-ЭОМ1.1-Изм.1\03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json")

if processed_path.exists():
    with open(processed_path, 'r', encoding='utf-8') as f:
        processed = json.load(f)
    
    print("=== СТРУКТУРА PROCESSED JSON ===")
    print(f"Корневые ключи: {list(processed.keys())}")
    
    # Проверяем structure
    if 'structure' in processed:
        print(f"\nstructure ключи: {list(processed['structure'].keys())}")
        page_0 = processed['structure'].get('0', {})
        print(f"structure[0] ключи: {list(page_0.keys())}")
        
        if 'text_blocks_details' in page_0:
            blocks = page_0['text_blocks_details']
            print(f"\ntext_blocks_details[0]:")
            if blocks:
                print(json.dumps(blocks[0], indent=2, ensure_ascii=False))
    
    # Проверяем text
    if 'text' in processed:
        print(f"\ntext ключи: {list(processed['text'].keys())}")
        if '0' in processed['text']:
            text_preview = processed['text']['0'][:200]
            print(f"text[0] preview: {text_preview}...")
else:
    print(f"Файл не найден: {processed_path}")
    print("\nПроверьте путь к файлу.")
