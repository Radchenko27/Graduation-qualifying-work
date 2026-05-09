"""
Утилита для парсинга PDF документов и извлечения данных для смет.
Поддерживает обработанные JSON файлы из processed/ директории.
"""

import json
import re
from pathlib import Path
from typing import Optional
from datetime import datetime


class PDFDataExtractor:
    """Класс для извлечения данных из обработанных PDF документов"""
    
    def __init__(self, json_file_path: str):
        """
        Инициализация экстрактора
        
        Args:
            json_file_path: Путь к обработанному JSON файлу
        """
        self.json_path = Path(json_file_path)
        self.data = self._load_json()
        self.metadata = self.data.get('metadata', {})
        self.text_pages = self.data.get('text', {})
    
    def _load_json(self) -> dict:
        """Загрузить JSON файл"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def extract_specifications(self) -> list[dict]:
        """
        Извлечь спецификации (таблицы материалов) из документа
        
        Returns:
            Список извлечённых материалов
        """
        materials = []
        
        for page_num, text in self.text_pages.items():
            # Поиск страниц со спецификациями
            if self._is_specification_page(text):
                page_materials = self._parse_materials_from_text(text, page_num)
                materials.extend(page_materials)
        
        return materials
    
    def _is_specification_page(self, text: str) -> bool:
        """
        Проверить, является ли страница спецификацией
        
        Args:
            text: Текст страницы
            
        Returns:
            True если страница содержит спецификацию
        """
        keywords = [
            'спецификация',
            'ведомость',
            'материалы',
            'оборудование',
            'изделия',
            'позиция',
            'наименование'
        ]
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in keywords)
    
    def _parse_materials_from_text(self, text: str, page_num: int) -> list[dict]:
        """
        Распарсить материалы из текста страницы
        
        Args:
            text: Текст страницы
            page_num: Номер страницы
            
        Returns:
            Список материалов
        """
        materials = []
        lines = text.split('\n')
        
        for line in lines:
            material = self._parse_material_line(line, page_num)
            if material:
                materials.append(material)
        
        return materials
    
    def _parse_material_line(self, line: str, page_num: int) -> Optional[dict]:
        """
        Распарсить одну строку с материалом
        
        Args:
            line: Строка текста
            page_num: Номер страницы
            
        Returns:
            Словарь с данными материала или None
        """
        line = line.strip()
        if not line or len(line) < 10:
            return None
        
        # Попытка извлечь данные по паттернам
        patterns = {
            'cable': self._parse_cable_line,
            'fixture': self._parse_fixture_line,
            'device': self._parse_device_line,
            'general': self._parse_general_line
        }
        
        for material_type, parser in patterns.items():
            material = parser(line, page_num, material_type)
            if material:
                return material
        
        return None
    
    def _parse_cable_line(self, line: str, page_num: int, material_type: str) -> Optional[dict]:
        """Парсинг строки с кабелем"""
        # Паттерн для кабелей: ПРГнг(А)-HF 3×2,5 или ППГнг 5×70
        cable_pattern = r'([А-ЯЁ0-9\s\-\(\)]+\d[×xX]\d[\d,\s]+мм²)'
        
        match = re.search(cable_pattern, line, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            
            # Извлечение количества (если есть)
            qty_match = re.search(r'(\d+)\s*шт', line)
            quantity = int(qty_match.group(1)) if qty_match else 1.0
            
            return {
                'type': 'cable',
                'name': name,
                'mark': self._extract_mark(name),
                'quantity': quantity,
                'unit': 'шт',
                'page_number': page_num,
                'raw_text': line
            }
        
        return None
    
    def _parse_fixture_line(self, line: str, page_num: int, material_type: str) -> Optional[dict]:
        """Парсинг строки со светильником"""
        # Паттерн для светильников
        fixture_pattern = r'(светиль[а-яё]+\d*\s*[0-9A-Zёа-яё]*)'
        
        match = re.search(fixture_pattern, line, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            
            qty_match = re.search(r'(\d+)\s*шт', line)
            quantity = int(qty_match.group(1)) if qty_match else 1.0
            
            return {
                'type': 'fixture',
                'name': name,
                'mark': '',
                'quantity': quantity,
                'unit': 'шт',
                'page_number': page_num,
                'raw_text': line
            }
        
        return None
    
    def _parse_device_line(self, line: str, page_num: int, material_type: str) -> Optional[dict]:
        """Парсинг строки с устройством (розетка, выключатель)"""
        device_keywords = ['розетка', 'выключатель', 'датчик', 'автомат', 'щит']
        
        if any(keyword in line.lower() for keyword in device_keywords):
            # Простое извлечение названия
            name_match = re.search(r'([А-ЯЁа-яё0-9\s\-\(\)]{5,50})', line)
            if name_match:
                name = name_match.group(1).strip()
                
                qty_match = re.search(r'(\d+)\s*шт', line)
                quantity = int(qty_match.group(1)) if qty_match else 1.0
                
                return {
                    'type': 'device',
                    'name': name,
                    'mark': '',
                    'quantity': quantity,
                    'unit': 'шт',
                    'page_number': page_num,
                    'raw_text': line
                }
        
        return None
    
    def _parse_general_line(self, line: str, page_num: int, material_type: str) -> Optional[dict]:
        """Парсинг общей строки материала"""
        # Простой парсер для остальных материалов
        parts = line.split()
        
        if len(parts) >= 2:
            # Предположим, что первые 2-3 слова - название
            name = ' '.join(parts[:3]).strip('.,;:')
            
            # Поиск количества
            quantity = 1.0
            for part in parts:
                if part.isdigit():
                    quantity = int(part)
                    break
            
            return {
                'type': 'general',
                'name': name,
                'mark': '',
                'quantity': quantity,
                'unit': 'шт',
                'page_number': page_num,
                'raw_text': line
            }
        
        return None
    
    def _extract_mark(self, name: str) -> str:
        """Извлечь маркировку из названия"""
        # Паттерн для маркировок: PPGng(A)-HF 3×2.5
        mark_pattern = r'([A-ZА-Я0-9\-\(\)]+[\d×xX][\d,\.]+)'
        match = re.search(mark_pattern, name)
        return match.group(0) if match else ''
    
    def extract_drawing_info(self) -> dict:
        """
        Извлечь информацию о чертежах
        
        Returns:
            Словарь с данными чертежей
        """
        drawings = []
        
        for page_num, text in self.text_pages.items():
            # Поиск обозначений чертежей
            drawing_pattern = r'(\d{2}-\d{2}-[А-ЯЁ0-9\.\-]+)'
            matches = re.findall(drawing_pattern, text)
            
            for match in matches:
                drawings.append({
                    'number': match,
                    'page_number': page_num,
                    'source_file': self.metadata.get('file_name', '')
                })
        
        return {
            'drawings': drawings,
            'total_pages': self.metadata.get('page_count', 0),
            'document_title': self.metadata.get('title', '')
        }
    
    def export_to_json(self, output_path: str) -> None:
        """
        Экспортировать извлечённые данные в JSON
        
        Args:
            output_path: Путь к выходному файлу
        """
        data = {
            'metadata': self.metadata,
            'extracted_at': datetime.now().isoformat(),
            'specifications': self.extract_specifications(),
            'drawings': self.extract_drawing_info()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def get_page_text(self, page_num: int) -> Optional[str]:
        """
        Получить текст конкретной страницы
        
        Args:
            page_num: Номер страницы
            
        Returns:
            Текст страницы или None
        """
        return self.text_pages.get(str(page_num))


def parse_pdf_to_materials(json_file_path: str) -> list[dict]:
    """
    Функция-обёртка для быстрого извлечения материалов
    
    Args:
        json_file_path: Путь к обработанному JSON файлу
        
    Returns:
        Список извлечённых материалов
    """
    extractor = PDFDataExtractor(json_file_path)
    return extractor.extract_specifications()


def batch_parse_processed_files(
    input_dir: str,
    output_dir: Optional[str] = None
) -> list[dict]:
    """
    Пакетно обработать все JSON файлы в директории
    
    Args:
        input_dir: Директория с JSON файлами
        output_dir: Директория для экспорта (опционально)
        
    Returns:
        Объединённый список всех материалов
    """
    input_path = Path(input_dir)
    all_materials = []
    
    for json_file in input_path.glob('**/*_processed.json'):
        print(f"Processing: {json_file}")
        
        try:
            extractor = PDFDataExtractor(str(json_file))
            materials = extractor.extract_specifications()
            
            # Добавить источник к каждому материалу
            for material in materials:
                material['source_file'] = json_file.name
                material['project_id'] = None  # Будет установлено при импорте
            
            all_materials.extend(materials)
            
            # Экспорт если указан output_dir
            if output_dir:
                output_path = Path(output_dir) / f"{json_file.stem}_materials.json"
                extractor.export_to_json(str(output_path))
                print(f"Exported to: {output_path}")
        
        except Exception as e:
            print(f"Error processing {json_file}: {e}")
    
    return all_materials


if __name__ == '__main__':
    # Пример использования
    import sys
    
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
    else:
        json_file = 'processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json'
    
    print(f"Parsing: {json_file}")
    
    extractor = PDFDataExtractor(json_file)
    materials = extractor.extract_specifications()
    
    print(f"\nFound {len(materials)} materials:")
    for mat in materials[:10]:  # Показать первые 10
        print(f"  - {mat['type']}: {mat['name']} x {mat['quantity']} {mat['unit']} (стр. {mat['page_number']})")
    
    if len(materials) > 10:
        print(f"  ... и ещё {len(materials) - 10}")
