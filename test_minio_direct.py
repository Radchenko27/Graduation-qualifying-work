"""
Прямое тестирование MinIO через boto3
"""
import boto3
from botocore.exceptions import ClientError

print("=" * 60)
print("Direct MinIO Test via boto3")
print("=" * 60)

# Конфигурация
endpoint = "http://localhost:9000"
access_key = "minioadmin"
secret_key = "minioadmin_password"
bucket = "documents"
object_key = "documents/3/17-23-00-ЭОМ.pdf"

# Создаём клиент
client = boto3.client(
    's3',
    endpoint_url=endpoint,
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    config=boto3.session.Config(signature_version='s3v4'),
    verify=False
)

print(f"Endpoint: {endpoint}")
print(f"Bucket: {bucket}")
print(f"Object: {object_key}")

# Проверяем существование
print("\n[1] Проверка существования файла...")
try:
    response = client.head_object(Bucket=bucket, Key=object_key)
    print(f"[OK] File exists, size: {response['ContentLength']} bytes")
except ClientError as e:
    print(f"[ERROR] File not found: {e}")
    exit(1)

# Скачиваем
print("\n[2] Скачивание файла...")
try:
    response = client.get_object(Bucket=bucket, Key=object_key)
    file_content = response['Body'].read()
    print(f"[OK] Downloaded: {len(file_content)} bytes")
    print(f"[OK] First 100 bytes: {file_content[:100]}")
except Exception as e:
    print(f"[ERROR] Download failed: {e}")

print("\n" + "=" * 60)
