"""
Скрипт для проверки и исправления повреждённых processed JSON файлов.

Использование:
    python scripts/fix_processed_json.py [путь_к_файлу]
    
Если путь не указан, проверяются все файлы в папке processed/
"""

import json
import sys
from pathlib import Path


def check_json_file(filepath: Path) -> bool:
    """Проверить JSON файл на валидность"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            json.load(f)
        print(f"✅ {filepath}: Валидный JSON")
        return True
    except json.JSONDecodeError as e:
        print(f"❌ {filepath}: Повреждён")
        print(f"   Ошибка: {e}")
        return False
    except Exception as e:
        print(f"❌ {filepath}: Ошибка чтения - {e}")
        return False


def fix_json_file(filepath: Path, backup: bool = True) -> bool:
    """
    Попытаться исправить JSON файл
    
    Стратегии исправления:
    1. Удаление повреждённых символов
    2. Восстановление структуры
    """
    print(f"\n🔧 Попытка исправления {filepath}...")
    
    try:
        # Читаем файл
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Создаём бэкап
        if backup:
            backup_path = filepath.with_suffix('.json.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   Бэкап создан: {backup_path}")
        
        # Попытка 1: Простое исправление - удаление некорректных символов
        try:
            # Пробуем загрузить с игнорированием ошибок
            fixed_content = content.encode('utf-8', errors='ignore').decode('utf-8')
            data = json.loads(fixed_content)
            
            # Сохраняем исправленный файл
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"   ✅ Файл исправлен!")
            return True
        except json.JSONDecodeError:
            pass
        
        # Попытка 2: Обрезка до последнего валидного символа
        print("   Пробуем обрезку файла...")
        for i in range(len(content), 0, -1000):
            try:
                truncated = content[:i]
                # Ищем последнюю закрывающую скобку
                last_brace = truncated.rfind('}')
                if last_brace > 0:
                    truncated = truncated[:last_brace + 1]
                
                data = json.loads(truncated)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                print(f"   ✅ Файл исправлен обрезкой до {last_brace} символа")
                return True
            except:
                continue
        
        print("   ❌ Не удалось исправить файл")
        return False
        
    except Exception as e:
        print(f"   ❌ Ошибка при исправлении: {e}")
        return False


def check_all_processed_files(processed_dir: str = "processed") -> dict:
    """Проверить все processed файлы"""
    processed_path = Path(processed_dir)
    
    if not processed_path.exists():
        print(f"❌ Директория {processed_dir} не найдена")
        return {"valid": 0, "invalid": 0}
    
    json_files = list(processed_path.glob("**/*_processed.json"))
    
    if not json_files:
        print(f"❌ Файлы *_processed.json не найдены в {processed_dir}")
        return {"valid": 0, "invalid": 0}
    
    print(f"Найдено файлов: {len(json_files)}\n")
    
    results = {"valid": 0, "invalid": 0, "fixed": 0}
    
    for json_file in json_files:
        if check_json_file(json_file):
            results["valid"] += 1
        else:
            results["invalid"] += 1
            
            # Предлагаем исправить
            choice = input(f"\nИсправить {json_file.name}? (y/n): ").strip().lower()
            if choice == 'y':
                if fix_json_file(json_file):
                    results["fixed"] += 1
                    results["invalid"] -= 1
    
    return results


def main():
    """Главная функция"""
    print("=" * 70)
    print("ПРОВЕРКА И ИСПРАВЛЕНИЕ PROCESSED JSON ФАЙЛОВ")
    print("=" * 70)
    
    if len(sys.argv) > 1:
        # Проверка конкретного файла
        filepath = Path(sys.argv[1])
        
        if not filepath.exists():
            print(f"❌ Файл не найден: {filepath}")
            sys.exit(1)
        
        print(f"\nПроверка файла: {filepath}")
        
        if check_json_file(filepath):
            print("\n✅ Файл валиден")
        else:
            choice = input("\nИсправить файл? (y/n): ").strip().lower()
            if choice == 'y':
                if fix_json_file(filepath):
                    print("\n✅ Файл исправлен!")
                else:
                    print("\n❌ Не удалось исправить файл")
                    print("\nРекомендация: Переобработайте документ через pdf_processor")
            else:
                print("\n⚠️ Файл не был исправлен")
    else:
        # Проверка всех файлов
        print("\nПроверка всех файлов в директории processed/\n")
        
        results = check_all_processed_files()
        
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ")
        print("=" * 70)
        print(f"Валидные файлы: {results['valid']}")
        print(f"Повреждённые файлы: {results['invalid']}")
        print(f"Исправлено файлов: {results['fixed']}")
        
        if results['invalid'] > 0:
            print("\n⚠️ Некоторые файлы не удалось исправить автоматически.")
            print("   Рекомендуется переобработать документы:")
            print("   python -m app.services.pdf_processor <путь_к_pdf> processed/")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)