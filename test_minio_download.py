"""
Проверка работы с MinIO
"""
from app.services.minio_client import minio_client

print("=" * 50)
print("MinIO Client Test")
print("=" * 50)
print(f"Bucket: {minio_client.bucket_name}")
print(f"Endpoint: {minio_client.client.meta.endpoint_url}")

# Проверка существования файла
object_key = "documents/3/17-23-00-ЭОМ.pdf"
print(f"\nПроверка файла: {object_key}")

try:
    exists = minio_client.file_exists(object_key)
    print(f"Файл существует: {exists}")
    
    if exists:
        # Скачиваем
        print("\nСкачивание файла...")
        content = minio_client.download_file(object_key)
        print(f"Размер файла: {len(content)} байт")
        print(f"Первые 100 байт: {content[:100]}")
    else:
        print("Файл НЕ найден в MinIO!")
        
except Exception as e:
    print(f"Ошибка: {e}")

print("=" * 50)
