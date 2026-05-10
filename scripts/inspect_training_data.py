"""
Просмотр данных для обучения ML модели
"""
import os
import sys
import json
from pathlib import Path
from collections import Counter

# Добавляем корень проекта в path
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models

db = SessionLocal()

print("=" * 60)
print("АНАЛИЗ ДАННЫХ ДЛЯ ОБУЧЕНИЯ ML МОДЕЛИ")
print("=" * 60)

# Все страницы
pages = db.query(models.DocumentPage).all()
print(f"\nВсего страниц: {len(pages)}")

# Распределение по категориям
categories = Counter(p.category for p in pages)
print("\nРаспределение по категориям:")
for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
    percent = count / len(pages) * 100
    print(f"  {cat:20s}: {count:3d} стр. ({percent:5.1f}%)")

# Распределение по документам
docs = db.query(models.Document).all()
print(f"\nВсего документов: {len(docs)}")

print("\nДокументы и их страницы:")
for doc in docs:
    doc_pages = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == doc.id
    ).all()
    
    doc_categories = Counter(p.category for p in doc_pages)
    print(f"  {doc.name[:40]:40s}: {len(doc_pages):3d} стр., {doc_categories}")

# Пример metadata
print("\n" + "=" * 60)
print("ПРИМЕРЫ METADATA")
print("=" * 60)

for i, page in enumerate(pages[:3]):
    print(f"\nСтр. {page.document_id}-{page.page_number}:")
    print(f"  Категория: {page.category}")
    print(f"  Уверенность: {page.confidence:.2f}")
    print(f"  content_type: {page.content_type}")
    
    if page.page_metadata:
        try:
            metadata = json.loads(page.page_metadata)
            vf = metadata.get('visual_features', {})
            print(f"  Визуальные признаки:")
            print(f"    images: {vf.get('image_count', 0)}")
            print(f"    has_table: {vf.get('has_table', False)}")
            print(f"    has_signatures: {vf.get('has_signatures', False)}")
        except Exception as e:
            print(f"  Ошибка парсинга metadata: {e}")

# Проверка качества данных
print("\n" + "=" * 60)
print("КАЧЕСТВО ДАННЫХ")
print("=" * 60)

# Страницы без metadata
no_metadata = [p for p in pages if not p.page_metadata]
print(f"\nСтраниц без metadata: {len(no_metadata)} ({len(no_metadata)/len(pages)*100:.1f}%)")

# Страницы с confidence < 0.5
low_confidence = [p for p in pages if p.confidence < 0.5]
print(f"Страниц с низкой уверенностью (<0.5): {len(low_confidence)}")

# Рекомендации
print("\n" + "=" * 60)
print("РЕКОМЕНДАЦИИ")
print("=" * 60)

if len(pages) < 50:
    print("\n⚠️  НЕДОСТАТОЧНО ДАННЫХ!")
    print("Нужно минимум 50 страниц для обучения")
elif len(pages) < 200:
    print("\n✓ Достаточно данных для базового обучения")
    print("Для лучшей точности соберите 200+ страниц")
else:
    print("\n✓ Отличное количество данных для обучения!")

# Проверка баланса
max_percent = max(count/len(pages)*100 for count in categories.values())
if max_percent > 70:
    print(f"\n⚠️  ДИСБАЛАНС КЛАССОВ!")
    print(f"Один класс занимает {max_percent:.1f}% (норма <70%)")
    print("Модель будет смещена в сторону доминирующего класса")
else:
    print("\n✓ Баланс классов нормальный")

db.close()
