"""
Скрипт для извлечения страниц PDF и загрузки их в MinIO как отдельные изображения.

Использование:
    python scripts/extract_pdf_pages.py <document_id>
"""

import sys
import io
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import SessionLocal
from app import models, crud
from app.services.minio_client import MinIOClient


def extract_pages_to_minio(document_id: int):
    """Извлечь все страницы PDF в изображения и загрузить в MinIO"""
    db = SessionLocal()
    client = MinIOClient()
    
    try:
        # Получаем документ
        document = crud.Documents.get(db, document_id)
        if not document:
            print(f"❌ Документ с ID {document_id} не найден")
            return False
        
        print("=" * 70)
        print(f"ИЗВЛЕЧЕНИЕ СТРАНИЦ PDF")
        print("=" * 70)
        print(f"Документ: {document.name}")
        print(f"ID: {document_id}")
        
        # Проверяем файл
        if not document.file_path:
            print(f"❌ У документа нет файла")
            return False
        
        # Получаем object_key
        if document.file_path.startswith("minio://"):
            object_key = document.file_path.replace("minio://", "")
        else:
            object_key = document.file_path
        
        if object_key.startswith("documents/"):
            object_key = object_key.replace("documents/", "", 1)
        
        print(f"\nObject key: {object_key}")
        
        # Скачиваем PDF из MinIO
        print(f"\n1. Скачивание PDF из MinIO...")
        try:
            pdf_content = client.download_file(object_key)
            print(f"   ✅ Скачано: {len(pdf_content)} bytes")
        except Exception as e:
            print(f"   ❌ Ошибка скачивания: {e}")
            return False
        
        # Открываем PDF
        print(f"\n2. Открытие PDF...")
        try:
            import fitz  # PyMuPDF
            pdf_doc = fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf")
            page_count = len(pdf_doc)
            print(f"   ✅ Страниц в PDF: {page_count}")
        except Exception as e:
            print(f"   ❌ Ошибка открытия PDF: {e}")
            return False
        
        # Создаём директорию для страниц
        pages_key = f"{object_key.rsplit('/', 1)[0]}/pages"
        print(f"\n3. Извлечение страниц в: {pages_key}")
        
        # Извлекаем каждую страницу
        success_count = 0
        for page_num in range(page_count):
            page = pdf_doc[page_num]
            
            # Рендерим страницу в PNG (150 DPI)
            mat = fitz.Matrix(1.5, 1.5)  # Масштаб 150% для лучшего качества
            pix = page.get_pixmap(matrix=mat)
            
            # Получаем байты изображения
            img_bytes = pix.tobytes("png")
            
            # Формируем object key для изображения
            img_key = f"{pages_key}/page_{page_num + 1}.png"
            
            # Загружаем в MinIO
            try:
                client.client.put_object(
                    Bucket=client.bucket_name,
                    Key=img_key,
                    data=io.BytesIO(img_bytes),
                    length=len(img_bytes),
                    content_type='image/png'
                )
                success_count += 1
                print(f"   ✅ Стр. {page_num + 1}/{page_count}: {len(img_bytes)} bytes")
            except Exception as e:
                print(f"   ❌ Стр. {page_num + 1}/{page_count}: Ошибка загрузки - {e}")
        
        # Закрываем PDF
        pdf_doc.close()
        
        print(f"\n" + "=" * 70)
        print(f"ГОТОВО!")
        print("=" * 70)
        print(f"Извлечено страниц: {success_count}/{page_count}")
        print(f"\nИзображения доступны по URL:")
        print(f"  {pages_key}/page_1.png")
        print(f"  {pages_key}/page_2.png")
        print(f"  ...")
        
        return True
        
    finally:
        db.close()


def main():
    print("\n📄 ИЗВЛЕЧЕНИЕ СТРАНИЦ PDF\n")
    
    if len(sys.argv) < 2:
        print("Использование:")
        print("  python scripts/extract_pdf_pages.py <document_id>\n")
        print("Пример:")
        print("  python scripts/extract_pdf_pages.py 27\n")
        sys.exit(1)
    
    try:
        document_id = int(sys.argv[1])
        success = extract_pages_to_minio(document_id)
        
        if not success:
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
