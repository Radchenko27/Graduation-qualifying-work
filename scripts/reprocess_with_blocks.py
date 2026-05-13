"""
Переобработка документа с text_blocks_details.

Использование:
    python scripts/reprocess_with_blocks.py <document_id>
"""
import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from app.db import SessionLocal
from app import crud, models
from app.services.pdf_processor import PDFProcessor

def reprocess_document(document_id: int):
    """Переобработать PDF с text_blocks_details"""
    db = SessionLocal()
    
    try:
        document = crud.Documents.get(db, document_id)
        if not document:
            print(f"❌ Документ {document_id} не найден")
            return False
        
        if not document.file_path:
            print(f"❌ У документа нет file_path")
            return False
        
        print("=" * 70)
        print(f"ПЕРЕОБРАБОТКА ДОКУМЕНТА {document_id}")
        print("=" * 70)
        print(f"Название: {document.name}")
        print(f"Файл: {document.file_path}")
        
        # Скачиваем PDF из MinIO
        object_key = document.file_path.replace("minio://", "")
        if object_key.startswith("documents/"):
            object_key = object_key.replace("documents/", "", 1)
        
        from app.services.minio_client import minio_client
        pdf_content = minio_client.download_file(object_key)
        
        # Создаём временный файл
        temp_pdf = Path('temp_reprocess.pdf')
        with open(temp_pdf, 'wb') as f:
            f.write(pdf_content)
        
        print(f"✓ PDF загружён: {temp_pdf} ({len(pdf_content) / 1024 / 1024:.2f} MB)")
        
        # Обрабатываем через PDFDataExtractor
        output_dir = Path('processed') / f"{document_id}_{Path(document.name).stem}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📄 Обработка PDF...")
        print(f"  Выходная директория: {output_dir}")
        
        processor = PDFProcessor(str(temp_pdf))
        
        result = processor.process_document(
            output_dir=output_dir,
            extract_images=False,
            extract_text=True,
            analyze_structure=True,  # ВАЖНО: всегда True для text_blocks_details
            zoom=1.0
        )
        
        processor.close()
        
        # Удаляем временный файл
        temp_pdf.unlink()
        
        # Проверяем результат
        json_files = list(output_dir.glob("*_processed.json"))
        if json_files:
            json_file = json_files[0]
            print(f"\n✓ Обработка завершена")
            print(f"  Файл: {json_file.name}")
            print(f"  Размер: {json_file.stat().st_size / 1024 / 1024:.2f} MB")
            
            # Проверяем наличие text_blocks_details
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'structure' in data and data['structure']:
                first_page = list(data['structure'].values())[0]
                if 'text_blocks_details' in first_page:
                    blocks_count = len(first_page['text_blocks_details'])
                    print(f"  ✓ text_blocks_details: {blocks_count} блоков на странице")
                    print(f"\n🎉 Готово! Теперь парсер будет использовать геометрические данные")
                else:
                    print(f"  ⚠ text_blocks_details НЕ найден!")
            else:
                print(f"  ⚠ structure НЕ найден!")
            
            return True
        else:
            print(f"❌ JSON файл не создан")
            return False
            
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Использование: python scripts/reprocess_with_blocks.py <document_id>")
        print("Пример: python scripts/reprocess_with_blocks.py 32")
        sys.exit(1)
    
    doc_id = int(sys.argv[1])
    success = reprocess_document(doc_id)
    sys.exit(0 if success else 1)
