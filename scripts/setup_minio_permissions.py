"""
Скрипт для настройки прав доступа к MinIO бакету
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.minio_client import minio_client

print("=" * 60)
print("MinIO Bucket Permissions Setup")
print("=" * 60)

bucket_name = minio_client.bucket_name
print(f"Bucket: {bucket_name}")

# Проверяем существование бакета
try:
    exists = minio_client.client.bucket_exists(bucket_name)
    print(f"[OK] Bucket exists: {exists}")
except Exception as e:
    print(f"[ERROR] Cannot check bucket: {e}")
    exit(1)

# Проверяем политику доступа
try:
    # Получаем список объектов в бакете
    objects = minio_client.client.list_objects(bucket_name, recursive=True)
    object_list = list(objects)
    print(f"[OK] Objects in bucket: {len(object_list)}")
    
    if len(object_list) > 0:
        print("Sample objects:")
        for obj in object_list[:5]:
            print(f"  - {obj.object_name} ({obj.size} bytes)")
except Exception as e:
    print(f"[ERROR] Cannot list objects: {e}")
    print("This might mean the bucket is private or credentials are wrong")

# Пробуем установить публичный доступ (не рекомендуется для production)
print("\n[NOTE] To make bucket publicly readable:")
print("  docker exec minio_storage mc anonymous set download myminio/documents")
print("Or set policy via MinIO Console: http://localhost:9001")

print("\n" + "=" * 60)
