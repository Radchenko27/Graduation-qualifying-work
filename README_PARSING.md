# Руководство по парсингу PDF документов

## Обзор

Этот модуль позволяет извлекать данные из обработанных PDF документов (спецификации, сметы, перечни материалов) для автоматического заполнения базы данных.

---

## Структура данных

### Входные данные

Обработанные JSON файлы находятся в директории `processed/`:

```
processed/
├── 03-23-ОГР01.1-ЭОМ1.1-Изм.1/
│   ├── 03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json
│   └── images/
└── 17-23-00-ЭОМ/
    └── 17-23-00-ЭОМ_processed.json
```

### Структура JSON файла

```json
{
  "metadata": {
    "file_name": "имя_файла.pdf",
    "page_count": 157,
    "title": "Обложка документа",
    ...
  },
  "text": {
    "0": "Текст страницы 0...",
    "1": "Текст страницы 1...",
    ...
  }
}
```

---

## Использование

### 1. Быстрый старт

```python
from app.utils.pdf_parser import parse_pdf_to_materials

# Извлечь материалы из одного файла
materials = parse_pdf_to_materials('processed/project/processed.json')

for mat in materials:
    print(f"{mat['type']}: {mat['name']} x {mat['quantity']} {mat['unit']}")
```

### 2. Пакетная обработка

```python
from app.utils.pdf_parser import batch_parse_processed_files

# Обработать все JSON файлы в директории
all_materials = batch_parse_processed_files('processed/')

print(f"Всего материалов: {len(all_materials)}")
```

### 3. Экспорт в JSON

```python
from app.utils.pdf_parser import PDFDataExtractor

extractor = PDFDataExtractor('processed/project/processed.json')
extractor.export_to_json('output/materials.json')
```

---

## API Endpoints

### Импорт из JSON

```bash
POST /api/materials/import-from-json?json_file_path=processed/project/file.json
```

**Ответ:**
```json
[
  {
    "id": 1,
    "type": "cable",
    "name": "ППГнг(А)-HF 3×2,5",
    "mark": "ППГнг(А)-HF 3×2,5",
    "price": 0.0,
    "quantity": 100
  }
]
```

### Пакетный импорт

```bash
POST /api/materials/batch-import?input_dir=processed/
```

### Получить извлечённые материалы

```bash
GET /api/materials/extracted/{doc_id}
```

### Поиск материалов

```bash
GET /api/materials/search?q=ППГнг&type=cable
```

### Получить типы материалов

```bash
GET /api/materials/types
```

**Ответ:**
```json
["cable", "fixture", "device", "general", "pipe", "conduit", "panel"]
```

---

## Типы материалов

| Тип | Описание | Примеры |
|-----|----------|---------|
| `cable` | Кабели и провода | ППГнг, ПРГнг, ПуГПнг |
| `fixture` | Светильники | Светодиодный, ЛБ |
| `device` | Устройства | Розетка, выключатель, датчик |
| `general` | Прочие материалы | Труба, лоток, коробка |

---

## Кастомизация парсера

### Добавление новых паттернов

В файле `app/utils/pdf_parser.py` можно добавить новые методы парсинга:

```python
def _parse_pipe_line(self, line: str, page_num: int, material_type: str) -> Optional[dict]:
    """Парсинг строки с трубой"""
    pipe_pattern = r'(труба\s*[А-Я0-9\-\(\)]+)'
    
    match = re.search(pipe_pattern, line, re.IGNORECASE)
    if match:
        name = match.group(1).strip()
        return {
            'type': 'pipe',
            'name': name,
            'mark': '',
            'quantity': 1.0,
            'unit': 'м',
            'page_number': page_num,
            'raw_text': line
        }
    
    return None
```

### Регистрация нового типа

Добавить в словарь `patterns` в методе `_parse_material_line`:

```python
patterns = {
    'cable': self._parse_cable_line,
    'fixture': self._parse_fixture_line,
    'device': self._parse_device_line,
    'pipe': self._parse_pipe_line,  # Новый тип
    'general': self._parse_general_line
}
```

---

## Интеграция со сметой

### Автоматическое создание элементов сметы

```python
from app import crud
from app.utils.pdf_parser import parse_pdf_to_materials

# Извлечь материалы
materials = parse_pdf_to_materials('processed/project/file.json')

# Создать смету
estimate = crud.Estimates.create(db, {
    'project_id': 1,
    'name': 'Смета из PDF',
    'description': 'Автоматически из спецификации'
})

# Добавить элементы
for mat in materials:
    # Найти или создать материал
    material = crud.Materials.get_by_name_and_mark(
        db, mat['name'], mat.get('mark', '')
    )
    
    if not material:
        material = crud.Materials.create(db, {
            'type': mat['type'],
            'name': mat['name'],
            'mark': mat.get('mark', ''),
            'price': 0.0  # Установить цену
        })
    
    # Добавить в смету
    crud.EstimateItems.create(db, {
        'estimate_id': estimate.id,
        'material_id': material.id,
        'quantity': mat['quantity'],
        'unit_cost': material.price,
        'total_cost': mat['quantity'] * material.price
    })
```

---

## Тестирование

### Запуск парсера из командной строки

```bash
# Один файл
python -m app.utils.pdf_parser processed/project/file.json

# Все файлы
python scripts/test_parser.py
```

### Пример вывода

```
Parsing: processed/03-23-ОГР01.1-ЭОМ1.1-Изм.1_processed.json

Found 150 materials:
  - cable: ППГнг(А)-HF 3×2,5 x 100 шт (стр. 5)
  - cable: ППГнг(А)-HF 3×6 x 50 шт (стр. 5)
  - device: Розетка 16А x 200 шт (стр. 10)
  - fixture: Светильник светодиодный x 80 шт (стр. 15)
  ... и ещё 146
```

---

## Известные ограничения

1. **Качество текста:** Парсер работает только с текстовыми PDF. Для сканов нужен OCR.
2. **Сложные таблицы:** Некоторые таблицы могут парситься некорректно.
3. **Ручная проверка:** Всегда проверяйте извлечённые данные перед использованием.

---

## Будущие улучшения

- [ ] Поддержка OCR для сканов PDF
- [ ] Распознавание таблиц с помощью OpenCV
- [ ] Машинное обучение для классификации материалов
- [ ] Интеграция с внешними базами цен
- [ ] Экспорт в Excel/CSV
- [ ] Веб-интерфейс для ручной коррекции

---

## Поддержка

При возникновении проблем:

1. Проверьте формат JSON файла
2. Убедитесь, что текст извлечён корректно
3. Добавьте новые паттерны для специфичных материалов
4. Создайте issue в репозитории
