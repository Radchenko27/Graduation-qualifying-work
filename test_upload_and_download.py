"""
Тест загрузки и скачивания файла в MinIO
"""
from app.services.minio_client import minio_client

print("=" * 60)
print("MinIO Upload & Download Test")
print("=" * 60)
print(f"Bucket: {minio_client.bucket_name}")
print(f"Endpoint: {minio_client.client.meta.endpoint_url}")

# Создаём тестовый PDF (мини-версия)
test_pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000052 00000 n \n0000000101 00000 n \ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n178\n%%EOF"

object_key = f"documents/3/test-{12345}.pdf"

print(f"\n1. Загрузка файла: {object_key}")
try:
    uploaded_key = minio_client.upload_file(test_pdf_content, f"test-{12345}.pdf", 3)
    print(f"[OK] Файл загружен: {uploaded_key}")
except Exception as e:
    print(f"[ERROR] Ошибка загрузки: {e}")
    exit(1)

print(f"\n2. Проверка существования:")
try:
    exists = minio_client.file_exists(object_key)
    print(f"[OK] Файл существует: {exists}")
except Exception as e:
    print(f"[ERROR] Ошибка проверки: {e}")

print(f"\n3. Скачивание файла:")
try:
    downloaded_content = minio_client.download_file(object_key)
    print(f"[OK] Скачано {len(downloaded_content)} байт")
    print(f"[OK] Содержимое совпадает: {downloaded_content == test_pdf_content}")
except Exception as e:
    print(f"[ERROR] Ошибка скачивания: {e}")

print(f"\n4. Удаление файла:")
try:
    minio_client.delete_file(object_key)
    print(f"[OK] Файл удалён")
except Exception as e:
    print(f"[ERROR] Ошибка удаления: {e}")

print("\n" + "=" * 60)
print("Test completed!")
print("=" * 60)
