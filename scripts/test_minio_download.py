"""
Скрипт для тестирования скачивания файлов из MinIO.

Использование:
    python scripts/test_minio_download.py <object_key>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.minio_client import MinIOClient


def test_download(object_key: str):
    """Протестировать скачивание файла"""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ СКАЧИВАНИЯ ИЗ MINIO")
    print("=" * 70)
    
    try:
        client = MinIOClient()
        
        # Проверяем что файл существует
        print(f"\n1. Проверка существования файла: {object_key}")
        exists = client.file_exists(object_key)
        if not exists:
            print(f"   ❌ Файл не существует в MinIO")
            return False
        print(f"   ✅ Файл существует")
        
        # Скачиваем файл
        print(f"\n2. Скачивание файла...")
        content = client.download_file(object_key)
        print(f"   ✅ Скачано: {len(content)} bytes")
        
        # Генерируем presigned URL
        print(f"\n3. Генерация presigned URL...")
        url = client.get_presigned_url(object_key, expires_in=3600)
        print(f"   ✅ URL сгенерирован")
        print(f"   URL: {url}")
        
        # Проверяем что URL корректный
        if not url.startswith(('http://', 'https://')):
            print(f"   ❌ Ошибка: URL не содержит протокол http/https")
            return False
        
        print(f"   ✅ URL корректный (начинается с http/https)")
        
        print("\n" + "=" * 70)
        print("✅ ВСЕ ТЕСТЫ УСПЕШНЫ!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    if len(sys.argv) < 2:
        print("Использование: python scripts/test_minio_download.py <object_key>")
        print("\nПримеры:")
        print("  python scripts/test_minio_download.py documents/1/test.pdf")
        print("  python scripts/test_minio_download.py documents/6/17-23-00-ЭОМ.pdf")
        sys.exit(1)
    
    object_key = sys.argv[1]
    success = test_download(object_key)
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()
