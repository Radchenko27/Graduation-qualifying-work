"""
Скрипт для тестирования API endpoints материалов
"""

import requests
import json
from pathlib import Path

BASE_URL = "http://localhost:8000"


def test_materials_api():
    """Тестирование API материалов"""
    
    print("=" * 70)
    print("ТЕСТИРОВАНИЕ API МАТЕРИАЛОВ")
    print("=" * 70)
    
    # Проверка доступности API
    try:
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            print(f"✗ API недоступен: {BASE_URL}")
            print("Запустите сервер: uvicorn app.main:app --reload")
            return False
        print("✓ API доступен")
    except requests.ConnectionError:
        print(f"✗ Не удалось подключиться к {BASE_URL}")
        return False
    
    # Тест 1: Получить типы материалов
    print("\n[ТЕСТ 1] GET /api/materials/types")
    try:
        response = requests.get(f"{BASE_URL}/api/materials/types")
        if response.status_code == 200:
            types = response.json()
            print(f"✓ Типы материалов: {types}")
        else:
            print(f"✗ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 2: Поиск материалов (пустой запрос)
    print("\n[ТЕСТ 2] GET /api/materials/search?q=ППГнг")
    try:
        response = requests.get(f"{BASE_URL}/api/materials/search", params={"q": "ППГнг"})
        if response.status_code == 200:
            materials = response.json()
            print(f"✓ Найдено материалов: {len(materials)}")
            for mat in materials[:3]:
                print(f"  - {mat['name']} ({mat['type']})")
        elif response.status_code == 401:
            print("⚠ Требуется аутентификация")
        else:
            print(f"✗ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Тест 3: Импорт из JSON (если файл существует)
    processed_dir = Path("processed")
    json_files = list(processed_dir.glob("**/*_processed.json"))
    
    if json_files:
        json_file = json_files[0]
        print(f"\n[ТЕСТ 3] POST /api/materials/import-from-json")
        print(f"  Файл: {json_file}")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/materials/import-from-json",
                json={"json_file_path": str(json_file)}
            )
            
            if response.status_code == 200:
                materials = response.json()
                print(f"✓ Импорт успешен: {len(materials)} материалов")
                for mat in materials[:5]:
                    print(f"  - {mat['type']}: {mat['name']}")
            elif response.status_code == 401:
                print("⚠ Требуется аутентификация")
                print("  Зарегистрируйтесь и войдите в систему")
            elif response.status_code == 404:
                print("✗ Файл не найден в базе")
            else:
                print(f"✗ Ошибка: {response.status_code}")
                print(f"  {response.text}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    else:
        print("\n[ТЕСТ 3] Пропущен - нет обработанных JSON файлов")
    
    # Тест 4: Пакетный импорт
    if processed_dir.exists():
        print(f"\n[ТЕСТ 4] POST /api/materials/batch-import")
        print(f"  Директория: processed/")
        
        try:
            response = requests.post(
                f"{BASE_URL}/api/materials/batch-import",
                json={"input_dir": "processed/"}
            )
            
            if response.status_code == 200:
                materials = response.json()
                print(f"✓ Пакетный импорт успешен: {len(materials)} материалов")
            elif response.status_code == 401:
                print("⚠ Требуется аутентификация")
            else:
                print(f"✗ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")
    else:
        print("\n[ТЕСТ 4] Пропущен - нет директории processed/")
    
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 70)
    
    return True


def test_with_authentication():
    """Тестирование с аутентификацией"""
    
    print("\n" + "=" * 70)
    print("ТЕСТИРОВАНИЕ С АВТОРИЗАЦИЕЙ")
    print("=" * 70)
    
    # Регистрация
    print("\n[РЕГИСТРАЦИЯ] POST /api/users/register")
    try:
        response = requests.post(
            f"{BASE_URL}/api/users/register",
            json={
                "username": "test_user",
                "first_name": "Иван",
                "last_name": "Иванов",
                "password": "testpass123",
                "email": "test@example.com"
            },
            cookies={}
        )
        
        if response.status_code in [200, 201]:
            print("✓ Регистрация успешна")
        elif response.status_code == 409:
            print("⚠ Пользователь уже существует")
        else:
            print(f"✗ Ошибка: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Вход
    print("\n[ВХОД] POST /api/users/login")
    session_cookies = {}
    try:
        response = requests.post(
            f"{BASE_URL}/api/users/login",
            json={
                "username": "test_user",
                "password": "testpass123"
            },
            cookies={},
            allow_redirects=True
        )
        
        if response.status_code == 200:
            print("✓ Вход успешен")
            session_cookies = response.cookies.get_dict()
        else:
            print(f"✗ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"✗ Ошибка: {e}")
    
    # Проверка материалов с авторизацией
    if session_cookies:
        print("\n[ПРОВЕРКА] GET /api/materials/types (с авторизацией)")
        try:
            response = requests.get(
                f"{BASE_URL}/api/materials/types",
                cookies=session_cookies
            )
            
            if response.status_code == 200:
                print(f"✓ Доступ разрешён: {response.json()}")
            else:
                print(f"✗ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"✗ Ошибка: {e}")


if __name__ == '__main__':
    import sys
    
    print("\nСкрипт для тестирования API материалов\n")
    print("Предварительно запустите сервер:")
    print("  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--auth':
        test_with_authentication()
    else:
        test_materials_api()
        print("\nДля тестирования с авторизацией используйте: --auth")
