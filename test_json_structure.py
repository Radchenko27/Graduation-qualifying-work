import json
from pathlib import Path

# Проверяем структуру processed JSON
p = Path('processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json')

with open(p, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("=" * 70)
print("СТРУКТУРА PROCESSED JSON")
print("=" * 70)
print(f"Корневые ключи: {list(data.keys())}")
print()

# Проверяем structure
if 'structure' in data:
    struct = data['structure']
    print(f"structure тип: {type(struct)}")
    keys = list(struct.keys())
    print(f"structure ключи (первые 3): {keys[:3]}")
    print(f"Тип первого ключа: {type(keys[0])}")
    print()
    
    first_key = keys[0]
    first_page = struct[first_key]
    print(f"structure[{first_key}] ключи: {list(first_page.keys())}")
    
    if 'text_blocks_details' in first_page:
        blocks = first_page['text_blocks_details']
        print(f"\ntext_blocks_details найден: {len(blocks)} блоков")
        print(f"Первый блок:")
        print(json.dumps(blocks[0], indent=2, ensure_ascii=False))
    else:
        print(f"\n❌ text_blocks_details НЕ найден!")
        print(f"Доступные ключи: {list(first_page.keys())}")

print()
print("=" * 70)
print("ПРОВЕРКА ЧТЕНИЯ ЧЕРЕЗ КЛЮЧИ")
print("=" * 70)

# Проверяем доступ по разным ключам
struct = data.get('structure', {})

print(f"Ключ '0' в structure: {'0' in struct}")
print(f"Ключ 0 в structure: {0 in struct}")

if '0' in struct:
    print(f"✓ Доступ по '0': {list(struct['0'].keys())}")
if 0 in struct:
    print(f"✓ Доступ по 0: {list(struct[0].keys())}")

# Проверяем text
print()
print("=" * 70)
print("ПРОВЕРКА TEXT")
print("=" * 70)
if 'text' in data:
    text = data['text']
    print(f"text тип: {type(text)}")
    print(f"text ключи (первые 3): {list(text.keys())[:3]}")
    print(f"Тип первого ключа: {type(list(text.keys())[0])}")
    if '0' in text:
        print(f"text['0'] preview: {text['0'][:200]}")
