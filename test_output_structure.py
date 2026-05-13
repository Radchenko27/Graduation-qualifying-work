"""
Тест структуры выхода DocumentParser без БД.
Использует существующий processed JSON напрямую.
"""
import json
from pathlib import Path

# Загружаем существующий processed JSON
processed_path = Path('processed/17-23-00-ЭОМ/17-23-00-ЭОМ_processed.json')

with open(processed_path, 'r', encoding='utf-8') as f:
    processed_data = json.load(f)

print("=" * 70)
print("АНАЛИЗ PROCESSED JSON")
print("=" * 70)
print(f"Корневые ключи: {list(processed_data.keys())}")

# Проверяем text
if 'text' in processed_data:
    text = processed_data['text']
    print(f"\ntext: {len(text)} страниц")
    print(f"Ключи text: {list(text.keys())[:5]}...")

# Проверяем structure
if 'structure' in processed_data:
    structure = processed_data['structure']
    print(f"\nstructure: {len(structure)} страниц")
    if structure:
        first_key = list(structure.keys())[0]
        print(f"Первый ключ structure: {first_key} (тип: {type(first_key).__name__})")
        print(f"structure[{first_key}] ключи: {list(structure[first_key].keys())}")
        
        if 'text_blocks_details' in structure[first_key]:
            blocks = structure[first_key]['text_blocks_details']
            print(f"✓ text_blocks_details: {len(blocks)} блоков")
            if blocks:
                print(f"  Первый блок: {json.dumps(blocks[0], indent=2, ensure_ascii=False)[:300]}...")
        else:
            print(f"✗ text_blocks_details НЕТ в structure[{first_key}]")
else:
    print(f"\n✗ structure НЕТ в JSON")

# Проверяем pages
if 'pages' in processed_data:
    pages = processed_data['pages']
    print(f"\npages: {len(pages)} элементов")
    if pages and isinstance(pages, list):
        print(f"pages[0] ключи: {list(pages[0].keys())}")
        if 'structure' in pages[0]:
            print(f"pages[0]['structure'] ключи: {list(pages[0]['structure'].keys())}")

print("\n" + "=" * 70)
print("ВЫВОД:")
print("=" * 70)
has_blocks = False
if 'structure' in processed_data and processed_data['structure']:
    first = list(processed_data['structure'].values())[0]
    has_blocks = 'text_blocks_details' in first

if has_blocks:
    print("✓ В processed JSON ЕСТЬ text_blocks_details")
    print("  DocumentParser будет использовать геометрический парсинг")
else:
    print("✗ В processed JSON НЕТ text_blocks_details")
    print("  Нужно переобработать PDF с analyze_structure=True")
    print("  Или использовать существующий текстовый fallback")
