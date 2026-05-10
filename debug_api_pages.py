import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models

db = SessionLocal()

# Эмулируем API /documents/{id}/pages
document_id = 15

document = db.query(models.Document).get(document_id)
if document is None:
    print("Document not found")
else:
    print(f"Document: {document.name}, project_id={document.project_id}")
    
    pages = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == document_id
    ).order_by(models.DocumentPage.page_number).all()
    
    print(f"Pages found: {len(pages)}")
    
    pages_data = [
        {
            "id": page.id,
            "document_id": page.document_id,
            "page_number": page.page_number,
            "category": page.category,
            "confidence": page.confidence,
            "content_type": page.content_type,
            "page_metadata": page.page_metadata
        }
        for page in pages
    ]
    
    print(f"pages_data length: {len(pages_data)}")
    if pages_data:
        print(f"First page: {pages_data[0]}")
        print(f"Last page: {pages_data[-1]}")

db.close()
