# Обучение ML модели для классификации страниц

## Краткое руководство

### Шаг 1: Установка зависимостей

```bash
pip install scikit-learn pandas numpy
```

### Шаг 2: Обучение модели

```bash
# Обучить модель на данных из БД
python scripts/train_ml_classifier.py

# С указанием размера тестовой выборки
python scripts/train_ml_classifier.py --test-size 0.25

# Сохранить модель в другом месте
python scripts/train_ml_classifier.py --output models/my_classifier.pkl
```

### Шаг 3: Проверка модели

```bash
# Оценить точность на данных из БД
python scripts/train_ml_classifier.py --evaluate-only --model models/ml_classifier.pkl

# Протестировать на PDF файле
python scripts/predict_with_ml.py --model models/ml_classifier.pkl --pdf document.pdf
```

### Шаг 4: Интеграция в приложение

1. Скопируйте модель в папку проекта:
```bash
cp models/ml_classifier.pkl models/ml_classifier.pkl
```

2. Перезапустите сервер:
```bash
uvicorn app.main:app --reload
```

Классификатор автоматически загрузит модель и начнёт использовать её.

---

## Подробное руководство

### 1. Как работают данные

Модель обучается на признаках из таблицы `document_pages`:
- Визуальные признаки (изображения, таблицы, подписи)
- Текстовые признаки (длина, количество слов)
- Оценки категорий из rule-based классификатора

### 2. Распределение классов

Перед обучением проверьте баланс классов:

```python
from app.db import SessionLocal
from app import models

db = SessionLocal()
pages = db.query(models.DocumentPage).all()

categories = {}
for page in pages:
    cat = page.category
    categories[cat] = categories.get(cat, 0) + 1

print(categories)
# {'drawing': 45, 'specification': 42, ...}
```

Если один класс доминирует (>70%), используйте `class_weight='balanced'` (уже настроено).

### 3. Параметры обучения

```bash
# Размер тестовой выборки (по умолчанию 0.2 = 20%)
--test-size 0.3

# Путь сохранения модели
--output models/custom_classifier.pkl

# Только оценка существующей модели
--evaluate-only --model models/ml_classifier.pkl
```

### 4. Оценка качества

После обучения вы увидите:

```
Точность: 0.87

Classification report:
              precision    recall  f1-score   support

       title       0.92      0.88      0.90        25
      drawing       0.85      0.89      0.87        50
specification       0.88      0.85      0.86        40
       scheme       0.80      0.75      0.78        20
        other       0.75      0.80      0.78        15

    accuracy                           0.87       150
   macro avg       0.84      0.83      0.83       150
weighted avg       0.86      0.87      0.86       150
```

**Интерпретация:**
- **precision**: насколько точно модель предсказывает класс
- **recall**: какой процент класса модель нашла
- **f1-score**: гармоническое среднее precision и recall
- **accuracy**: общая точность (целевое значение >85%)

### 5. Улучшение точности

#### a) Больше данных
```bash
# Проверить количество данных
python scripts/train_ml_classifier.py 2>&1 | grep "Обучающая выборка"
```

Минимум 50 страниц для обучения, рекомендуется 200+.

#### b) Балансировка классов
Если один класс доминирует:

```python
# В train_ml_classifier.py уже настроено:
('clf', LogisticRegression(class_weight='balanced', ...))
```

#### c) Подбор гиперпараметров

```python
from sklearn.model_selection import GridSearchCV

param_grid = {
    'tfidf__ngram_range': [(1,1), (1,2), (1,3)],
    'tfidf__max_features': [5000, 10000, 15000],
    'clf__C': [0.1, 1.0, 10.0]
}

grid = GridSearchCV(pipeline, param_grid, cv=5)
grid.fit(X_train, y_train)

print(f"Лучшие параметры: {grid.best_params_}")
```

### 6. Использование модели

#### В коде приложения

```python
from app.services.document_classifier_v2 import classifier

# Проверить доступность ML модели
print(f"ML model available: {classifier.ml_model_available}")

# Классификация происходит автоматически в classify_pdf_pages()
classifications = classifier.classify_pdf_pages(pdf_content)
```

#### Скрипт для предсказаний

```bash
# Предсказать для PDF файла
python scripts/predict_with_ml.py --model models/ml_classifier.pkl --pdf doc.pdf

# Вывод:
# Стр.1: drawing (92%)
# Стр.2: specification (87%)
# Стр.3: drawing (78%)
```

### 7. Сравнение подходов

| Метод | Точность | Скорость | Требуется обучение |
|-------|----------|----------|-------------------|
| Rule-based | 60-70% | Быстро | Нет |
| ML (TF-IDF) | 80-90% | Быстро | Да |
| LayoutLM | 90-95% | Медленно | Да (опционально) |

### 8. Частые проблемы

**Ошибка: "Недостаточно данных для обучения"**
- Решение: соберите больше размеченных страниц (минимум 50)

**Низкая точность на тестовой выборке**
- Проверьте баланс классов
- Увеличьте размер обучающей выборки
- Попробуйте другие n-grams

**Модель не загружается**
- Проверьте путь: `models/ml_classifier.pkl`
- Убедитесь, что файл существует

### 9. Экспорт/импорт модели

```bash
# Экспорт
python scripts/train_ml_classifier.py --output models/export.pkl

# Импорт в другом проекте
import pickle
with open('models/export.pkl', 'rb') as f:
    model = pickle.load(f)
```

### 10. Мониторинг качества

Создайте скрипт для регулярной оценки:

```python
# scripts/evaluate_model.py
from app.db import SessionLocal
from app import models
import pickle

# Загрузить модель
with open('models/ml_classifier.pkl', 'rb') as f:
    model = pickle.load(f)

# Оценить на свежих данных
db = SessionLocal()
pages = db.query(models.DocumentPage).filter(
    # Только последние данные
).all()

# ... оценка ...
db.close()
```

---

## Готовые команды

```bash
# Полный цикл обучения
python scripts/train_ml_classifier.py

# Тестирование на PDF
python scripts/predict_with_ml.py --model models/ml_classifier.pkl --pdf test.pdf

# Оценка на данных БД
python scripts/train_ml_classifier.py --evaluate-only

# Сбор данных для ручного обучения
python scripts/collect_training_data.py --output training.json
```

## Следующие шаги

1. **Обучите модель** на текущих данных
2. **Протестируйте** на нескольких PDF файлах
3. **Сравните** с rule-based подходом
4. **Дообучите** при необходимости с новыми данными
