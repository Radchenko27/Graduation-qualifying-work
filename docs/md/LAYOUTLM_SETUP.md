# Установка зависимостей для LayoutLM классификации

## Быстрая установка

```bash
# Основные зависимости
pip install transformers torch pillow opencv-python

# Для работы с PDF
pip install PyMuPDF

# Дополнительные утилиты
pip install accelerate datasets
```

## Проверка установки

```bash
python -c "import torch; import transformers; print('LayoutLM ready!')"
```

## Зависимости

### Обязательные
- `transformers>=4.30.0` - Hugging Face transformers
- `torch>=2.0.0` - PyTorch
- `pillow>=9.0.0` - Обработка изображений
- `opencv-python>=4.5.0` - Обработка изображений
- `PyMuPDF>=1.23.0` - Работа с PDF

### Опциональные (для дообучения)
- `accelerate>=0.20.0` - Ускорение обучения
- `datasets>=2.14.0` - Датасеты Hugging Face
- `scikit-learn>=1.3.0` - Метрики оценки
- `wandb` - Логирование экспериментов (опционально)

## Использование GPU (рекомендуется)

```bash
# Проверка доступности GPU
python -c "import torch; print('GPU available:', torch.cuda.is_available())"

# Если GPU есть, он будет использоваться автоматически
```

## Настройка памяти

Для больших PDF файлов может потребоваться увеличение памяти:

```python
# В document_classifier_v2.py можно настроить:
# max_length=512 (по умолчанию)
# batch_size=8 (если обрабатываете много страниц)
```

## Дообучение модели (опционально)

Если хотите улучшить точность на ваших данных:

1. Соберите размеченные данные:
```bash
python scripts/collect_training_data.py
```

2. Дообучите модель (см. `docs/md/LAYOUTLM_TRAINING.md`)

3. Загрузите дообученную модель в классификатор

## Fallback

Если LayoutLM недоступен (не установлены зависимости), классификатор автоматически переключится на улучшенный rule-based подход.
