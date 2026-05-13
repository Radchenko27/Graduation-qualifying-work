"""
Прямая проверка DocumentParser.parse_document() без сервера.
Запуск: python test_direct_parse.py <document_id>
"""
import sys
import json
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, '.')

def test_parse_document(doc_id):
    from app.utils.document_parser import DocumentParser
    
    print(f"Тестируем DocumentParser для документа ID={doc_id}")
    print("=" * 70)
    
    try:
        with DocumentParser(doc_id, processed_dir='processed') as parser:
            print(f"✓ DocumentParser создан")
            print(f"  Документ: {parser.document.name}")
            print(f"  Страниц в БД: {len(parser.all_pages)}")
            
            # Парсим
            result = parser.parse_document()
            
            # Проверяем структуру
            print(f"\n✓ Парсинг завершён")
            print(f"  Ключи результата: {list(result.keys())}")
            
            if 'pages' in result:
                pages = result['pages']
                print(f"  Страниц в результате: {len(pages)}")
                
                # Проверяем первую страницу
                if pages:
                    first_key = list(pages.keys())[0]
                    first_page = pages[first_key]
                    print(f"\n  --- {first_key} ---")
                    print(f"  Ключи страницы: {list(first_page.keys())}")
                    print(f"  Категория: {first_page.get('category')}")
                    
                    # Проверяем text_blocks_details
                    if 'text_blocks_details' in first_page:
                        blocks = first_page['text_blocks_details']
                        print(f"  ✓ text_blocks_details: {len(blocks)} блоков")
                    else:
                        print(f"  ⚠ text_blocks_details: нет (будет текстовый fallback)")
                    
                    # Проверяем data
                    if 'data' in first_page:
                        print(f"  ✓ data: {list(first_page['data'].keys())}")
            
            # Сохраняем результат для просмотра
            output_file = f"test_parse_result_doc{doc_id}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            
            print(f"\n✓ Результат сохранён: {output_file}")
            print(f"  Откройте файл и проверьте структуру!")
            
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python test_direct_parse.py <document_id>")
        print("Пример: python test_direct_parse.py 32")
        sys.exit(1)
    
    doc_id = int(sys.argv[1])
    test_parse_document(doc_id)
