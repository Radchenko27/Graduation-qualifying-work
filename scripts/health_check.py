"""
Скрипт для проверки работоспособности всех сервисов.
"""
import os
import sys
import requests
from datetime import datetime
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def check_database():
    """Проверка подключения к PostgreSQL."""
    try:
        from app.db import engine
        from sqlalchemy import text

        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ PostgreSQL: подключено")
            print(f"  Версия: {version.split(',')[0]}")
            return True
    except Exception as e:
        print(f"✗ PostgreSQL: ошибка подключения - {e}")
        return False


def check_minio():
    """Проверка подключения к MinIO."""
    try:
        from app.storage import storage

        # Проверяем существование бакета
        if storage.client.bucket_exists(storage.bucket_name):
            print(f"✓ MinIO: подключено")
            print(f"  Бакет: {storage.bucket_name}")
            print(f"  Endpoint: {storage.endpoint}")
            return True
        else:
            print(f"✗ MinIO: бакет не найден")
            return False
    except Exception as e:
        print(f"✗ MinIO: ошибка подключения - {e}")
        return False


def check_api():
    """Проверка API."""
    try:
        base_url = os.getenv("API_URL", "http://localhost:8000")

        # Проверка корневого эндпоинта
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            print(f"✓ API: доступно")
            print(f"  URL: {base_url}")
            print(f"  Статус: {response.status_code}")

            # Проверка документации
            docs_response = requests.get(f"{base_url}/docs", timeout=5)
            if docs_response.status_code == 200:
                print(f"  Документация: доступна ({base_url}/docs)")

            return True
        else:
            print(f"✗ API: недоступно (статус: {response.status_code})")
            return False
    except Exception as e:
        print(f"✗ API: ошибка - {e}")
        return False


def check_migrations():
    """Проверка миграций."""
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config("alembic.ini")
        current = command.current(alembic_cfg)

        print(f"✓ Миграции: применены")
        print(f"  Текущая версия: {current}")
        return True
    except Exception as e:
        print(f"✗ Миграции: ошибка - {e}")
        return False


def main():
    """Главная функция проверки."""
    print(f"\n{'='*60}")
    print(f"Health Check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    checks = [
        ("PostgreSQL", check_database),
        ("MinIO", check_minio),
        ("API", check_api),
        ("Миграции", check_migrations)
    ]

    results = []
    for name, check_func in checks:
        print(f"\n{name}:")
        result = check_func()
        results.append((name, result))

    print(f"\n{'='*60}")
    print("Итог:")
    print(f"{'='*60}")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name}: {status}")

    print(f"\nИтого: {passed}/{total} проверок пройдено")

    if passed == total:
        print("\n✓ Все сервисы работают корректно!")
        return 0
    else:
        print("\n✗ Некоторые сервисы недоступны. Проверьте логи.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
