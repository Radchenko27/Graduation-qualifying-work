"""
Пример использования specification_parser

Этот скрипт демонстрирует основные возможности парсера спецификаций.
"""

from pathlib import Path
import sys

# Добавляем корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.specification_parser import (
    SpecificationParser,
    parse_document_specifications,
    batch_parse_specifications
)


def example_1_parse_single_document():
    """Пример 1: Парсинг одного документа"""
    print("=" * 70)
    print("ПРИМЕР 1: Парсинг одного документа")
    print("=" * 70)
    
    document_id = 1  # Укажите ID вашего документа
    
    try:
        # Получаем сводную информацию
        with SpecificationParser(document_id) as parser:
            summary = parser.get_summary()
            
            print(f"\nДокумент: {summary['document_name']}")
            print(f"ID документа: {summary['document_id']}")
            print(f"ID проекта: {summary['project_id']}")
            print(f"Страниц со спецификациями: {summary['specification_pages_count']}")
            
            print("\nСтраницы:")
            for page in summary['specification_pages']:
                print(f"  - Страница {page['page_number']}: "
                      f"категория={page['category']}, "
                      f"уверенность={page['confidence']:.2%}")
        
        # Экспорт в JSON
        json_path = parse_document_specifications(
            document_id=document_id,
            output_format='json',
            output_dir='output/specifications'
        )
        print(f"\n✓ JSON сохранён: {json_path}")
        
        # Экспорт в Excel
        excel_path = parse_document_specifications(
            document_id=document_id,
            output_format='excel',
            output_dir='output/specifications'
        )
        print(f"✓ Excel сохранён: {excel_path}")
        
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")
        print("\nУбедитесь, что:")
        print("  1. Документ с указанным ID существует")
        print("  2. Документ классифицирован (есть страницы с category='specification')")
        print("  3. Существует processed JSON файл в директории processed/")


def example_2_detailed_parsing():
    """Пример 2: Детальный парсинг и анализ"""
    print("\n" + "=" * 70)
    print("ПРИМЕР 2: Детальный парсинг и анализ")
    print("=" * 70)
    
    document_id = 1
    
    try:
        with SpecificationParser(document_id) as parser:
            # Извлекаем спецификации
            specs = parser.extract_specification_tables()
            
            print(f"\nНайдено таблиц спецификаций: {len(specs)}")
            
            total_rows = 0
            for i, spec in enumerate(specs, 1):
                print(f"\nТаблица {i} (страница {spec['page_number']}):")
                print(f"  Заголовок: {spec['header']}")
                print(f"  Колонки: {', '.join(spec['columns'])}")
                print(f"  Строк: {spec['row_count']}")
                
                total_rows += spec['row_count']
                
                # Показываем первые 3 строки
                if spec['rows']:
                    print(f"  Примеры строк:")
                    for row in spec['rows'][:3]:
                        name = row.get('name', row.get('Наименование', '-'))
                        qty = row.get('quantity', row.get('Кол-во', '-'))
                        unit = row.get('unit', row.get('Ед.изм.', '-'))
                        print(f"    - {name} x {qty} {unit}")
            
            print(f"\nВсего строк во всех спецификациях: {total_rows}")
            
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")


def example_3_batch_processing():
    """Пример 3: Пакетная обработка проекта"""
    print("\n" + "=" * 70)
    print("ПРИМЕР 3: Пакетная обработка проекта")
    print("=" * 70)
    
    project_id = 1  # Укажите ID вашего проекта
    
    try:
        print(f"\nОбработка всех документов проекта {project_id}...")
        
        output_files = batch_parse_specifications(
            project_id=project_id,
            output_format='excel',
            output_dir='output/project_specs'
        )
        
        print(f"\n✓ Обработано документов: {len(output_files)}")
        for f in output_files:
            print(f"  - {f}")
            
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")


def example_4_custom_processing():
    """Пример 4: Кастомная обработка спецификаций"""
    print("\n" + "=" * 70)
    print("ПРИМЕР 4: Кастомная обработка спецификаций")
    print("=" * 70)
    
    document_id = 1
    
    try:
        with SpecificationParser(document_id) as parser:
            specs = parser.extract_specification_tables()
            
            # Группировка материалов по типам
            materials_by_type = {}
            
            for spec in specs:
                for row in spec['rows']:
                    # Определяем тип по названию
                    name = row.get('name', '').lower()
                    
                    if 'кабель' in name or 'провод' in name:
                        mat_type = 'Кабели и провода'
                    elif 'розетка' in name or 'выключатель' in name:
                        mat_type = 'Установочные изделия'
                    elif 'лампа' in name or 'светильник' in name:
                        mat_type = 'Осветительные приборы'
                    elif 'автомат' in name or 'предохранитель' in name:
                        mat_type = 'Аппараты защиты'
                    else:
                        mat_type = 'Прочее'
                    
                    if mat_type not in materials_by_type:
                        materials_by_type[mat_type] = []
                    
                    materials_by_type[mat_type].append(row)
            
            print("\nГруппировка материалов по типам:")
            for mat_type, materials in materials_by_type.items():
                print(f"\n{mat_type}:")
                print(f"  Количество наименований: {len(materials)}")
                
                # Подсчёт общего количества
                total_qty = 0
                for mat in materials:
                    qty = mat.get('quantity', 0)
                    if isinstance(qty, (int, float)):
                        total_qty += qty
                
                print(f"  Общее количество: {total_qty}")
                
    except Exception as e:
        print(f"\n✗ Ошибка: {e}")


def main():
    """Запуск примеров"""
    print("\n" + "=" * 70)
    print("ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ SPECIFICATION PARSER")
    print("=" * 70)
    
    print("\nДоступные примеры:")
    print("  1. Парсинг одного документа")
    print("  2. Детальный парсинг и анализ")
    print("  3. Пакетная обработка проекта")
    print("  4. Кастомная обработка спецификаций")
    print("  5. Все примеры")
    print("  0. Выход")
    
    choice = input("\nВыберите пример (0-5): ").strip()
    
    if choice == '1':
        example_1_parse_single_document()
    elif choice == '2':
        example_2_detailed_parsing()
    elif choice == '3':
        example_3_batch_processing()
    elif choice == '4':
        example_4_custom_processing()
    elif choice == '5':
        example_1_parse_single_document()
        example_2_detailed_parsing()
        example_3_batch_processing()
        example_4_custom_processing()
    elif choice == '0':
        print("Выход...")
    else:
        print("Неверный выбор")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    main()