"""
Скрипт для переобработки PDF файла конкретного документа.

Использование:
    python scripts/reprocess_document.py <document_id>
"""

import sys
from pathlib import Path

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app import models, crud
from app.services import pdf_processor


def reprocess_document(document_id: int):
    """Переобработать PDF файл документа"""
    db = SessionLocal()
    
    try:
        # Получаем документ
        document = crud.Documents.get(db, document_id)
        if not document:
            print(f"❌ Документ с ID {document_id} не найден")
            return False
        
        print("=" * 70)
        print(f"ПЕРЕОБРАБОТКА ДОКУМЕНТА: {document.name}")
        print("=" * 70)
        print(f"ID: {document.id}")
        print(f"Проект: {document.project_id}")
        print(f"Файл: {document.file_path or 'Нет файла'}")
        
        # Проверяем путь к файлу
        if not document.file_path:
            print(f"\n❌ Ошибка: У документа не указан путь к файлу")
            return False
        
        pdf_path = Path(document.file_path)
        if not pdf_path.exists():
            print(f"\n❌ Ошибка: PDF файл не найден: {pdf_path}")
            return False
        
        print(f"\n✅ PDF файл найден: {pdf_path}")
        print(f"Размер: {pdf_path.stat().st_size / (1024*1024):.2f} MB")
        
        # Определяем директорию для processed файлов
        processed_dir = Path('processed')
        processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Создаём поддиректорию для документа
        doc_output_dir = processed_dir / f"{document.id}_{Path(document.name).stem}"
        doc_output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Output directory: {doc_output_dir}")
        
        # Запускаем обработку
        print("\n⏳ Запуск обработки PDF...")
        
        try:
            result = pdf_processor.process_pdf(
                pdf_path=str(pdf_path),
                output_dir=str(doc_output_dir),
                extract_text=True,
                extract_tables=True,
                extract_images=False
            )
            
            if result.get('success'):
                print(f"\n✅ Обработка успешна!")
                print(f"\nРезультаты:")
                print(f"  Страниц: {result.get('page_count', 0)}")
                print(f"  Времени: {result.get('processing_time', 0):.2f} сек")
                print(f"  Output: {result.get('output_file', 'N/A')}")
                
                return True
            else:
                print(f"\n❌ Ошибка обработки: {result.get('error', 'Неизвестная ошибка')}")
                return False
                
        except Exception as e:
            print(f"\n❌ Исключение при обработке: {e}")
            import traceback
            traceback.print_exc()
            return False
        
    finally:
        db.close()


def main():
    """Главная функция"""
    print("\n🔄 ПЕРЕОБРАБОТКА PDF ДОКУМЕНТА\n")
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/reprocess_document.py <document_id>\n")
        print("Пример:")
        print("  python scripts/reprocess_document.py 24\n")
        sys.exit(1)
    
    try:
        document_id = int(sys.argv[1])
        success = reprocess_document(document_id)
        
        if success:
            print("\n" + "=" * 70)
            print("✅ ГОТОВО!")
            print("=" * 70)
            print("\nТеперь можно парсить спецификации:")
            print("  - Через интерфейс: кнопка 'Спецификации'")
            print("  - Через API: POST /api/documents/{id}/parse-specifications?format=excel")
            print("  - Через CLI: python scripts/parse_specifications.py --document {id} excel")
        else:
            print("\n❌ Обработка не удалась")
            sys.exit(1)
            
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