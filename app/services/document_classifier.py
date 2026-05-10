"""
Автоматическая классификация страниц PDF документов
Каждая страница классифицируется на одну из 5 категорий:
- drawing (чертеж)
- specification (спецификация)
- scheme (схема)
- title (титульник)
- other (другое)
"""
import io
import re
import json
from typing import List, Dict, Optional
from dataclasses import dataclass

@dataclass
class PageClassification:
    """Результат классификации страницы"""
    page_number: int  # Номер страницы (с 1)
    category: str  # drawing, specification, scheme, title, other
    confidence: float  # Уверенность классификации (0.0 - 1.0)
    content_type: str  # text, image, table
    metadata: Dict  # Дополнительная информация


class DocumentClassifier:
    """Классификатор страниц PDF документов"""
    
    # Ключевые слова для категории "чертеж"
    DRAWING_KEYWORDS = [
        'чертеж', 'чертежи', 'черт.', 'чертеж №', 'чертеж №',
        'конструктивные решения', 'архитектурные решения', 'КЖ', 'КМ', 'КМД',
        'АБВГ', 'обозначение', 'привязка', 'оси', 'размер', 'сборка',
        'узлы', 'деталировка', 'вид', 'фасад', 'профиль'
    ]
    
    # Ключевые слова для категории "спецификация"
    SPECIFICATION_KEYWORDS = [
        'спецификация', 'ведомость', 'материалы', 'оборудование', 'изделия',
        'количество', 'ед. изм.', 'примечание', 'позиция', 'поз.', '№ поз.',
        'наименование', 'кол-во', 'замену', 'замен', 'масс', 'кг'
    ]
    
    # Ключевые слова для категории "схема"
    SCHEME_KEYWORDS = [
        'схема', 'схемы', 'сх.', 'алгоритм', 'блок-схема', 'структурная',
        'функциональная', 'принципиальная', 'кинематическая', 'гидравлическая',
        'электрическая', 'пневматическая', 'подключение', 'соединение'
    ]
    
    # Ключевые слова для категории "титульник"
    TITLE_KEYWORDS = [
        'министерство', 'ведомство', 'университет', 'институт', 'кафедра',
        'утверждаю', 'утвердил', 'согласовано', 'согласовал', 'разработал',
        'проверил', 'н.контроль', 'т.контроль', 'зам.главного инженера',
        'главный инженер', 'стадия', 'листов', 'лист', 'замен', 'заменяет'
    ]
    
    def __init__(self):
        # Паттерн для обозначения чертежа (например, АБВГ.12345.001)
        self.drawing_number_pattern = re.compile(
            r'([А-Я]{2,6}\.?\s*\d+\.?\s*\d+\.?\s*\d+)',
            re.IGNORECASE
        )
        
        # Паттерн для таблицы
        self.table_pattern = re.compile(
            r'(поз\.?\s*\d+)|'
            r'(№\s*\d+)|'
            r'(позиция\s*\d+)|'
            r'(\d+\s+\S+\s+[\d.]+\s+[\d.]+)',
            re.IGNORECASE
        )
    
    def classify_pdf_pages(self, pdf_content: bytes) -> List[PageClassification]:
        """
        Классифицировать все страницы PDF документа
        
        Args:
            pdf_content: бинарное содержимое PDF файла
            
        Returns:
            Список классификаций для каждой страницы
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            print("PyMuPDF не установлен, используем базовую классификацию")
            return self._basic_classification(10)  # По умолчанию 10 страниц
        
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        classifications = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").lower()
            
            # Извлекаем метаданные страницы
            metadata = self._extract_page_metadata(page, text)
            
            # Классифицируем страницу
            classification = self._classify_page(page_num + 1, text, metadata)
            classifications.append(classification)
        
        doc.close()
        return classifications
    
    def _classify_page(self, page_num: int, text: str, metadata: Dict) -> PageClassification:
        """Классифицировать одну страницу"""
        
        # Подсчет совпадений по категориям
        scores = {
            'drawing': 0,
            'specification': 0,
            'scheme': 0,
            'title': 0,
            'other': 0
        }
        
        # Проверка на титульник (особенно первая страница)
        if page_num == 1:
            title_score = sum(1 for kw in self.TITLE_KEYWORDS if kw in text)
            scores['title'] = title_score * 3  # Усиленный вес для титульника
        
        # Проверка на чертежи
        drawing_score = sum(1 for kw in self.DRAWING_KEYWORDS if kw in text)
        if self.drawing_number_pattern.search(text):
            drawing_score += 3
        scores['drawing'] = drawing_score * 2
        
        # Проверка на спецификации
        spec_score = sum(1 for kw in self.SPECIFICATION_KEYWORDS if kw in text)
        if self.table_pattern.search(text):
            spec_score += 2
        scores['specification'] = spec_score * 2
        
        # Проверка на схемы
        scheme_score = sum(1 for kw in self.SCHEME_KEYWORDS if kw in text)
        scores['scheme'] = scheme_score * 2
        
        # Определение победителя
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        # Определение типа содержимого
        content_type = self._detect_content_type(text)
        
        # Расчет уверенности
        total_words = len(text.split())
        if best_score > 0 and total_words > 10:
            confidence = min(0.4 + (best_score * 0.1), 0.95)
        elif total_words < 10:
            confidence = 0.3  # Мало текста - низкая уверенность
            best_category = 'other'
        else:
            confidence = 0.5
            best_category = 'other'
        
        return PageClassification(
            page_number=page_num,
            category=best_category,
            confidence=confidence,
            content_type=content_type,
            metadata=metadata
        )
    
    def _detect_content_type(self, text: str) -> str:
        """Определить тип содержимого страницы"""
        if len(text) < 30:
            return 'image'
        
        # Проверка на таблицы
        lines = text.split('\n')
        table_lines = sum(1 for line in lines if len(line.split()) > 4)
        if table_lines > len(lines) * 0.4:
            return 'table'
        
        return 'text'
    
    def _extract_page_metadata(self, page, text: str) -> Dict:
        """Извлечь метаданные со страницы"""
        metadata = {
            'has_images': False,
            'has_tables': False,
            'text_length': len(text),
            'page_width': float(page.rect.width),
            'page_height': float(page.rect.height)
        }
        
        # Поиск изображений
        try:
            images = page.get_images(full=True)
            metadata['has_images'] = len(images) > 0
            metadata['image_count'] = len(images)
        except:
            pass
        
        # Поиск таблиц
        if self.table_pattern.search(text):
            metadata['has_tables'] = True
        
        # Извлечение обозначения чертежа
        match = self.drawing_number_pattern.search(text)
        if match:
            metadata['drawing_number'] = match.group(0).strip()
        
        return metadata
    
    def _basic_classification(self, page_count: int) -> List[PageClassification]:
        """Базовая классификация без PyMuPDF"""
        return [
            PageClassification(
                page_number=i + 1,
                category='other',
                confidence=0.3,
                content_type='text',
                metadata={}
            )
            for i in range(page_count)
        ]
    
    @staticmethod
    def category_to_russian(category: str) -> str:
        """Преобразовать категорию на русском"""
        categories = {
            'drawing': 'Чертеж',
            'specification': 'Спецификация',
            'scheme': 'Схема',
            'title': 'Титульник',
            'other': 'Другое'
        }
        return categories.get(category, category)


# Singleton
classifier = DocumentClassifier()
