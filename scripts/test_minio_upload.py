"""
Скрипт для тестирования загрузки файлов в MinIO.

Использование:
    python scripts/test_minio_upload.py
"""

import sys
from pathlib import Path

# Добавляем корневую директорию
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.minio_client import MinIOClient


def test_minio():
    """Протестировать работу MinIO"""
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ MINIO")
    print("=" * 70)
    
    try:
        # Создаём клиент
        print("\n1. Создание клиента MinIO...")
        client = MinIOClient()
        print("   ✅ Клиент создан успешно")
        
        # Проверяем бакет
        print("\n2. Проверка бакета...")
        try:
            client.client.head_bucket(Bucket=client.bucket_name)
            print(f"   ✅ Бакет '{client.bucket_name}' существует")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
        
        # Создаём тестовый файл
        print("\n3. Создание тестового файла...")
        test_content = b"Test file content for MinIO upload test\n" * 10
        test_file_name = "test_upload.txt"
        project_id = 1
        
        print(f"   Content size: {len(test_content)} bytes")
        
        # Загружаем файл
        print("\n4. Загрузка тестового файла...")
        object_key = client.upload_file(test_content, test_file_name, project_id)
        print(f"   ✅ Файл загружен: {object_key}")
        
        # Проверяем что файл существует
        print("\n5. Проверка существования файла...")
        exists = client.file_exists(object_key)
        if exists:
            print(f"   ✅ Файл существует в MinIO")
        else:
            print(f"   ❌ Файл не найден в MinIO")
        
        # Скачиваем файл
        print("\n6. Скачивание тестового файла...")
        downloaded_content = client.download_file(object_key)
        
        if downloaded_content == test_content:
            print(f"   ✅ Контент совпадает!")
        else:
            print(f"   ❌ Контент не совпадает")
            print(f"      Ожидалось: {len(test_content)} bytes")
            print(f"      Получено: {len(downloaded_content)} bytes")
        
        # Удаляем тестовый файл
        print("\n7. Удаление тестового файла...")
        client.delete_file(object_key)
        print(f"   ✅ Файл удалён")
        
        # Проверяем что удалён
        exists = client.file_exists(object_key)
        if not exists:
            print(f"   ✅ Файл действительно удалён")
        else:
            print(f"   ⚠️  Файл всё ещё существует")
        
        # Генерируем presigned URL
        print("\n8. Генерация presigned URL...")
        url = client.get_presigned_url("documents/1/test.txt", expires_in=3600)
        print(f"   ✅ URL сгенерирован: {url[:80]}...")
        
        print("\n" + "=" * 70)
        print("✅ ВСЕ ТЕСТЫ УСПЕШНЫ!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ ОШИБКА:")
        print("=" * 70)
        print(f"\n{e}")
        
        import traceback
        traceback.print_exc()
        
        return False


def main():
    """Главная функция"""
    print("\n🧪 ТЕСТ MinIO UPLOAD\n")
    
    success = test_minio()
    
    if not success:
        print("\nВозможные причины:")
        print("1. MinIO не запущен (проверьте: docker ps)")
        print("2. Неправильные credentials (MINIO_ACCESS_KEY, MINIO_SECRET_KEY)")
        print("3. Ошибка времени (RequestTimeTooSkewed)")
        print("4. Неправильный endpoint (MINIO_ENDPOINT)")
        print("\nПроверьте переменные окружения в .env:")
        print("  MINIO_ENDPOINT=http://localhost:9000")
        print("  MINIO_ACCESS_KEY=minioadmin")
        print("  MINIO_SECRET_KEY=minioadmin_password")
        print("  MINIO_BUCKET=documents")
        sys.exit(1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(0)
