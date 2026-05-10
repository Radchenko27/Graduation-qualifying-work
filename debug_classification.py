import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models

db = SessionLocal()

# Проверяем все документы и их страницы
docs = db.query(models.Document).all()
print(f"Всего документов: {len(docs)}")

for doc in docs:
    pages = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == doc.id
    ).all()
    print(f"\nДокумент '{doc.name}' (id={doc.id}):")
    print(f"  file_path: {doc.file_path}")
    print(f"  page_count: {doc.page_count}")
    print(f"  Классифицировано страниц: {len(pages)}")
    for p in pages:
        print(f"    Стр.{p.page_number}: {p.category} (confidence={p.confidence:.2f})")

db.close()
