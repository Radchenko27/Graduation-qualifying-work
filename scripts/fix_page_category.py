"""
Ручная корректировка категории страницы

Пример:
    python scripts/fix_page_category.py --document 16 --page 3 --category specification
"""
import os
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models


def fix_page(document_id: int, page_number: int, category: str):
    """Исправить категорию страницы"""
    db = SessionLocal()
    
    page = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == document_id,
        models.DocumentPage.page_number == page_number
    ).first()
    
    if not page:
        print(f"[!] Страница {document_id}-{page_number} не найдена")
        db.close()
        return
    
    old_category = page.category
    page.category = category
    
    db.commit()
    print(f"✓ Исправлено: {document_id}-{page_number}: {old_category} → {category}")
    
    db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Исправить категорию страницы")
    parser.add_argument("--document", type=int, required=True, help="ID документа")
    parser.add_argument("--page", type=int, required=True, help="Номер страницы")
    parser.add_argument("--category", type=str, required=True, 
                       choices=['drawing', 'specification', 'scheme', 'title', 'other'],
                       help="Новая категория")
    
    args = parser.parse_args()
    fix_page(args.document, args.page, args.category)
