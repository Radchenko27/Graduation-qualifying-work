# Дообучение LayoutLM модели для классификации страниц

## Подготовка данных

### 1. Сбор данных из БД

```bash
# Собрать данные с визуальными признаками
python scripts/collect_training_data.py --output training_data.json

# Или с информацией о документах
python scripts/collect_training_data.py --with-docs --output training_data_with_docs.json
```

### 2. Ручная разметка (если нужно)

Если текущие классификации недостаточно точны, создайте файл с ручной разметкой:

```json
[
  {
    "text": "текст страницы...",
    "bboxes": [[100, 200, 300, 250], ...],
    "label": "drawing"
  },
  ...
]
```

Категории:
- `0` - title (титульник)
- `1` - drawing (чертеж)
- `2` - specification (спецификация)
- `3` - scheme (схема)
- `4` - other (другое)

## Дообучение модели

### Шаг 1: Установка зависимостей

```bash
pip install transformers torch accelerate datasets scikit-learn
```

### Шаг 2: Создание датасета

```python
from datasets import Dataset
import json

# Загрузить данные
with open('training_data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Преобразовать в формат для обучения
texts = []
labels = []
bboxes = []

category_to_id = {
    'title': 0,
    'drawing': 1,
    'specification': 2,
    'scheme': 3,
    'other': 4
}

for page in data:
    # Текстовые признаки из metadata
    if page.get('metadata'):
        import json as js
        metadata = js.loads(page['metadata'])
        text = f"Категория: {page['category']} Текст: {metadata.get('text_length', 0)} символов"
        
        texts.append(text)
        labels.append(category_to_id[page['category']])
        bboxes.append(metadata.get('visual_features', {}))

# Создать датасет
dataset = Dataset.from_dict({
    'text': texts,
    'labels': labels,
    'bboxes': bboxes
})
```

### Шаг 3: Дообучение

```python
from transformers import LayoutLMTokenizer, LayoutLMForSequenceClassification
from transformers import TrainingArguments, Trainer
import torch

# Загрузка модели и токенизатора
model_name = 'microsoft/layoutlm-base-uncased'
tokenizer = LayoutLMTokenizer.from_pretrained(model_name)
model = LayoutLMForSequenceClassification.from_pretrained(
    model_name,
    num_labels=5
)

# Токенизация
def preprocess_data(examples):
    tokenized = tokenizer(
        examples['text'],
        boxes=examples['bboxes'],
        padding='max_length',
        truncation=True,
        max_length=512
    )
    tokenized['labels'] = examples['labels']
    return tokenized

tokenized_dataset = dataset.map(preprocess_data, batched=True)

# Настройки обучения
training_args = TrainingArguments(
    output_dir='./layoutlm-finetuned',
    num_train_epochs=3,
    per_device_train_batch_size=8,
    learning_rate=5e-5,
    weight_decay=0.01,
    evaluation_strategy='epoch',
    save_strategy='epoch',
    logging_steps=50,
    load_best_model_at_end=True
)

# Trainer
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    eval_dataset=tokenized_dataset,  # В идеале разделить на train/test
    tokenizer=tokenizer
)

# Обучение
trainer.train()

# Сохранение
model.save_pretrained('./layoutlm-custom')
tokenizer.save_pretrained('./layoutlm-custom')
```

### Шаг 4: Оценка точности

```python
from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

# Предсказания
predictions = trainer.predict(tokenized_dataset)
pred_labels = np.argmax(predictions.predictions, axis=-1)

# Отчёт
true_labels = predictions.label_ids
print(classification_report(true_labels, pred_labels, 
                           target_names=['title', 'drawing', 'specification', 'scheme', 'other']))

# Матрица ошибок
print(confusion_matrix(true_labels, pred_labels))
```

### Шаг 5: Интеграция в приложение

1. Скопируйте дообученную модель в папку проекта:
```bash
mkdir -p models/layoutlm-custom
cp -r ./layoutlm-custom/* models/layoutlm-custom/
```

2. Обновите `document_classifier_v2.py`:

```python
def _init_layoutlm(self):
    try:
        from transformers import LayoutLMTokenizer, LayoutLMForSequenceClassification
        
        # Загрузка вашей дообученной модели
        self.layoutlm_tokenizer = LayoutLMTokenizer.from_pretrained(
            'models/layoutlm-custom'
        )
        self.layoutlm_model = LayoutLMForSequenceClassification.from_pretrained(
            'models/layoutlm-custom'
        )
        
        self.layoutlm_available = True
        print("[LayoutLM] Дообученная модель загружена")
        
    except Exception as e:
        print(f"[LayoutLM] Ошибка: {e}")
        self.layoutlm_available = False
```

## Улучшение точности

### 1. Больше данных
- Минимум 100 размеченных страниц для базового дообучения
- Рекомендуется 500+ страниц для хорошей точности

### 2. Балансировка классов
```python
from sklearn.utils.class_weight import compute_class_weight

# Вычислить веса классов
class_weights = compute_class_weight(
    'balanced',
    classes=np.unique(labels),
    y=labels
)

# Использовать в модели
model.classifier.weight = torch.nn.Parameter(
    torch.tensor(class_weights).float()
)
```

### 3. Аугментация данных
- Добавление шума в текст
- Случайное удаление слов
- Изменение bounding boxes

### 4. Ensemble моделей
```python
# Комбинация LayoutLM + rule-based
def ensemble_predict(layoutlm_pred, rule_based_pred, confidence):
    if confidence > 0.8:
        return layoutlm_pred
    else:
        # Голосование
        return rule_based_pred if rule_based_confidence > 0.7 else layoutlm_pred
```

## Мониторинг

Используйте Weights & Biases для отслеживания экспериментов:

```bash
pip install wandb
wandb login
```

```python
training_args = TrainingArguments(
    ...
    report_to="wandb",
    run_name="layoutlm-finetraining-v1"
)
```

## Результат

После дообучения ожидаемая точность:
- **До дообучения:** 70-80% (предобученная модель)
- **После дообучения:** 85-95% (на ваших данных)

## Частые проблемы

### Низкая точность
- Недостаточно данных для обучения
- Дисбаланс классов
- Переобучение (уменьшите epochs, увеличьте dropout)

### Ошибки памяти
- Уменьшите `max_length` (256 вместо 512)
- Уменьшите `batch_size` (4 вместо 8)
- Используйте GPU

### Модель не сходится
- Уменьшите learning_rate (1e-5 вместо 5e-5)
- Добавьте weight_decay
- Используйте warmup_steps
