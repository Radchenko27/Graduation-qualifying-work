# Универсальный парсер документов

## Обзор

`DocumentParser` — универсальный парсер, который обрабатывает **ВСЁ** документ целиком и создаёт полную структурированную модель в зависимости от категории каждой страницы.

## Чем отличается от specification_parser?

| specification_parser | document_parser |
|---------------------|-----------------|
| Только страницы `category='specification'` | **Все** страницы документа |
| Только таблицы спецификаций | Таблицы + чертежи + схемы + титулы |
| Экспорт: спецификации JSON/Excel | Экспорт: полная структура JSON/Excel |
| Для получения данных о материалах | Для создания полного dataset'а документа |

## Архитектура

```
Документ (10 страниц)
    ↓
Классификатор → БД:
  - стр. 1: title
  - стр. 2-3: specification
  - стр. 4-7: drawing
  - стр. 8: scheme
  - стр. 9-10: other
    ↓
DocumentParser обрабатывает КАЖДУЮ страницу:
  - title       → извлекает метаданные (название, шифр, организация)
  - specification → парсит таблицы (позиция, обозначение, наименование...)
  - drawing     → извлекает обозначение, название, размеры, формат
  - scheme      → находит элементы (Э1, К1, Р1...)
  - other       → сохраняет текст
    ↓
Структурированный JSON/Excel
```

## Структура выходного JSON

```json
{
  "document_id": 1,
  "document_name": "03-23-ОГР01.1-ЭОМ1.1.pdf",
  "project_id": 5,
  "parsed_at": "2025-01-15T10:30:00",
  "source": "processed_json",
  "total_pages": 10,
  "pages": {
    "page_1": {
      "page_number": 1,
      "category": "title",
      "confidence": 0.98,
      "data": {
        "type": "title",
        "document_title": "Рабочая документация",
        "document_code": "03-23-ОГР01.1-ЭОМ1.1",
        "organization": "ООО ПроектМонтаж",
        "date": "15.01.2025",
        "signatures": ["Иванов И.И.", "Петров П.П."],
        "text_preview": "..."
      }
    },
    "page_2": {
      "page_number": 2,
      "category": "specification",
      "confidence": 0.95,
      "data": {
        "type": "specification_table",
        "has_table": true,
        "header": "Позиция  Обозначение  Наименование  Кол-во  Ед.изм.",
        "columns": [
          {"key": "position", "label": "Позиция", "start": 0, "end": 9},
          {"key": "designation", "label": "Обозначение", "start": 9, "end": 22},
          {"key": "name", "label": "Наименование", "start": 22, "end": 46},
          {"key": "quantity", "label": "Кол-во", "start": 46, "end": 54},
          {"key": "unit", "label": "Ед.изм.", "start": 54, "end": null}
        ],
        "rows": [
          {
            "position": "1",
            "designation": "Э1.00.00.000",
            "name": "Электродвигатель АИР80А2",
            "quantity": "2",
            "unit": "шт.",
            "cells_by_header": {...}
          }
        ],
        "row_count": 5
      }
    },
    "page_4": {
      "page_number": 4,
      "category": "drawing",
      "confidence": 0.92,
      "data": {
        "type": "drawing",
        "designation": "АБВГ.123456.001",
        "title": "План расположения оборудования",
        "format_size": "А3",
        "scale": "1:50",
        "dimensions": ["1200×800×600"],
        "text_preview": "..."
      }
    },
    "page_8": {
      "page_number": 8,
      "category": "scheme",
      "confidence": 0.89,
      "data": {
        "type": "scheme",
        "elements_count": 15,
        "elements": [
          {"designation": "Э1", "context": "Электродвигатель М1"},
          {"designation": "К1", "context": "Контактор КМИ-10910"},
          {"designation": "Р1", "context": "Реле РЭК77/3"}
        ],
        "element_types": [
          {"type": "двигатель", "context": "..."},
          {"type": "контактор", "context": "..."}
        ],
        "sheet_references": [2, 3]
      }
    }
  }
}
```

## Структура Excel

Файл содержит несколько листов:

| Лист | Описание |
|------|----------|
| **Сводка** | Статистика по категориям страниц |
| **Спецификации** | Все строки из всех таблиц спецификаций |
| **Чертежи** | Обозначения, названия, форматы чертежей |
| **Элементы_схем** | Все найденные элементы схем (Э1, К1, Р1...) |
| **Титулы** | Метаданные титульных листов |

### Пример: Лист "Сводка"
| document_id | document_name | total_pages | specification_pages | drawing_pages | scheme_pages | title_pages | other_pages |
|-------------|---------------|-------------|---------------------|---------------|--------------|-------------|-------------|
| 1 | 03-23-ОГР01.1.pdf | 10 | 2 | 4 | 1 | 1 | 2 |

### Пример: Лист "Спецификации"
| Страница | Позиция | Обозначение | Наименование | Кол-во | Ед.изм. |
|----------|---------|-------------|--------------|--------|---------|
| 2 | 1 | Э1.00.00.000 | Электродвигатель АИР80А2 | 2 | шт. |
| 2 | 2 | К1.00.00.000 | Контактор КМИ-10910 | 4 | шт. |
| 3 | 3 | Р1.00.00.000 | Реле РЭК77/3 | 10 | шт. |

### Пример: Лист "Чертежи"
| Страница | Обозначение | Название | Формат | Масштаб | Размеры |
|----------|-------------|----------|--------|---------|---------|
| 4 | АБВГ.123456.001 | План расположения оборудования | А3 | 1:50 | 1200×800×600 |
| 5 | АБВГ.123456.002 | Схема электрическая | А2 | 1:20 | |

### Пример: Лист "Элементы_схем"
| Страница | Обозначение | Контекст |
|----------|-------------|----------|
| 8 | Э1 | Электродвигатель М1 (380В, 2.2кВт) |
| 8 | К1 | Контактор КМИ-10910 (230В, 9А) |
| 8 | Р1 | Реле РЭК77/3 (24В DC) |

## API

### 1. Обработать документ и сохранить в файл

```http
POST /api/documents/{id}/parse-full?format=excel
```

**Ответ:**
```json
{
  "status": "success",
  "document_id": 1,
  "document_name": "03-23-ОГР01.1.pdf",
  "format": "excel",
  "output_path": "output/documents/03-23-ОГР01.1_structured.xlsx",
  "message": "Документ успешно обработан и сохранён в EXCEL"
}
```

### 2. Получить структуру без сохранения

```http
GET /api/documents/{id}/structure
```

**Ответ:** Полный JSON документ (см. выше)

## CLI

```bash
# Обработать один документ в JSON
python scripts/parse_document.py --document 1

# Обработать один документ в Excel
python scripts/parse_document.py --document 1 excel

# Пакетная обработка проекта
python scripts/parse_document.py --project 5 excel

# Обработать ВСЕ документы
python scripts/parse_document.py --all json
```

## UI

### Страница документа (`/documents/{id}`)

Две новые кнопки в шапке:
- **"Обработать в JSON"** → `parse-full?format=json`
- **"Обработать в Excel"** → `parse-full?format=excel`

### Список документов (`/documents`)

Новая колонка в таблице:
- **"Обработать в Excel"** → быстрая обработка без открытия страницы

## Парсеры по категориям

### 1. specification (Спецификация)

**Что извлекает:**
- Заголовок таблицы
- Колонки (key, label, start, end)
- Строки данных
- cells_by_header (маппинг по оригинальным названиям)

**Метод:** `SpecificationParser._parse_page_by_columns()`

### 2. drawing (Чертеж)

**Что извлекает:**
- `designation` — обозначение чертежа (АБВГ.123456.001)
- `title` — название чертежа
- `format_size` — формат (А4, А3, А2...)
- `scale` — масштаб (1:50, 1:20...)
- `dimensions` — габаритные размеры (1200×800×600)

**Метод:** regex + поиск паттернов

### 3. scheme (Схема)

**Что извлекает:**
- `elements` — позиционные обозначения (Э1, К1, Р1, QS1...)
- `element_types` — типы элементов (двигатель, контактор, реле...)
- `sheet_references` — ссылки на другие листы

**Метод:** regex `([А-ЯA-Z]{1,3}\d{1,3})`

### 4. title (Титульник)

**Что извлекает:**
- `document_title` — название документа/проекта
- `document_code` — шифр документа
- `organization` — организация
- `date` — дата
- `signatures` — подписи (Иванов И.И.)

**Метод:** поиск по ключевым словам + regex

### 5. other (Прочее)

**Что извлекает:**
- `text_preview` — первые 20 строк
- `line_count` — количество строк
- `char_count` — количество символов

## Использование

### Пример 1: Получить полный dataset документа

```python
from app.utils.document_parser import DocumentParser

with DocumentParser(document_id=1) as parser:
    # Получить структуру
    structure = parser.parse_document()
    
    # Экспорт в JSON
    parser.export_to_json('output/doc_structured.json')
    
    # Экспорт в Excel
    parser.export_to_excel('output/doc_structured.xlsx')
```

### Пример 2: Извлечь только чертежи

```python
from app.utils.document_parser import DocumentParser

with DocumentParser(document_id=1) as parser:
    structure = parser.parse_document()
    
    drawings = []
    for page_key, page_data in structure['pages'].items():
        if page_data['category'] == 'drawing':
            drawings.append(page_data['data'])
    
    print(f"Найдено чертежей: {len(drawings)}")
    for d in drawings:
        print(f"  - {d.get('designation')}: {d.get('title')}")
```

### Пример 3: Извлечь все элементы схем

```python
from app.utils.document_parser import DocumentParser

with DocumentParser(document_id=1) as parser:
    structure = parser.parse_document()
    
    all_elements = []
    for page_data in structure['pages'].values():
        if page_data['category'] == 'scheme':
            elements = page_data['data'].get('elements', [])
            all_elements.extend(elements)
    
    print(f"Всего элементов схем: {len(all_elements)}")
    for el in all_elements:
        print(f"  {el['designation']}: {el['context']}")
```

## Преимущества

1. **Один проход — все данные**: Не нужно запускать несколько парсеров
2. **Структурированный dataset**: Готово для ML/AI анализа
3. **Excel с листами**: Удобно для просмотра человеком
4. **Расширяемость**: Легко добавить новый тип парсера для категории

## Отладка

```python
from app.utils.document_parser import DocumentParser

with DocumentParser(document_id=1) as parser:
    # Проверка страниц
    print(f"Всего страниц: {len(parser.all_pages)}")
    for page in parser.all_pages:
        print(f"  Стр. {page.page_number}: {page.category}")
    
    # Парсинг
    structure = parser.parse_document()
    
    # Статистика
    categories = {}
    for p in structure['pages'].values():
        cat = p['category']
        categories[cat] = categories.get(cat, 0) + 1
    
    print(f"\nКатегории: {categories}")
```

## Зависимости

- `pandas` — для DataFrame
- `openpyxl` — для Excel
- `fitz` (PyMuPDF) — fallback чтение PDF
- `sqlalchemy` — работа с БД

## См. также

- `docs/SPECIFICATION_PARSER_WORKFLOW.md` — детально о парсинге спецификаций
- `app/utils/specification_parser.py` — парсер только спецификаций
- `scripts/parse_specifications.py` — CLI для спецификаций
