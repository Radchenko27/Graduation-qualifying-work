# Классификация документов с машинным обучением

## Текущий подход

Сейчас используется rule-based подход с ключевыми словами:
- Простая реализация
- Не требует данных для обучения
- Плохая точность (~60-70%)

## Улучшенные подходы

### Вариант 1: Улучшенный rule-based (быстро, без обучения)

Добавить больше признаков для классификации:

#### 1. Структурные признаки
```python
def extract_structural_features(text, page_num):
    """
    Извлечь структурные признаки страницы
    """
    features = {
        # Позиция на листе
        'is_first_page': page_num == 1,
        'is_last_page': False,  # определяется после обработки всего документа
        
        # Расположение текста
        'text_at_bottom': bool(re.search(r'.{0,50}(утверждаю|согласовано|разработал).*', text, re.IGNORECASE)),
        'text_at_top': bool(re.search(r'^.{0,50}(министерство|кафедра|университет).*', text, re.IGNORECASE)),
        
        # Наличие заголовков
        'has_title': bool(re.search(r'^(чертеж|спецификация|схема)\s*№', text, re.IGNORECASE)),
        
        # Длина текста
        'is_short_text': len(text.split()) < 20,
        'is_long_text': len(text.split()) > 200,
        
        # Наличие таблиц
        'has_table': bool(re.search(r'(поз\.?\s*\d+|№\s*\d+|позиция)', text)),
        
        # Наличие чертежных обозначений
        'has_drawing_number': bool(re.search(r'[А-Я]{2,}\.\d+\.\d+\.\d+', text)),
        
        # Наличие подписей
        'has_signatures': bool(re.search(r'(разработал|проверил|н\.контроль|т\.контроль)', text)),
    }
    
    return features
```

#### 2. Визуальные признаки (если есть изображения)
```python
def extract_visual_features(page):
    """
    Извлечь визуальные признаки из страницы PDF
    """
    features = {
        'image_count': 0,
        'has_large_image': False,
        'has_diagram': False,
        'image_to_text_ratio': 0,
    }
    
    # Извлекаем изображения
    try:
        images = page.get_images(full=True)
        features['image_count'] = len(images)
        
        # Проверяем размер изображений
        for img in images:
            xref = img[0]
            try:
                pix = fitz.PDFImage(xref)
                if pix.width > 400 and pix.height > 400:
                    features['has_large_image'] = True
            except:
                pass
    except:
        pass
    
    return features
```

#### 3. Улучшенная логика классификации
```python
def classify_page_v2(text, page_num, is_last_page, visual_features):
    """
    Улучшенная классификация с весами признаков
    """
    scores = {
        'title': 0,
        'drawing': 0,
        'specification': 0,
        'scheme': 0,
        'other': 0
    }
    
    # Титульник (стр. 1 + подписи)
    if page_num == 1:
        if visual_features.get('has_signatures'):
            scores['title'] += 5
        if 'министерство' in text.lower() or 'университет' in text.lower():
            scores['title'] += 4
    
    # Чертеж (обозначение + изображения)
    if re.search(r'[А-Я]{2,}\.\d+\.\d+\.\d+', text):
        scores['drawing'] += 5
    if visual_features.get('image_count', 0) > 2:
        scores['drawing'] += 2
    
    # Спецификация (таблица + слова)
    if visual_features.get('has_table'):
        scores['specification'] += 3
    spec_keywords = ['спецификация', 'ведомость', 'материалы', 'количество', 'ед. изм.']
    if sum(1 for kw in spec_keywords if kw in text.lower()) >= 2:
        scores['specification'] += 3
    
    # Схема
    scheme_keywords = ['схема', 'блок-схема', 'электрическая', 'гидравлическая']
    if sum(1 for kw in scheme_keywords if kw in text.lower()) >= 1:
        scores['scheme'] += 3
    
    return max(scores, key=scores.get)
```

**Ожидаемая точность:** 75-85%

---

### Вариант 2: Классическое ML (средняя сложность)

Использовать готовые модели NLP без дообучения:

#### 1. TF-IDF + Классификатор
```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

class MLClassifier:
    def __init__(self):
        self.pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(
                ngram_range=(1, 3),
                max_features=10000,
                stop_words='russian'
            )),
            ('clf', LogisticRegression(max_iter=1000))
        ])
    
    def train(self, texts, labels):
        """
        Обучить на размеченных данных
        texts: ['текст страницы 1', 'текст страницы 2', ...]
        labels: ['drawing', 'specification', ...]
        """
        self.pipeline.fit(texts, labels)
    
    def predict(self, texts):
        return self.pipeline.predict(texts)
```

**Как собрать данные для обучения:**
```python
# 1. Экспортировать уже классифицированные страницы
import os
os.environ["DATABASE_URL"] = "postgresql://..."

from app.db import SessionLocal
from app import models

db = SessionLocal()

data = []
labels = []

for page in db.query(models.DocumentPage).all():
    if page.page_metadata:
        import json
        metadata = json.loads(page.page_metadata)
        text = f"Категория: {page.category} Текст: {metadata.get('text', '')[:500]}"
        data.append(text)
        labels.append(page.category)

# Сохранить для обучения
import pickle
with open('training_data.pkl', 'wb') as f:
    pickle.dump({'texts': data, 'labels': labels}, f)

db.close()
```

**Ожидаемая точность:** 85-90% (при 100+ размеченных страницах)

---

### Вариант 3: Глубокое обучение (сложно, лучшая точность)

Использовать предобученные модели:

#### 1. YOLO для обнаружения объектов на изображениях страниц
```python
from ultralytics import YOLO

# Модель обучена на чертежах
model = YOLO('yolov8_custom_drawings.pt')

def detect_drawing_elements(page_image):
    """
    Обнаружить элементы чертежа на странице
    """
    results = model(page_image)
    
    elements = {
        'has_dimensions': False,
        'has_views': False,
        'has_technical_text': False,
    }
    
    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            if cls == 0:  # размеры
                elements['has_dimensions'] = True
            elif cls == 1:  # виды
                elements['has_views'] = True
    
    return elements
```

#### 2. LayoutLM / Donut для понимания макета
```python
from transformers import LayoutLMTokenizer, LayoutLMForSequenceClassification

# Предобученная модель для документов
tokenizer = LayoutLMTokenizer.from_pretrained('microsoft/layoutlm-base-uncased')
model = LayoutLMForSequenceClassification.from_pretrained('your-model-path')

def classify_with_layoutlm(text, bboxes, image):
    """
    Классификация с учётом текстового и визуального контента
    """
    inputs = tokenizer(
        text,
        boxes=bboxes,
        image=image,
        return_tensors="pt"
    )
    
    outputs = model(**inputs)
    prediction = outputs.logits.argmax(-1).item()
    
    return prediction
```

**Ожидаемая точность:** 90-95% (при 500+ размеченных страницах)

---

## Практический план улучшения

### Этап 1: Улучшение rule-based (1-2 часа)
1. Добавить визуальные признаки (изображения, таблицы)
2. Добавить структурные признаки (позиция, длина)
3. Улучшить веса категорий

### Этап 2: Сбор данных для ML (1-3 дня)
1. Экспортировать текущие классификации
2. Ручная разметка 100-200 страниц
3. Сохранить в формате JSON/CSV

### Этап 3: Обучение простой модели (1 день)
1. TF-IDF + LogisticRegression
2. Валидация на тестовом наборе
3. Интеграция в проект

### Этап 4: Продвинутая модель (неделя)
1. LayoutLM или аналогичная
2. Дообучение на данных проекта
3. A/B тестирование

---

## Быстрый старт: Улучшение текущего классификатора

Создайте `app/services/document_classifier_v2.py`:

```python
import re
import json
from typing import Dict
from dataclasses import dataclass

@dataclass
class PageClassification:
    page_number: int
    category: str
    confidence: float
    content_type: str
    metadata: Dict

class DocumentClassifierV2:
    """Улучшенный классификатор с визуальными и структурными признаками"""
    
    def __init__(self):
        # Ключевые слова с весами
        self.keywords = {
            'drawing': {
                'чертеж': 3, 'черт.': 2, 'КЖ': 3, 'КМ': 3, 'КМД': 3,
                'архитектурные': 2, 'конструктивные': 2, 'разрез': 2,
                'план': 2, 'фасад': 2, 'вид': 2, 'узлы': 2
            },
            'specification': {
                'спецификация': 4, 'ведомость': 3, 'материалы': 2,
                'оборудование': 2, 'изделия': 2, 'количество': 1,
                'ед. изм.': 1, 'позиция': 2, 'наименование': 1
            },
            'scheme': {
                'схема': 3, 'блок-схема': 3, 'структурная': 2,
                'электрическая': 2, 'гидравлическая': 2
            },
            'title': {
                'министерство': 3, 'университет': 3, 'институт': 2,
                'кафедра': 2, 'утверждаю': 3, 'разработал': 2,
                'проверил': 2, 'согласовано': 2
            }
        }
        
        # Паттерны
        self.patterns = {
            'drawing_number': re.compile(r'[А-Я]{2,}\.\d+\.\d+\.\d+'),
            'table': re.compile(r'(поз\.?\s*\d+|№\s*\d+|позиция)'),
            'signatures': re.compile(r'(разработал|проверил|н\.контроль|т\.контроль)'),
        }
    
    def classify_pdf_pages(self, pdf_content: bytes):
        import fitz
        
        doc = fitz.open(stream=pdf_content, filetype="pdf")
        classifications = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text("text").lower()
            
            # Извлечь визуальные признаки
            visual_features = self._extract_visual_features(page)
            
            # Классификация
            classification = self._classify_page(
                page_num + 1, 
                text, 
                visual_features,
                len(doc)
            )
            classifications.append(classification)
        
        doc.close()
        return classifications
    
    def _extract_visual_features(self, page):
        features = {
            'image_count': 0,
            'has_table': False,
            'has_signatures': False,
        }
        
        # Изображения
        try:
            images = page.get_images(full=True)
            features['image_count'] = len(images)
        except:
            pass
        
        # Таблицы
        text = page.get_text("text").lower()
        if self.patterns['table'].search(text):
            features['has_table'] = True
        
        # Подписи
        if self.patterns['signatures'].search(text):
            features['has_signatures'] = True
        
        return features
    
    def _classify_page(self, page_num, text, visual_features, total_pages):
        scores = {cat: 0 for cat in ['title', 'drawing', 'specification', 'scheme', 'other']}
        
        # Титульник (стр. 1 + подписи)
        if page_num == 1 and visual_features['has_signatures']:
            scores['title'] += 5
        
        # Подсчёт ключевых слов
        for category, words in self.keywords.items():
            for word, weight in words.items():
                if word in text:
                    scores[category] += weight
        
        # Чертежное обозначение
        if self.patterns['drawing_number'].search(text):
            scores['drawing'] += 4
        
        # Таблицы → спецификация
        if visual_features['has_table']:
            scores['specification'] += 3
        
        # Изображения → чертеж
        if visual_features['image_count'] >= 2:
            scores['drawing'] += 2
        
        # Определение победителя
        best_category = max(scores, key=scores.get)
        best_score = scores[best_category]
        
        # Уверенность
        total_score = sum(scores.values())
        confidence = min(best_score / max(total_score, 1), 0.95)
        
        if best_score == 0:
            confidence = 0.3
            best_category = 'other'
        
        return PageClassification(
            page_number=page_num,
            category=best_category,
            confidence=confidence,
            content_type='table' if visual_features['has_table'] else 'text',
            metadata={'visual_features': visual_features}
        )

classifier = DocumentClassifierV2()
```

**Замена в `create_document`:**
```python
from ...services.document_classifier_v2 import classifier
```

---

## Сравнение подходов

| Подход | Точность | Сложность | Время |
|--------|----------|-----------|-------|
| Текущий (keywords) | 60-70% | Низкая | 0 |
| Улучшенный rule-based | 75-85% | Низкая | 1-2 ч |
| TF-IDF + ML | 85-90% | Средняя | 1 день |
| LayoutLM / Donut | 90-95% | Высокая | 1 неделя |

---

## Рекомендация

**Начните с Варианта 1 (улучшенный rule-based):**
1. Быстро (~2 часа)
2. Не требует данных для обучения
3. Улучшит точность на 15-20%
4. Можно постепенно добавлять признаки

Если нужно больше точности → переходите к Варианту 2 (сбор данных + ML).
