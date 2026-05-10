"""
Сбор данных из БД для дообучения модели LayoutLM

Экспортирует классифицированные страницы в формат, подходящий для обучения.
"""
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models


def collect_training_data(output_path: str = "training_data.json"):
    """
    Собрать данные из БД для дообучения модели
    
    Args:
        output_path: Путь для сохранения JSON файла
    """
    db = SessionLocal()
    
    print("Сбор данных из БД...")
    
    data = []
    
    # Получаем все страницы
    pages = db.query(models.DocumentPage).all()
    print(f"Найдено страниц: {len(pages)}")
    
    for page in pages:
        # Извлекаем информацию
        page_data = {
            "id": page.id,
            "document_id": page.document_id,
            "page_number": page.page_number,
            "category": page.category,
            "confidence": page.confidence,
            "content_type": page.content_type,
            "metadata": page.page_metadata
        }
        
        # Парсим metadata если есть
        if page.page_metadata:
            try:
                metadata = json.loads(page.page_metadata)
                page_data["visual_features"] = metadata.get("visual_features", {})
                page_data["text_length"] = metadata.get("text_length", 0)
                page_data["scores"] = metadata.get("scores", {})
            except:
                pass
        
        data.append(page_data)
    
    # Сохраняем в JSON
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Данные сохранены в: {output_file.absolute()}")
    
    # Статистика
    categories = {}
    for page in data:
        cat = page['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\nРаспределение по категориям:")
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} стр.")
    
    db.close()
    
    return data


def collect_with_documents(output_path: str = "training_data_with_docs.json"):
    """
    Собрать данные вместе с информацией о документах
    """
    db = SessionLocal()
    
    print("Сбор данных с информацией о документах...")
    
    data = []
    
    # Получаем все документы
    documents = db.query(models.Document).all()
    print(f"Найдено документов: {len(documents)}")
    
    for doc in documents:
        pages = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == doc.id
        ).all()
        
        if not pages:
            continue
        
        doc_data = {
            "document_id": doc.id,
            "name": doc.name,
            "project_id": doc.project_id,
            "page_count": doc.page_count,
            "pages": []
        }
        
        for page in pages:
            page_info = {
                "page_number": page.page_number,
                "category": page.category,
                "confidence": page.confidence,
                "content_type": page.content_type
            }
            
            if page.page_metadata:
                try:
                    metadata = json.loads(page.page_metadata)
                    page_info["visual_features"] = metadata.get("visual_features", {})
                except:
                    pass
            
            doc_data["pages"].append(page_info)
        
        data.append(doc_data)
    
    # Сохраняем
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f"Данные сохранены в: {output_file.absolute()}")
    
    db.close()
    
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Сбор данных для дообучения модели")
    parser.add_argument(
        "--output", 
        type=str, 
        default="training_data.json",
        help="Путь для сохранения данных"
    )
    parser.add_argument(
        "--with-docs",
        action="store_true",
        help="Включить информацию о документах"
    )
    
    args = parser.parse_args()
    
    if args.with_docs:
        collect_with_documents(args.output)
    else:
        collect_training_data(args.output)
