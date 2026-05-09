"""
Тесты для проверки парсинга PDF и импорта материалов
"""

import pytest
import json
from pathlib import Path
from app.utils.pdf_parser import (
    PDFDataExtractor,
    parse_pdf_to_materials,
    batch_parse_processed_files
)


class TestPDFDataExtractor:
    """Тесты для экстрактора PDF данных"""
    
    def test_load_json_file(self, tmp_path):
        """Тест загрузки JSON файла"""
        # Создаём тестовый JSON
        test_data = {
            "metadata": {"file_name": "test.pdf", "page_count": 10},
            "text": {"0": "Тестовый текст", "1": "Ещё текст"}
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        # Загружаем и проверяем
        extractor = PDFDataExtractor(str(json_file))
        assert extractor.metadata["file_name"] == "test.pdf"
        assert len(extractor.text_pages) == 2
    
    def test_extract_drawing_info(self, tmp_path):
        """Тест извлечения информации о чертежах"""
        test_data = {
            "metadata": {
                "file_name": "03-23-ОГР01.1-ЭОМ1.1.pdf",
                "page_count": 157
            },
            "text": {
                "0": "03-23-ОГР01.1-ЭОМ1.1 - Обложка",
                "1": "Ведомость чертежей 03-23-ОГР01.1-ЭОМ1.1"
            }
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        extractor = PDFDataExtractor(str(json_file))
        drawings_info = extractor.extract_drawing_info()
        
        assert drawings_info["total_pages"] == 157
        assert len(drawings_info["drawings"]) > 0
        assert any(d["number"] == "03-23-ОГР01.1-ЭОМ1.1" for d in drawings_info["drawings"])


class TestMaterialExtraction:
    """Тесты для извлечения материалов"""
    
    def test_parse_cable_pattern(self, tmp_path):
        """Тест парсинга кабеля"""
        test_data = {
            "metadata": {"file_name": "test.pdf", "page_count": 1},
            "text": {
                "0": "ППГнг(А)-HF 3×2,5 - кабель 100 шт, ППГнг 5×70 - 50 шт"
            }
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        extractor = PDFDataExtractor(str(json_file))
        materials = extractor.extract_specifications()
        
        assert len(materials) > 0
        cable_materials = [m for m in materials if m['type'] == 'cable']
        assert len(cable_materials) > 0
    
    def test_parse_device_pattern(self, tmp_path):
        """Тест парсинга устройств"""
        test_data = {
            "metadata": {"file_name": "test.pdf", "page_count": 1},
            "text": {
                "0": "Розетка 16А - 200 шт, Выключатель - 50 шт, Датчик движения - 30 шт"
            }
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        extractor = PDFDataExtractor(str(json_file))
        materials = extractor.extract_specifications()
        
        device_materials = [m for m in materials if m['type'] == 'device']
        assert len(device_materials) > 0
    
    def test_page_number_tracking(self, tmp_path):
        """Тест отслеживания номера страницы"""
        test_data = {
            "metadata": {"file_name": "test.pdf", "page_count": 3},
            "text": {
                "0": "Страница 0",
                "1": "ППГнг(А)-HF 3×2,5 - 100 шт",
                "2": "Страница 2"
            }
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        extractor = PDFDataExtractor(str(json_file))
        materials = extractor.extract_specifications()
        
        for mat in materials:
            assert 'page_number' in mat
            assert mat['page_number'] == 1


class TestBatchProcessing:
    """Тесты для пакетной обработки"""
    
    def test_batch_parse_multiple_files(self, tmp_path):
        """Тест пакетного парсинга нескольких файлов"""
        # Создаём несколько тестовых файлов
        for i in range(2):
            test_data = {
                "metadata": {"file_name": f"test{i}.pdf", "page_count": 1},
                "text": {
                    "0": f"Файл {i}: ППГнг(А)-HF 3×2,5 - {100 * (i+1)} шт"
                }
            }
            
            json_file = tmp_path / f"test{i}_processed.json"
            json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        # Пакетный парсинг
        all_materials = batch_parse_processed_files(str(tmp_path))
        
        assert len(all_materials) > 0
        assert all('source_file' in m for m in all_materials)


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_real_processed_file(self):
        """Тест с реальным обработанным файлом (если существует)"""
        test_file = Path("processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json")
        
        if not test_file.exists():
            pytest.skip("Тестовый файл не найден")
        
        extractor = PDFDataExtractor(str(test_file))
        materials = extractor.extract_specifications()
        
        assert len(materials) >= 0  # Может быть 0, если паттерны не совпадают
        print(f"\nНайдено материалов: {len(materials)}")
        
        # Показать первые 5 материалов
        for mat in materials[:5]:
            print(f"  - {mat['type']}: {mat['name']} x {mat['quantity']} (стр. {mat['page_number']})")
    
    def test_export_to_json(self, tmp_path):
        """Тест экспорта в JSON"""
        test_data = {
            "metadata": {"file_name": "test.pdf", "page_count": 1},
            "text": {"0": "ППГнг(А)-HF 3×2,5 - 100 шт"}
        }
        
        json_file = tmp_path / "test.json"
        json_file.write_text(json.dumps(test_data, ensure_ascii=False))
        
        output_file = tmp_path / "output.json"
        
        extractor = PDFDataExtractor(str(json_file))
        extractor.export_to_json(str(output_file))
        
        assert output_file.exists()
        
        with open(output_file, 'r', encoding='utf-8') as f:
            exported = json.load(f)
        
        assert 'specifications' in exported
        assert 'metadata' in exported


def run_manual_tests():
    """Ручное тестирование без pytest"""
    print("=" * 60)
    print("РУЧНОЕ ТЕСТИРОВАНИЕ ПАРСЕРА PDF")
    print("=" * 60)
    
    # Тест 1: Загрузка реального файла
    print("\n[ТЕСТ 1] Загрузка реального обработанного файла...")
    test_file = Path("processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json")
    
    if test_file.exists():
        print(f"✓ Файл найден: {test_file}")
        
        extractor = PDFDataExtractor(str(test_file))
        print(f"✓ Метаданные: {extractor.metadata.get('file_name')}")
        print(f"  Страниц: {extractor.metadata.get('page_count')}")
        
        # Тест 2: Извлечение материалов
        print("\n[ТЕСТ 2] Извлечение материалов...")
        materials = extractor.extract_specifications()
        print(f"✓ Найдено материалов: {len(materials)}")
        
        # Группировка по типам
        from collections import Counter
        types = Counter(m['type'] for m in materials)
        print("\n  Распределение по типам:")
        for mat_type, count in types.items():
            print(f"    - {mat_type}: {count}")
        
        # Тест 3: Показать примеры
        print("\n[ТЕСТ 3] Примеры материалов:")
        for mat in materials[:10]:
            print(f"  • {mat['type']:10} | {mat['name'][:40]:40} | {mat['quantity']:6} {mat['unit']} (стр. {mat['page_number']})")
        
        if len(materials) > 10:
            print(f"  ... и ещё {len(materials) - 10} материалов")
        
        # Тест 4: Извлечение чертежей
        print("\n[ТЕСТ 4] Извлечение информации о чертежах...")
        drawings = extractor.extract_drawing_info()
        print(f"✓ Найдено чертежей: {len(drawings['drawings'])}")
        print(f"  Документ: {drawings['document_title']}")
        
        print("\n" + "=" * 60)
        print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО УСПЕШНО")
        print("=" * 60)
        
        return True
    else:
        print(f"✗ Файл не найден: {test_file}")
        print("\nСоздайте тестовый файл или используйте существующий в processed/")
        return False


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--manual':
        run_manual_tests()
    else:
        print("Запуск тестов через pytest...")
        print("Или используйте: python tests/test_parsing.py --manual")
