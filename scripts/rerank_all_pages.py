"""
Переклассификация всех страниц документов с улучшенным классификатором

Обновляет таблицу document_pages с новыми результатами классификации.
"""
import os
import sys
import json
from pathlib import Path
from tqdm import tqdm

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models
from app.services.document_classifier_v2 import classifier
from app.services.minio_client import minio_client


def rerank_document(db, doc: models.Document) -> int:
    """
    Переклассифицировать один документ
    
    Args:
        db: Сессия БД
        doc: Document объект
        
    Returns:
        Количество обновлённых страниц
    """
    print(f"\nОбработка документа: {doc.name}")
    
    # Скачать PDF из MinIO
    try:
        pdf_content = minio_client.get_file(doc.file_path)
        if not pdf_content:
            print(f"  [!] Файл не найден в MinIO: {doc.file_path}")
            return 0
    except Exception as e:
        print(f"  [!] Ошибка загрузки файла: {e}")
        return 0
    
    # Классификация
    print(f"  Классификация {doc.page_count} страниц...")
    classifications = classifier.classify_pdf_pages(pdf_content)
    
    # Обновить страницы
    updated_count = 0
    for classification in classifications:
        # Найти страницу в БД
        page = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == doc.id,
            models.DocumentPage.page_number == classification.page_number
        ).first()
        
        if not page:
            print(f"  [!] Страница {classification.page_number} не найдена")
            continue
        
        # Обновить данные
        old_category = page.category
        page.category = classification.category
        page.confidence = classification.confidence
        page.content_type = classification.content_type
        page.page_metadata = json.dumps({
            'visual_features': classification.metadata.get('visual_features', {}),
            'text_length': classification.metadata.get('text_length', 0),
            'word_count': classification.metadata.get('word_count', 0),
            'scores': classification.metadata.get('scores', {}),
            'ml_confidence': classification.metadata.get('ml_confidence', 0)
        }, ensure_ascii=False)
        
        # Показать изменения
        if old_category != classification.category:
            print(f"    Стр.{classification.page_number}: {old_category} → {classification.category} ({classification.confidence:.1%})")
        else:
            print(f"    Стр.{classification.page_number}: {classification.category} ({classification.confidence:.1%})")
        
        updated_count += 1
    
    db.commit()
    print(f"  ✓ Обновлено: {updated_count} страниц")
    
    return updated_count


def rerank_all_documents():
    """Переклассифицировать все документы"""
    db = SessionLocal()
    
    print("=" * 60)
    print("ПЕРЕКЛАССИФИКАЦИЯ ВСЕХ СТРАНИЦ")
    print("=" * 60)
    
    # Получить все документы
    documents = db.query(models.Document).all()
    print(f"\nВсего документов: {len(documents)}")
    
    total_updated = 0
    
    for doc in documents:
        updated = rerank_document(db, doc)
        total_updated += updated
    
    print("\n" + "=" * 60)
    print(f"ГОТОВО! Обновлено страниц: {total_updated}")
    print("=" * 60)
    
    # Статистика
    pages = db.query(models.DocumentPage).all()
    from collections import Counter
    categories = Counter(p.category for p in pages)
    
    print("\nНовое распределение:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count} стр. ({count/len(pages)*100:.1f}%)")
    
    db.close()


if __name__ == "__main__":
    print("⚠️  Внимание: это действие перезапишет текущую классификацию!")
    response = input("Продолжить? (yes/no): ").strip().lower()
    
    if response != 'yes':
        print("Отменено")
        sys.exit(0)
    
    rerank_all_documents()
