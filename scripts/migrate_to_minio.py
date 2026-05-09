"""
Скрипт для миграции старых локальных файлов в MinIO
"""
import sys
import os

# Добавляем корневую директорию в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app import models
from app.services.minio_client import minio_client
import hashlib

def migrate_documents():
    """Мигрировать все документы из локального хранилища в MinIO"""
    db: Session = SessionLocal()
    
    try:
        # Получаем все документы
        documents = db.query(models.Document).all()
        print(f"Найдено документов: {len(documents)}")
        
        migrated = 0
        failed = 0
        
        for doc in documents:
            if not doc.file_path:
                print(f"Документ {doc.id} ({doc.name}): нет file_path - пропускаем")
                continue
            
            # Проверяем, что это локальный путь
            if not doc.file_path.startswith("uploads/"):
                print(f"Документ {doc.id} ({doc.name}): уже в MinIO - пропускаем")
                continue
            
            # Путь к локальному файлу
            local_path = Path(doc.file_path)
            
            if not local_path.exists():
                print(f"Документ {doc.id} ({doc.name}): файл не найден {local_path} - пропускаем")
                failed += 1
                continue
            
            try:
                # Читаем файл
                file_content = local_path.read_bytes()
                file_name = local_path.name
                
                # Загружаем в MinIO
                object_key = minio_client.upload_file(
                    file_content,
                    file_name,
                    doc.project_id
                )
                
                # Обновляем путь в БД
                old_path = doc.file_path
                doc.file_path = f"minio://{object_key}"
                db.commit()
                
                print(f"✓ Документ {doc.id} ({doc.name}): {old_path} -> {doc.file_path}")
                migrated += 1
                
            except Exception as e:
                print(f"✗ Документ {doc.id} ({doc.name}): ошибка {e}")
                failed += 1
                db.rollback()
        
        print(f"\nРезультат:")
        print(f"  Успешно мигрировано: {migrated}")
        print(f"  Ошибок: {failed}")
        
    finally:
        db.close()

if __name__ == "__main__":
    migrate_documents()
