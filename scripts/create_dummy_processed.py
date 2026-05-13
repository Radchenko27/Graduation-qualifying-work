"""
Создание заглушки processed JSON файла для тестирования.

Использование:
    python scripts/create_dummy_processed.py <document_id> <page_count>
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app import models, crud


def create_dummy_processed(document_id: int, page_count: int = 14):
    """Создать заглушку processed JSON файла"""
    db = SessionLocal()
    
    try:
        # Получаем документ
        document = crud.Documents.get(db, document_id)
        if not document:
            print(f"❌ Документ с ID {document_id} не найден")
            return False
        
        print("=" * 70)
        print(f"СОЗДАНИЕ DUMMY PROCESSED ФАЙЛА")
        print("=" * 70)
        print(f"Документ: {document.name}")
        print(f"ID: {document_id}")
        print(f"Страниц: {page_count}")
        
        # Создаём processed директорию
        processed_dir = Path('processed') / f"{document_id}_{Path(document.name).stem}"
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаём заглушку данных
        dummy_data = {
            "metadata": {
                "document_id": document_id,
                "document_name": document.name,
                "page_count": page_count,
                "processed_at": datetime.now().isoformat(),
                "processor_version": "1.0.0-dummy"
            },
            "text": {},
            "tables": {},
            "images": {}
        }
        
        # Создаём заглушку текста для каждой страницы
        for page_num in range(page_count):
            # Генерируем текст в зависимости от категории страницы
            page = db.query(models.DocumentPage).filter(
                models.DocumentPage.document_id == document_id,
                models.DocumentPage.page_number == page_num + 1
            ).first()
            
            if page:
                category = page.category
                confidence = page.confidence
            else:
                category = "unknown"
                confidence = 0.0
            
            # Генерируем текст для страницы со спецификацией
            if category == "specification":
                text = f"""СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ

Позиция    Обозначение        Наименование                          Кол-во    Ед.изм.    Примечание
1          Э1.00.00.000       Электродвигатель асинхронный          2         шт.        Основное
2          К1.00.00.000       Контактор магнитный                   4         шт.        
3          Р1.00.00.000       Реле промежуточное                    6         шт.        
4          АВ1.00.00.000      Автоматический выключатель            3         шт.        
5          Т1.00.00.000       Трансформатор тока                    8         шт.        
"""
            elif category == "title_page":
                text = f"""ТИТУЛЬНЫЙ ЛИСТ
Проект: {document.name}
Страница {page_num + 1} из {page_count}
"""
            elif category == "general_info":
                text = f"""ОБЩАЯ ИНФОРМАЦИЯ
Документ: {document.name}
Страница {page_num + 1}
"""
            else:
                text = f"""Страница {page_num + 1}
Категория: {category}
Документ: {document.name}
"""
            
            dummy_data["text"][str(page_num)] = text
            dummy_data["tables"][str(page_num)] = []
            dummy_data["images"][str(page_num)] = []
        
        # Сохраняем файл
        output_file = processed_dir / f"{document_id}_{Path(document.name).stem}_processed.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dummy_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ Файл создан: {output_file}")
        print(f"Размер: {output_file.stat().st_size / 1024:.2f} KB")
        
        return True
        
    finally:
        db.close()


def main():
    """Главная функция"""
    print("\n📄 СОЗДАНИЕ DUMMY PROCESSED ФАЙЛА\n")
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/create_dummy_processed.py <document_id> [page_count]\n")
        print("Пример:")
        print("  python scripts/create_dummy_processed.py 24 14\n")
        sys.exit(1)
    
    try:
        document_id = int(sys.argv[1])
        page_count = int(sys.argv[2]) if len(sys.argv) > 2 else 14
        
        success = create_dummy_processed(document_id, page_count)
        
        if success:
            print("\n" + "=" * 70)
            print("✅ ГОТОВО!")
            print("=" * 70)
            print("\nТеперь можно парсить спецификации:")
            print("  - Через интерфейс: кнопка 'Спецификации'")
            print("  - Через API: POST /api/documents/{id}/parse-specifications?format=excel")
            print("  - Через CLI: python scripts/parse_specifications.py --document {id} excel")
        else:
            print("\n❌ Ошибка создания файла")
            sys.exit(1)
            
    except ValueError:
        print(f"❌ Неверный аргумент")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()