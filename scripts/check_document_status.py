"""
Скрипт для проверки статуса документа: классификация страниц, processed файлы.

Использование:
    python scripts/check_document_status.py <document_id>
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app import models, crud


def check_document_status(document_id: int):
    """Проверить статус документа"""
    db = SessionLocal()
    
    try:
        # Получаем документ
        document = crud.Documents.get(db, document_id)
        if not document:
            print(f"❌ Документ с ID {document_id} не найден")
            return
        
        print("=" * 70)
        print(f"СТАТУС ДОКУМЕНТА: {document.name}")
        print("=" * 70)
        print(f"ID: {document.id}")
        print(f"Проект: {document.project_id}")
        print(f"Дата создания: {document.created_at}")
        print(f"Страниц: {document.page_count or 0}")
        print(f"Файл: {document.file_path or 'Нет файла'}")
        
        # Проверка классификации страниц
        print("\n" + "-" * 70)
        print("КЛАССИФИКАЦИЯ СТРАНИЦ")
        print("-" * 70)
        
        pages = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == document_id
        ).order_by(models.DocumentPage.page_number).all()
        
        if not pages:
            print("❌ Страницы не классифицированы")
            print("   Решение: Переклассифицируйте документ через интерфейс или API")
        else:
            # Группировка по категориям
            categories = {}
            for page in pages:
                cat = page.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(page)
            
            print(f"✅ Классифицировано страниц: {len(pages)}")
            print(f"\nКатегории:")
            for cat, cat_pages in categories.items():
                page_nums = [str(p.page_number) for p in cat_pages]
                avg_conf = sum(p.confidence for p in cat_pages) / len(cat_pages)
                print(f"  {cat:20s}: {len(cat_pages):2d} стр. (стр. {', '.join(page_nums[:10])}{'...' if len(page_nums) > 10 else ''})")
                print(f"                    Средняя уверенность: {avg_conf:.1%}")
        
        # Проверка processed файлов
        print("\n" + "-" * 70)
        print("PROCESSED ФАЙЛЫ")
        print("-" * 70)
        
        doc_name = Path(document.name).stem
        processed_dir = Path('processed')
        
        found_files = []
        if processed_dir.exists():
            for json_file in processed_dir.glob("**/*_processed.json"):
                if doc_name in json_file.stem or str(document_id) in json_file.stem:
                    found_files.append(json_file)
        
        if not found_files:
            print("❌ Processed файлы не найдены")
            print("   Решение: Переобработайте документ через pdf_processor")
            print(f"   Команда: python -m app.services.pdf_processor <путь_к_pdf> processed/")
        else:
            print(f"✅ Найдено processed файлов: {len(found_files)}")
            for json_file in found_files:
                file_size = json_file.stat().st_size
                file_size_mb = file_size / (1024 * 1024)
                print(f"\n  Файл: {json_file}")
                print(f"  Размер: {file_size_mb:.2f} MB")
                
                # Проверка валидности JSON
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  ✅ JSON валиден")
                    
                    # Проверка структуры
                    if 'text' in data:
                        text_pages = len(data.get('text', {}))
                        print(f"  Страниц с текстом: {text_pages}")
                    
                    if 'metadata' in data:
                        metadata = data['metadata']
                        print(f"  Страниц в metadata: {metadata.get('page_count', 0)}")
                        
                except json.JSONDecodeError as e:
                    print(f"  ❌ JSON повреждён: {e}")
                except Exception as e:
                    print(f"  ❌ Ошибка чтения: {e}")
        
        # Итоговая рекомендация
        print("\n" + "=" * 70)
        print("РЕКОМЕНДАЦИИ")
        print("=" * 70)
        
        issues = []
        
        if not pages:
            issues.append("❌ Страницы не классифицированы")
        
        if not found_files:
            issues.append("❌ Processed файл не найден")
        
        spec_pages = [p for p in pages if p.category == 'specification']
        if not spec_pages:
            issues.append("❌ Нет страниц со спецификациями (category='specification')")
        
        if issues:
            print("\nОбнаружены проблемы:")
            for issue in issues:
                print(f"  {issue}")
            
            print("\nДействия:")
            if "Страницы не классифицированы" in str(issues):
                print("  1. Переклассифицируйте документ:")
                print("     - Через интерфейс: кнопка 'Переклассифицировать'")
                print("     - Через API: POST /api/documents/{id}/classify")
            
            if "Processed файл не найден" in str(issues):
                print("  2. Переобработайте PDF:")
                print("     python -m app.services.pdf_processor <путь_к_pdf> processed/")
            
            if "Нет страниц со спецификациями" in str(issues):
                print("  3. Проверьте категории страниц:")
                print("     - Возможно документ не содержит спецификаций")
                print("     - Или страницы неправильно классифицированы")
        else:
            print("\n✅ Документ готов к парсингу спецификаций!")
            print(f"   Найдено {len(spec_pages)} страниц со спецификациями")
            print("\nЭкспорт:")
            print("  - Через интерфейс: кнопка 'Спецификации' → 'Экспорт в Excel'")
            print("  - Через API: POST /api/documents/{id}/parse-specifications?format=excel")
            print("  - Через CLI: python scripts/parse_specifications.py --document {id} excel")
        
    finally:
        db.close()


def main():
    """Главная функция"""
    print("\n🔍 ПРОВЕРКА СТАТУСА ДОКУМЕНТА\n")
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/check_document_status.py <document_id>\n")
        print("Пример:")
        print("  python scripts/check_document_status.py 24\n")
        sys.exit(1)
    
    try:
        document_id = int(sys.argv[1])
        check_document_status(document_id)
    except ValueError:
        print(f"❌ Неверный ID документа: {sys.argv[1]}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()