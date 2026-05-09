"""
Тест для проверки работы с MinIO
"""
from app.services.minio_client import minio_client

print("MinIO Client initialized")
print(f"Bucket: {minio_client.bucket_name}")
print(f"Endpoint: {minio_client.client.meta.endpoint_url}")

# Проверка существования бакета
bucket_exists = minio_client.file_exists("test.txt")
print(f"Test file exists: {bucket_exists}")

# Загрузим тестовый файл
test_content = b"Hello MinIO!"
object_key = minio_client.upload_file(test_content, "test.txt", 1)
print(f"Uploaded test file: {object_key}")

# Скачаем обратно
downloaded = minio_client.download_file(object_key)
print(f"Downloaded: {downloaded}")

# Удалим
minio_client.delete_file(object_key)
print("Test file deleted")

print("\n✓ All tests passed!")
