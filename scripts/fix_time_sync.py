"""
Скрипт для диагностики и исправления проблем с синхронизацией времени
при работе с MinIO.

Использование:
    python scripts/fix_time_sync.py
"""

import os
import sys
import subprocess
from datetime import datetime
import time


def check_system_time():
    """Проверить системное время"""
    print("=" * 70)
    print("ПРОВЕРКА СИСТЕМНОГО ВРЕМЕНИ")
    print("=" * 70)

    now = datetime.now()
    print(f"\nТекущее системное время: {now}")
    print(f"Часовой пояс: {time.tzname}")

    # Проверяем на Windows
    if os.name == 'nt':
        try:
            result = subprocess.run(
                ['w32tm', '/query', '/status'],
                capture_output=True,
                text=True,
                timeout=10
            )
            print("\nСтатус службы времени Windows:")
            print(result.stdout if result.stdout else "Не удалось получить статус")
        except Exception as e:
            print(f"\nНе удалось проверить статус времени Windows: {e}")


def sync_windows_time():
    """Синхронизировать время на Windows"""
    print("\n" + "=" * 70)
    print("СИНХРОНИЗАЦИЯ ВРЕМЕНИ НА WINDOWS")
    print("=" * 70)

    try:
        print("\nСинхронизация с интернет-серверами времени...")
        result = subprocess.run(
            ['w32tm', '/resync'],
            capture_output=True,
            text=True,
            timeout=30
        )

        if result.returncode == 0:
            print("✅ Время успешно синхронизировано!")
            print(f"\n{result.stdout}")
        else:
            print(f"❌ Ошибка синхронизации: {result.stderr}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")


def check_minio_connection():
    """Проверить соединение с MinIO"""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА СОЕДИНЕНИЯ С MINIO")
    print("=" * 70)

    try:
        from app.services.minio_client import MinIOClient

        print("\nПопытка подключения к MinIO...")
        client = MinIOClient()
        print("✅ Подключение к MinIO успешно!")

    except Exception as e:
        print(f"❌ Ошибка подключения к MinIO: {e}")

        # Проверяем, это ошибка времени
        if 'RequestTimeTooSkewed' in str(e) or 'TimeTooSkewed' in str(e):
            print("\n" + "!" * 70)
            print("ОБНАРУЖЕНА ОШИБКА СИНХРОНИЗАЦИИ ВРЕМЕНИ!")
            print("!" * 70)
            print("\nЭто происходит из-за расхождения времени между")
            print("вашим компьютером и сервером MinIO.")
            print("\nРешение:")
            print("1. Синхронизируйте системное время")
            print("2. Установите правильный часовой пояс")
            print("3. Перезапустите Docker контейнеры")


def check_docker_time():
    """Проверить время в Docker контейнерах"""
    print("\n" + "=" * 70)
    print("ПРОВЕРКА ВРЕМЕНИ В DOCKER КОНТЕЙНЕРАХ")
    print("=" * 70)

    try:
        # Проверяем время в контейнере MinIO
        result = subprocess.run(
            ['docker', 'exec', 'minio_storage', 'date'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            print(f"\nВремя в контейнере MinIO: {result.stdout.strip()}")
        else:
            print("\nНе удалось получить время из контейнера MinIO")
    except Exception as e:
        print(f"\nDocker недоступен или контейнер не запущен: {e}")


def show_solution():
    """Показать решение проблемы"""
    print("\n" + "=" * 70)
    print("РЕШЕНИЕ ПРОБЛЕМЫ RequestTimeTooSkewed")
    print("=" * 70)

    print("""
ОШИБКА: RequestTimeTooSkewed
ПРИЧИНА: Разница между временем клиента и сервера слишком велика

РЕШЕНИЕ:

1. СИНХРОНИЗАЦИЯ ВРЕМЕНИ НА WINDOWS:
   → Откройте "Параметры" → "Время и язык" → "Дата и время"
   → Включите "Автоматическая установка времени"
   → Нажмите "Синхронизировать сейчас"

   ИЛИ через командную строку:
   → w32tm /resync

2. УСТАНОВКА ЧАСОВОГО ПОЯСА:
   → Set-TimeZone -Id "Russian Standard Time"

3. ПЕРЕЗАПУСК DOCKER:
   → docker-compose down
   → docker-compose up -d

4. ПРОВЕРКА .env ФАЙЛА:
   → Убедитесь, что добавлена настройка TZ=Europe/Moscow
   → Перезапустите контейнеры после изменения

5. ПРОВЕРКА ВРЕМЕНИ В КОНТЕЙНЕРАХ:
   → docker exec minio_storage date
   → docker exec fastapi_app date

Если проблема сохраняется:
- Проверьте настройки BIOS/UEFI (время может сбиваться)
- Отключите NTP в BIOS и используйте только NTP в Windows
- Перезагрузите компьютер
""")


def main():
    """Главная функция"""
    print("\n🔧 ДИАГНОСТИКА И ИСПРАВЛЕНИЕ ПРОБЛЕМ С ВРЕМЕНЕМ\n")

    if os.name == 'nt':
        # Windows
        print("Обнаружена операционная система: Windows\n")

        check_system_time()
        check_docker_time()
        check_minio_connection()

        print("\n" + "=" * 70)
        print("ДЕЙСТВИЯ")
        print("=" * 70)

        choice = input("\nВыполнить синхронизацию времени? (y/n): ").strip().lower()

        if choice == 'y':
            sync_windows_time()
            print("\nПосле синхронизации перезапустите Docker контейнеры:")
            print("  docker-compose down")
            print("  docker-compose up -d")
        else:
            show_solution()

    else:
        # Linux/Mac
        print("Обнаружена операционная система: Linux/Mac\n")
        print("Для синхронизации времени на Linux:")
        print("  sudo timedatectl set-ntp true")
        print("  sudo systemctl restart docker")

        check_system_time()
        check_minio_connection()
        show_solution()

    print("\n" + "=" * 70)
    print("ГОТОВО")
    print("=" * 70)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)