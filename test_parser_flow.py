"""
Проверка полного цикла парсинга документа
"""
import json
from pathlib import Path
import sys
sys.path.insert(0, '.')

from app.utils.document_parser import DocumentParser

# Тестируем на документе 32 (03-23-ОГР01.1-ЭОМ1.1-Изм.1)
doc_id = 32

print("=" * 70)
print(f"ПРОВЕРКА DocumentParser для документа ID={doc_id}")
print("=" * 70)

try:
    with DocumentParser(doc_id, processed_dir='processed') as parser:
        print(f"\n✓ DocumentParser создан")
        print(f"Документ: {parser.document.name}")
        print(f"Всего страниц в БД: {len(parser.all_pages)}")
        
        # Проверяем загруженные данные
        print(f"\n--- processed_data ключи: {list(parser.processed_data.keys())}")
        
        # Проверяем structure
        if 'structure' in parser.processed_data:
            struct = parser.processed_data['structure']
            print(f"structure ключи: {list(struct.keys())[:5]}...")
            if struct:
                first_key = list(struct.keys())[0]
                print(f"Первый ключ structure: '{first_key}' (тип: {type(first_key).__name__})")
                
                # Проверяем text_blocks_details
                if 'text_blocks_details' in struct[first_key]:
                    blocks = struct[first_key]['text_blocks_details']
                    print(f"✓ text_blocks_details найден: {len(blocks)} блоков")
                else:
                    print(f"✗ text_blocks_details НЕ найден в structure[{first_key}]")
                    print(f"  Доступные ключи: {list(struct[first_key].keys())}")
        
        # Проверяем text
        if 'text' in parser.processed_data:
            text = parser.processed_data['text']
            print(f"text ключи: {list(text.keys())[:5]}...")
        
        # Парсим документ
        print("\n--- Парсинг документа ---")
        result = parser.parse_document()
        
        print(f"Результат ключи: {list(result.keys())}")
        print(f"Всего страниц в результате: {result.get('total_pages')}")
        
        # Проверяем первую страницу
        pages = result.get('pages', {})
        if pages:
            first_page_key = list(pages.keys())[0]
            first_page = pages[first_page_key]
            print(f"\n--- {first_page_key} ---")
            print(f"Категория: {first_page.get('category')}")
            print(f"Ключи страницы: {list(first_page.keys())}")
            
            # Проверяем text_blocks_details
            if 'text_blocks_details' in first_page:
                blocks = first_page['text_blocks_details']
                print(f"✓ text_blocks_details: {len(blocks)} блоков")
                if blocks:
                    print(f"  Первый блок: {json.dumps(blocks[0], ensure_ascii=False)[:200]}...")
            else:
                print(f"✗ text_blocks_details НЕ найден")
            
            # Проверяем data
            if 'data' in first_page:
                print(f"data ключи: {list(first_page['data'].keys())}")
        
        # Сохраняем результат
        output_path = Path('output/test_result.json')
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\n✓ Результат сохранён: {output_path}")
        print(f"  Откройте файл и проверьте структуру!")

except Exception as e:
    print(f"\n✗ ОШИБКА: {e}")
    import traceback
    traceback.print_exc()
