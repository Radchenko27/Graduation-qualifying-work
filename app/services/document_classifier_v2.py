"""
Классификация документов через OCR основной надписи (штампа)

Принцип: Каждый лист чертежа/документа имеет основную надпись (штамп)
в правом нижнем углу (по ГОСТ 2.104-2006), где указан тип документа.

Категории определяются по тексту из штампа + ключевые слова.
"""
import io
import json
import pickle
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class PageClassification:
    """Результат классификации страницы"""
    page_number: int
    category: str
    confidence: float
    content_type: str
    metadata: Dict


# Слова для поиска в основной надписи (штампе)
STAMP_KEYWORDS = {
    'drawing': [
        'чертеж', 'черт', 'чертёж', 'чертежа',
        'план', 'плана', 'планировка',
        'разрез', 'разреза',
        'фасад', 'фасада',
        'узел', 'узла', 'узлов',
        'схема', 'схемы',  # иногда в штампе чертежа пишут "схема"
    ],
    'specification': [
        'спецификация', 'спецификации',
        'ведомость', 'ведомости',
        'перечень', 'перечня',
        'документация', 'документации',
        'экспликация',
    ],
    'scheme': [
        'схема', 'схемы',
        'блок-схема', 'блок-схемы',
        'структурная',
        'принципиальная',
        'функциональная',
        'электрическая',
        'гидравлическая',
        'пневматическая',
    ],
    'title': [
        'титул', 'титульный', 'титульная',
        'утверждаю',
        'лист титульный',
    ]
}

# Слова для поиска по всему тексту страницы
TEXT_KEYWORDS = {
    'drawing': [
        'чертеж', 'черт', 'чертёж',
        'план', 'разрез', 'фасад',
        'узел', 'узлы',
        'конструкция', 'конструктив',
        'арматура', 'бетон', 'колонна', 'балка',
        'фундамент', 'перекрытие', 'стена',
    ],
    'specification': [
        'спецификация', 'ведомость',
        'материалов', 'оборудования',
        'изделий', 'деталей',
        'позиция', 'поз',
        'наименование', 'обозначение',
        'количество', 'масса', 'кг',
        'марка', 'гост',
    ],
    'scheme': [
        'схема', 'блок-схема',
        'структурная', 'принципиальная',
        'электрическая', 'гидравлическая',
        'подключение', 'кабель', 'провод',
        'трубопровод', 'арматура',
    ],
    'title': [
        'утверждаю', 'разработал', 'проверил',
        'согласовано', 'н.контроль', 'т.контроль',
        'утвердил', 'проверил',
        'министерство', 'университет', 'институт',
        'кафедра', 'факультет',
        'диплом', 'курсовой',
    ]
}


class DocumentClassifierV2:
    """
    Классификатор на основе OCR основной надписи (штампа)
    """
    
    def __init__(self):
        self.ml_model_available = False
        self.ml_model = None
        self._init_ml_model()
    
    def _init_ml_model(self):
        """Загрузить ML модель если есть"""
        try:
            model_paths = [
                Path(__file__).parent.parent.parent / "models" / "ml_classifier_v2.pkl",
                Path("models/ml_classifier_v2.pkl"),
            ]
            for model_path in model_paths:
                if model_path.exists():
                    with open(model_path, 'rb') as f:
                        self.ml_model = pickle.load(f)
                    self.ml_model_available = True
                    print(f"[ML] Модель загружена: {model_path.name}")
                    return
        except Exception as e:
            print(f"[ML] Не удалось загрузить: {e}")
    
    def classify_pdf_pages(self, pdf_content: bytes) -> List[PageClassification]:
        """Классифицировать все страницы PDF"""
        try:
            import fitz
        except ImportError:
            print("[ERROR] PyMuPDF не установлен: pip install PyMuPDF")
            return []
        
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        results = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text")
            
            classification = self._classify_page(
                page_num + 1,
                page,
                text,
                len(doc)
            )
            results.append(classification)
        
        doc.close()
        return results
    
    def _classify_page(self, page_num: int, page, text: str, total_pages: int) -> PageClassification:
        """
        Классифицировать одну страницу
        
        Приоритет:
        1. Основная надпись (штамп) - самый надёжный признак
        2. Ключевые слова в тексте
        3. Позиция страницы (первая = титульник)
        4. Количество текста
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        # === 1. Читаем основную надпись (штамп) ===
        stamp_text = self._read_stamp(page)
        stamp_scores = self._score_by_keywords(stamp_text, STAMP_KEYWORDS, weight=10)
        
        # === 2. Ключевые слова по всему тексту ===
        text_scores = self._score_by_keywords(text_lower, TEXT_KEYWORDS, weight=2)
        
        # === 3. Специальные признаки ===
        special_scores = self._score_special_features(page_num, text_lower, words, total_pages)
        
        # === Суммируем все очки ===
        scores = {
            'title': stamp_scores['title'] + text_scores['title'] + special_scores['title'],
            'drawing': stamp_scores['drawing'] + text_scores['drawing'] + special_scores['drawing'],
            'specification': stamp_scores['specification'] + text_scores['specification'] + special_scores['specification'],
            'scheme': stamp_scores['scheme'] + text_scores['scheme'] + special_scores['scheme'],
            'other': 0
        }
        
        # === Выбираем победителя ===
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        total_score = sum(scores.values())
        
        # === Уверенность ===
        if best_score == 0:
            # Ничего не найдено - значит это просто лист с картинкой
            category = 'drawing' if len(words) < 50 else 'other'
            confidence = 0.3
        elif stamp_scores[best_category] > 0:
            # Есть подтверждение из штампа - высокая уверенность
            confidence = min(0.7 + (best_score / total_score) * 0.25, 0.95)
        else:
            # Только текстовые признаки - средняя уверенность
            confidence = min(0.5 + (best_score / total_score) * 0.3, 0.75)
        
        # === Тип содержимого ===
        content_type = self._detect_content_type(page, words)
        
        # === Метаданные ===
        metadata = {
            'stamp_text': stamp_text[:300],  # первые 300 символов штампа
            'stamp_scores': stamp_scores,
            'text_scores': text_scores,
            'special_scores': special_scores,
            'total_scores': scores,
            'word_count': len(words),
            'text_length': len(text)
        }
        
        return PageClassification(
            page_number=page_num,
            category=category if best_score == 0 else best_category,
            confidence=confidence,
            content_type=content_type,
            metadata=metadata
        )
    
    def _read_stamp(self, page) -> str:
        """
        Прочитать текст основной надписи (штампа)
        
        По ГОСТ 2.104-2006 основная надпись находится в правом нижнем углу.
        Пробуем несколько областей.
        """
        try:
            w = page.rect.width
            h = page.rect.height
            
            # Вариант 1: Правый нижний угол (стандарт)
            stamp = page.get_textbox((w * 0.55, h * 0.82, w, h)).lower()
            if len(stamp.strip()) > 5:
                return stamp
            
            # Вариант 2: Нижняя полоса чуть выше
            stamp = page.get_textbox((w * 0.5, h * 0.75, w, h * 0.95)).lower()
            if len(stamp.strip()) > 5:
                return stamp
            
            # Вариант 3: Весь нижний край
            stamp = page.get_textbox((0, h * 0.8, w, h)).lower()
            if len(stamp.strip()) > 5:
                return stamp
            
            # Вариант 4: Верхний правый угол (иногда штамп сверху)
            stamp = page.get_textbox((w * 0.6, 0, w, h * 0.15)).lower()
            if len(stamp.strip()) > 5:
                return stamp
            
        except Exception as e:
            print(f"[WARN] Ошибка чтения штампа: {e}")
        
        return ""
    
    def _score_by_keywords(self, text: str, keyword_dict: Dict, weight: int = 1) -> Dict:
        """
        Подсчитать очки по ключевым словам (простой поиск подстрок, без regex)
        
        Args:
            text: Текст для анализа
            keyword_dict: Словарь {категория: [слова]}
            weight: Вес каждого совпадения
            
        Returns:
            {категория: очки}
        """
        scores = {'title': 0, 'drawing': 0, 'specification': 0, 'scheme': 0}
        
        for category, keywords in keyword_dict.items():
            for keyword in keywords:
                # Простой поиск: сколько раз слово встречается в тексте
                count = text.count(keyword)
                scores[category] += count * weight
        
        return scores
    
    def _score_special_features(self, page_num: int, text_lower: str, words: List[str], total_pages: int) -> Dict:
        """
        Специальные признаки (без regex)
        
        Returns:
            {категория: очки}
        """
        scores = {'title': 0, 'drawing': 0, 'specification': 0, 'scheme': 0}
        
        # === Признак 1: Первая страница = титульник ===
        if page_num == 1:
            scores['title'] += 3
            # Если мало текста и есть подписи - точно титульник
            if len(words) < 100:
                scores['title'] += 5
        
        # === Признак 2: Мало текста = чертёж (картинка) ===
        if len(words) < 30:
            scores['drawing'] += 3
        
        # === Признак 3: Много текста + таблицы = спецификация ===
        if len(words) > 150:
            # Проверяем наличие табличных слов
            table_words = ['позиция', 'поз', 'наименование', 'количество', 'масса', 'кг', 'шт']
            table_count = sum(1 for w in table_words if w in text_lower)
            if table_count >= 2:
                scores['specification'] += 4
        
        # === Признак 4: Чертёжное обозначение (простая проверка) ===
        # ГОСТ 2.201: формат АБВ.ХХХХХ.ХХХ - ищем точки и цифры
        if '.' in text_lower:
            lines = text_lower.split('\n')
            for line in lines[:20]:  # проверяем первые 20 строк
                parts = line.split('.')
                if len(parts) >= 3:
                    # Проверяем что есть цифры после точек
                    has_digits = any(p.strip().isdigit() for p in parts)
                    if has_digits and len(line) < 50:
                        scores['drawing'] += 2
                        break
        
        # === Признак 5: Последняя страница ===
        if page_num == total_pages and total_pages > 1:
            # Часто последняя страница - ведомость или спецификация
            if len(words) > 50:
                scores['specification'] += 1
        
        return scores
    
    def _detect_content_type(self, page, words: List[str]) -> str:
        """Определить тип содержимого страницы"""
        # Проверяем наличие изображений
        try:
            images = page.get_images()
            if len(images) > 0:
                return 'image'
        except:
            pass
        
        # По количеству текста
        if len(words) < 20:
            return 'image'
        elif len(words) > 100:
            return 'text'
        else:
            return 'mixed'


# Singleton
classifier = DocumentClassifierV2()
