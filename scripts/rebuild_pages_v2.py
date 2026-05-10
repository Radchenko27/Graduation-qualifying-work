"""
Пересоздание document_pages с улучшенным классификатором v2

Использует:
- Парсинг основной надписи (штампа)
- Ключевые слова из текста
- Визуальные признаки

НЕ использует оценки старого rule-based!
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models
from app.services.minio_client import minio_client
from app.services.document_classifier_v2 import classifier


def process_document(db, doc: models.Document) -> dict:
    """Обработать один документ"""
    print(f"\n{'='*60}")
    print(f"Документ: {doc.name}")
    print(f"{'='*60}")
    
    # Скачать PDF
    try:
        # Убрать префикс minio:// если есть
        object_key = doc.file_path.replace("minio://", "") if doc.file_path.startswith("minio://") else doc.file_path
        pdf_content = minio_client.download_file(object_key)
        if not pdf_content:
            print(f"  [!] Файл не найден: {object_key}")
            return {'updated': 0, 'errors': 1}
    except Exception as e:
        print(f"  [!] Ошибка загрузки: {e}")
        return {'updated': 0, 'errors': 1}
    
    # Классификация
    try:
        classifications = classifier.classify_pdf_pages(pdf_content)
    except Exception as e:
        print(f"  [!] Ошибка классификации: {e}")
        return {'updated': 0, 'errors': 1}
    
    # Удалить старые страницы
    old_count = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == doc.id
    ).delete()
    print(f"  Удалено старых страниц: {old_count}")
    
    # Создать новые
    updated = 0
    for cl in classifications:
        page = models.DocumentPage(
            document_id=doc.id,
            page_number=cl.page_number,
            category=cl.category,
            confidence=cl.confidence,
            content_type=cl.content_type,
            page_metadata=json.dumps(cl.metadata, ensure_ascii=False)
        )
        db.add(page)
        updated += 1
        
        # Показать результат
        stamp_info = ""
        if cl.metadata.get('stamp_features', {}).get('has_stamp'):
            stamp = cl.metadata['stamp_features']
            detected = []
            if stamp.get('stamp_drawing'): detected.append('drawing')
            if stamp.get('stamp_specification'): detected.append('spec')
            if stamp.get('stamp_scheme'): detected.append('scheme')
            if detected:
                stamp_info = f" [штамп: {','.join(detected)}]"
        
        print(f"  Стр.{cl.page_number:2d}: {cl.category:15s} ({cl.confidence:.1%}){stamp_info}")
    
    db.commit()
    print(f"  Добавлено новых страниц: {updated}")
    
    return {'updated': updated, 'errors': 0}


def main():
    db = SessionLocal()
    
    print("ПЕРЕСОЗДАНИЕ DOCUMENT_PAGES С УЛУЧШЕННЫМ КЛАССИФИКАТОРОМ")
    print("=" * 60)
    print("\nЧто нового:")
    print("  - Парсинг основной надписи (штампа)")
    print("  - Ключевые слова из текста (без оценок rule-based)")
    print("  - Визуальные признаки")
    print("\nВНИМАНИЕ: Это перезапишет текущую классификацию!")
    
    response = input("\nПродолжить? (yes/no): ").strip().lower()
    if response != 'yes':
        print("Отменено")
        db.close()
        return
    
    documents = db.query(models.Document).all()
    print(f"\nВсего документов: {len(documents)}")
    
    total_updated = 0
    total_errors = 0
    
    for doc in documents:
        result = process_document(db, doc)
        total_updated += result['updated']
        total_errors += result['errors']
    
    print("\n" + "=" * 60)
    print("ИТОГО")
    print("=" * 60)
    print(f"Обновлено страниц: {total_updated}")
    print(f"Ошибок: {total_errors}")
    
    # Статистика
    pages = db.query(models.DocumentPage).all()
    from collections import Counter
    cats = Counter(p.category for p in pages)
    
    print("\nРаспределение по категориям:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} стр. ({count/len(pages)*100:.1f}%)")
    
    db.close()
    print("\nГотово!")


if __name__ == "__main__":
    main()
