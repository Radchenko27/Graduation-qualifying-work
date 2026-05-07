"""
Тест скачивания через MinIO client
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.minio_client import minio_client

print("=" * 60)
print("MinIO Download Test")
print("=" * 60)
print(f"Endpoint: {minio_client.client.meta.endpoint_url}")
print(f"Bucket: {minio_client.bucket_name}")

object_key = "documents/3/17-23-00-ЭОМ.pdf"
print(f"Object: {object_key}")

print("\n[1] Проверка существования...")
exists = minio_client.file_exists(object_key)
print(f"Exists: {exists}")

print("\n[2] Скачивание...")
try:
    content = minio_client.download_file(object_key)
    print(f"[OK] Downloaded: {len(content)} bytes")
    if len(content) > 0:
        print(f"[OK] First 100 bytes: {content[:100]}")
    else:
        print("[ERROR] File is EMPTY!")
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()

print("=" * 60)
