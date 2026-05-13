# Поток работы парсера спецификаций

## Обзор

Парсер спецификаций извлекает табличные данные со страниц, классифицированных как `specification`, и экспортирует их в JSON или Excel формат.

## Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI (document_detail.html)                │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │ Кнопка          │  │ Панель           │  │ Кнопки         │ │
│  │ "Спецификации"  │→ │ спецификаций     │→ │ JSON / Excel   │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                            ↓ HTTP fetch
┌─────────────────────────────────────────────────────────────────┐
│                      API (documents.py)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ GET /api/documents/{id}/specification-summary            │   │
│  │ POST /api/documents/{id}/parse-specifications?format=..  │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                  SpecificationParser (specification_parser.py)   │
│                                                                  │
│  1. _get_specification_pages()                                   │
│     → SQL: SELECT FROM document_pages                           │
│        WHERE category='specification'                            │
│        ORDER BY page_number                                      │
│                                                                  │
│  2. _load_processed_json()                                       │
│     → processed/{id}_*_processed.json                            │
│        (текст каждой страницы PDF)                               │
│                                                                  │
│  3. extract_specification_tables()                               │
│     → Для каждой spec_page:                                      │
│        - _parse_page_by_columns()                                │
│        - _find_header_line()                                     │
│        - _detect_columns()                                       │
│        - _parse_data_line()                                      │
│                                                                  │
│  4. export_to_json() / export_to_excel()                         │
│     → output/specifications/{doc_name}_specifications.{json,xlsx}│
└─────────────────────────────────────────────────────────────────┘
```

## Детальный поток

### Шаг 1: Инициализация парсера

```python
with SpecificationParser(document_id, processed_dir='processed') as parser:
    # В __init__:
    self.spec_pages = db.query(DocumentPage).filter(
        document_id == document_id,
        category == 'specification'  # ← Только спецификации!
    ).order_by(page_number).all()
    
    self.processed_data = load_json('processed/{id}_*.json')
```

**Важно:** Парсер берёт **только** страницы с `category='specification'` из БД.

### Шаг 2: Извлечение таблиц

```python
for spec_page in self.spec_pages:
    page_num = spec_page.page_number  # Например, 2
    page_key = str(page_num - 1)      # Индекс в JSON: "1"
    
    page_text = processed_data['text'][page_key]
    
    # Парсинг с определением заголовка на каждой странице
    table = self._parse_page_by_columns(page_text, page_num, spec_page.confidence)
    
    if table and table.get('rows'):
        result[f"page_{page_num}"] = table
```

### Шаг 3: Определение заголовка таблицы

```python
def _find_header_line(self, lines: List[str]) -> Tuple[int, str]:
    for i, line in enumerate(lines):
        if self._is_table_header(line):  # ← Проверка по колонкам
            return i, line
    return -1, ""

def _is_table_header(self, line: str) -> bool:
    detected = {col['key'] for col in self._detect_columns(line)}
    # Должно быть: ≥2 колонок + (name ИЛИ quantity) + (position ИЛИ designation)
    return len(detected) >= 2 and (has_name or has_quantity) and ...
```

**Критично:** Строки типа "СПЕЦИФИКАЦИЯ ОБОРУДОВАНИЯ" **не считаются** заголовком таблицы.

### Шаг 4: Определение колонок

```python
def _detect_columns(self, header_line: str) -> List[Dict]:
    # Ищем паттерны: Позиция, Обозначение, Наименование, Кол-во, ...
    matches = []
    for pattern, key in self._column_header_patterns():
        for match in re.finditer(pattern, header_line, flags=re.IGNORECASE):
            matches.append({
                'key': key,           # technical: 'position', 'name', ...
                'label': match.group(),  # original: 'Позиция', '№ п/п', ...
                'start': match.start(),
                'end': match.end()
            })
    return matches
```

### Шаг 5: Парсинг строк

```python
def _parse_data_line(self, line: str, columns: List[Dict]) -> Optional[Dict]:
    # Fixed-width parsing по позициям из заголовка
    row = self._parse_fixed_width_line(line, columns)
    
    # Сохраняем маппинг по оригинальным заголовкам
    row['cells_by_header'] = {
        col['label']: row.get(col['key'], '')
        for col in columns
    }
    return row
```

### Шаг 6: Экспорт

#### JSON структура:
```json
{
  "document_id": 1,
  "specification_pages_count": 2,
  "tables_found": 2,
  "schema_note": "Для каждой страницы columns содержит реальные заголовки...",
  "specifications": {
    "page_2": {
      "page_number": 2,
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
          "cells_by_header": {
            "Позиция": "1",
            "Обозначение": "Э1.00.00.000",
            "Наименование": "Электродвигатель АИР80А2",
            "Кол-во": "2",
            "Ед.изм.": "шт."
          }
        }
      ],
      "row_count": 1,
      "parse_method": "fixed_width_by_page_header"
    }
  },
  "all_rows_flat": [
    {
      "Позиция": "1",
      "Обозначение": "Э1.00.00.000",
      "Наименование": "Электродвигатель АИР80А2",
      "Кол-во": "2",
      "Ед.изм.": "шт.",
      "page_number": 2,
      "source_page_key": "page_2"
    }
  ],
  "summary": {
    "total_rows": 1,
    "total_tables": 2
  }
}
```

#### Excel структура:
- **Лист "Сводка"**: общая информация о документе
- **Лист "Стр_2"**: данные страницы 2 с заголовками из оригинального заголовка
- **Лист "Стр_3"**: данные страницы 3 со своими заголовками
- **Лист "Все_строки"**: объединённые данные всех страниц

## UI Integration

### 1. Кнопка "Спецификации"
```html
<button class="btn btn-success" onclick="showSpecificationPanel()">Спецификации</button>
```

### 2. Запрос сводки
```javascript
async function showSpecificationPanel() {
    const response = await fetch(`/api/documents/${DOCUMENT_ID}/specification-summary`, {
        headers: { 'X-Session-Key': localStorage.getItem('session_key') }
    });
    const data = await response.json();
    renderSpecificationSummary(data);
}
```

### 3. Отображение страниц со спецификациями
```javascript
function renderSpecificationSummary(data) {
    // data.specification_pages = [
    //   {page_number: 2, confidence: 0.95, content_type: 'table'},
    //   {page_number: 3, confidence: 0.92, content_type: 'table'}
    // ]
    
    data.specification_pages.forEach(page => {
        html += `<span class="badge">Стр. ${page.page_number} (${confidence}%)</span>`;
    });
}
```

### 4. Экспорт
```javascript
async function parseSpecifications(format) {
    const response = await fetch(`/api/documents/${DOCUMENT_ID}/parse-specifications?format=${format}`, {
        method: 'POST',
        headers: { 'X-Session-Key': localStorage.getItem('session_key') }
    });
    const result = await response.json();
    // result.output_path = "output/specifications/..."
}
```

## Сценарии использования

### Сценарий 1: Успешный парсинг
1. Пользователь открывает документ
2. Страницы классифицированы: стр. 2, 3 → `specification`
3. Нажимает "Спецификации" → панель показывает 2 страницы
4. Нажимает "Экспорт в Excel" → файл сохранён в `output/specifications/`

### Сценарий 2: Нет спецификаций
1. Пользователь открывает документ
2. Нет страниц с `category='specification'`
3. Нажимает "Спецификации" → сообщение "Спецификации не найдены"
4. Кнопка "Переклассифицировать"

### Сценарий 3: Ручное исправление категории
1. Пользователь видит, что стр. 5 не распознана как спецификация
2. В режиме "Просмотр всех страниц" выбирает стр. 5
3. Нажимает кнопку "Спецификация" → категория обновлена в БД
4. Повторяет парсинг → стр. 5 включена в экспорт

### Сценарий 4: Processed файл не найден
1. Документ классифицирован, но нет `processed/*.json`
2. API возвращает ошибку 400: "Processed файл не найден"
3. Пользователь запускает `pdf_processor` → создаётся JSON
4. Повторяет парсинг → успешно

## CLI использование

```bash
# Парсинг одного документа
python scripts/parse_specifications.py --document 1 json
python scripts/parse_specifications.py --document 1 excel

# Пакетный парсинг проекта
python scripts/parse_specifications.py --project 5 json
python scripts/parse_specifications.py --project 5 excel
```

## Отладка

```python
from app.utils.specification_parser import SpecificationParser

with SpecificationParser(document_id=1) as parser:
    # Проверка найденных страниц
    print(f"Spec pages: {[p.page_number for p in parser.spec_pages]}")
    
    # Парсинг
    specs = parser.extract_specification_tables()
    
    # Детали по странице
    for page_key, table in specs.items():
        print(f"\n{page_key}:")
        print(f"  Header: {table['header']!r}")
        print(f"  Columns: {[c['label'] for c in table['columns']]}")
        print(f"  Rows: {table['row_count']}")
```

## Ошибки и решения

| Ошибка | Причина | Решение |
|--------|---------|---------|
| "В документе нет страниц, классифицированных как спецификации" | Нет страниц с category='specification' | Переклассифицировать документ или вручную изменить категорию страницы |
| "Processed файл не найден" | Отсутствует `processed/{id}_*_processed.json` | Запустить pdf_processor для документа |
| "Ошибка парсинга спецификаций: openpyxl" | Не установлен модуль openpyxl | `pip install openpyxl` |
| Страница не парсится | Заголовок таблицы не распознан | Проверить текст страницы в processed JSON, возможно PDF отдал текст некорректно |
