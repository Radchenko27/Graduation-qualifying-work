"""
Список файлов в MinIO
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.minio_client import MinIOClient

client = MinIOClient()
print(f'Bucket: {client.bucket_name}')

try:
    files = client.client.list_objects(Bucket=client.bucket_name, Prefix='')
    if files.get('Contents'):
        print('\nФайлы в MinIO:')
        for obj in files['Contents']:
            key = obj['Key']
            size = obj['Size']
            print(f'  {key} ({size} bytes)')
    else:
        print('Бакет пуст')
except Exception as e:
    print(f'Ошибка: {e}')
    import traceback
    traceback.print_exc()
