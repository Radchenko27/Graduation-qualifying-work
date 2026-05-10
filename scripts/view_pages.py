"""
Просмотр всех страниц с категориями

Показать все страницы и их категории для проверки.
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models

db = SessionLocal()

print("=" * 80)
print("ВСЕ СТРАНИЦЫ И ЕГО КАТЕГОРИИ")
print("=" * 80)

pages = db.query(models.DocumentPage).order_by(
    models.DocumentPage.document_id,
    models.DocumentPage.page_number
).all()

for page in pages:
    doc = db.query(models.Document).filter(models.Document.id == page.document_id).first()
    doc_name = doc.name if doc else f"Doc {page.document_id}"
    
    # Показать metadata если есть
    meta = ""
    if page.page_metadata:
        try:
            m = json.loads(page.page_metadata)
            vf = m.get('visual_features', {})
            meta = f" | images:{vf.get('image_count', 0)} table:{vf.get('has_table', False)}"
        except:
            pass
    
    print(f"{doc_name:45s} | Стр.{page.page_number:2d} | {page.category:15s} | {page.confidence:.2f}{meta}")

print("=" * 80)
print(f"Всего страниц: {len(pages)}")

db.close()
