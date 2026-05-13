# Руководство по парсингу спецификаций

## Обзор

Модуль `specification_parser` позволяет извлекать спецификации из документов после классификации страниц. Страницы, классифицированные как "Спецификация", преобразуются в редактируемые форматы (JSON или Excel).

---

## Как это работает

```
┌─────────────────────────────────────────────────────────────┐
│                    1. Загрузка документа                    │
│                      (PDF в MinIO)                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              2. Обработка PDF (pdf_processor)               │
│              → Извлечение текста постранично                 │
│              → Сохранение в processed/*.json                │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│            3. Классификация страниц                         │
│            (document_classifier_v2)                         │
│              → Определение категории каждой страницы        │
│              → Сохранение в document_pages таблицу          │
│         Категории: drawing, specification, scheme, etc.     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│           4. Парсинг спецификаций (specification_parser)    │
│              → Выбор страниц с category='specification'     │
│              → Извлечение таблиц спецификаций               │
│              → Экспорт в JSON или Excel                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Установка зависимостей

```bash
pip install pandas openpyxl
```

Или обновите requirements.txt:

```bash
pip install -r requirements.txt
```

---

## Использование

### 1. Из командной строки

#### Парсинг одного документа

```bash
# Экспорт в JSON
python scripts/parse_specifications.py --document 1 json

# Экспорт в Excel
python scripts/parse_specifications.py --document 1 excel

# С указанием выходной директории
python scripts/parse_specifications.py --document 1 json output/my_specs
```

#### Пакетный парсинг всех документов проекта

```bash
# Все документы проекта в JSON
python scripts/parse_specifications.py --project 1 json

# Все документы проекта в Excel
python scripts/parse_specifications.py --project 1 excel
```

#### Просмотр списка документов

```bash
python scripts/parse_specifications.py --list
```

#### Просмотр страниц со спецификациями

```bash
python scripts/parse_specifications.py --list-pages 1
```

---

### 2. Программно (Python)

#### Парсинг одного документа

```python
from app.utils.specification_parser import parse_document_specifications

# Экспорт в JSON
json_path = parse_document_specifications(
    document_id=1,
    output_format='json',
    output_dir='output/specifications'
)
print(f"Сохранено: {json_path}")

# Экспорт в Excel
excel_path = parse_document_specifications(
    document_id=1,
    output_format='excel',
    output_dir='output/specifications'
)
print(f"Сохранено: {excel_path}")
```

#### Использование класса SpecificationParser

```python
from app.utils.specification_parser import SpecificationParser

with SpecificationParser(document_id=1, processed_dir='processed') as parser:
    # Получить сводную информацию
    summary = parser.get_summary()
    print(f"Документ: {summary['document_name']}")
    print(f"Страниц со спецификациями: {summary['specification_pages_count']}")
    
    # Извлечь спецификации
    specs = parser.extract_specification_tables()
    for spec in specs:
        print(f"Страница {spec['page_number']}: {spec['row_count']} строк")
    
    # Экспорт в JSON
    json_path = parser.export_to_json('output/spec.json')
    
    # Экспорт в Excel
    excel_path = parser.export_to_excel('output/spec.xlsx')
```

#### Пакетный парсинг

```python
from app.utils.specification_parser import batch_parse_specifications

# Все документы проекта
output_files = batch_parse_specifications(
    project_id=1,
    output_format='excel',
    output_dir='output/specifications'
)

for f in output_files:
    print(f"Создан: {f}")
```

---

## Структура выходных файлов

### JSON формат

```json
{
  "document_id": 1,
  "document_name": "Спецификация.pdf",
  "project_id": 1,
  "exported_at": "2025-01-15T10:30:00",
  "specification_pages": 3,
  "specifications": [
    {
      "page_number": 2,
      "confidence": 0.85,
      "header": "Спецификация оборудования",
      "columns": ["position", "designation", "name", "quantity", "unit", "note"],
      "rows": [
        {
          "position": "1",
          "designation": "АБВГ.001",
          "name": "Кабель ВВГнг 3x2.5",
          "quantity": 100.0,
          "unit": "м",
          "note": "Для освещения"
        },
        {
          "position": "2",
          "designation": "АБВГ.002",
          "name": "Розетка 16А",
          "quantity": 50.0,
          "unit": "шт",
          "note": "С заземлением"
        }
      ],
      "row_count": 2
    }
  ],
  "summary": {
    "total_tables": 3,
    "total_rows": 15
  }
}
```

### Excel формат

Excel файл содержит несколько листов:

1. **Сводка** — общая информация о документе
2. **Спецификация_стрN** — каждая таблица спецификации на отдельном листе
3. **Все_спецификации** — объединённая таблица всех спецификаций

Пример структуры листа "Все_спецификации":

| position | designation | name | quantity | unit | note | page_number |
|----------|-------------|------|----------|------|------|-------------|
| 1 | АБВГ.001 | Кабель ВВГнг 3x2.5 | 100.0 | м | Для освещения | 2 |
| 2 | АБВГ.002 | Розетка 16А | 50.0 | шт | С заземлением | 2 |
| 3 | - | Лампа LED 10W | 200.0 | шт | - | 3 |

---

## API

### SpecificationParser

```python
class SpecificationParser:
    def __init__(self, document_id: int, processed_dir: str = "processed")
    
    def extract_specification_tables(self) -> List[Dict]
    def export_to_json(self, output_path: str) -> str
    def export_to_excel(self, output_path: str) -> str
    def get_summary(self) -> Dict
    def close(self)
```

### Функции-обёртки

```python
def parse_document_specifications(
    document_id: int,
    output_format: str = 'json',
    output_dir: str = 'output/specifications',
    processed_dir: str = 'processed'
) -> str

def batch_parse_specifications(
    project_id: Optional[int] = None,
    output_format: str = 'json',
    output_dir: str = 'output/specifications',
    processed_dir: str = 'processed'
) -> List[str]
```

---

## Требования

Для работы модуля необходимы:

1. **Классифицированные страницы** — документ должен быть обработан через `document_classifier_v2`, и страницы должны иметь категорию `specification`
2. **Processed JSON файл** — должен существовать файл в директории `processed/` с извлечённым текстом
3. **База данных** — должна быть доступна БД с таблицей `document_pages`

Проверка:

```sql
-- Проверить классификацию страниц
SELECT document_id, page_number, category, confidence
FROM document_pages
WHERE document_id = 1 AND category = 'specification'
ORDER BY page_number;
```

---

## Интеграция с API

### Добавить endpoint для парсинга спецификаций

```python
# app/routers/api/specifications.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.utils.specification_parser import parse_document_specifications
from app import models

router = APIRouter()

@router.post("/documents/{document_id}/parse-specifications")
def parse_specifications(
    document_id: int,
    format: str = "json",
    db: Session = Depends(get_db)
):
    """Парсинг спецификаций документа"""
    
    # Проверяем существование документа
    document = db.query(models.Document).filter(
        models.Document.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    try:
        output_path = parse_document_specifications(
            document_id=document_id,
            output_format=format,
            output_dir='output/specifications'
        )
        
        return {
            "status": "success",
            "document_id": document_id,
            "format": format,
            "output_path": output_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Примеры использования

### Пример 1: Парсинг спецификаций проекта

```bash
# 1. Посмотреть список документов проекта
python scripts/parse_specifications.py --list

# 2. Проверить страницы со спецификациями
python scripts/parse_specifications.py --list-pages 1

# 3. Экспортировать спецификации в Excel
python scripts/parse_specifications.py --document 1 excel

# 4. Открыть файл и отредактировать
start output\specifications\Спецификация_specifications.xlsx
```

### Пример 2: Пакетная обработка

```python
from app.utils.specification_parser import batch_parse_specifications

# Обработать все документы проекта
files = batch_parse_specifications(
    project_id=1,
    output_format='excel',
    output_dir='output/project_1_specs'
)

print(f"Создано {len(files)} файлов спецификаций")
```

### Пример 3: Анализ спецификаций

```python
from app.utils.specification_parser import SpecificationParser

with SpecificationParser(document_id=1) as parser:
    specs = parser.extract_specification_tables()
    
    # Подсчёт общего количества материалов
    total_quantity = 0
    for spec in specs:
        for row in spec['rows']:
            if 'quantity' in row:
                try:
                    total_quantity += float(row['quantity'])
                except:
                    pass
    
    print(f"Общее количество материалов: {total_quantity}")
```

---

## Устранение проблем

### Проблема: "Processed JSON файл не найден"

**Решение:**
```bash
# Проверить наличие processed файла
ls processed/*_processed.json

# Если файла нет, обработать документ через pdf_processor
python -m app.services.pdf_processor documents/1/file.pdf processed/output/
```

### Проблема: "Страниц со спецификациями не найдено"

**Решение:**
```sql
-- Проверить классификацию страниц
SELECT document_id, page_number, category, confidence
FROM document_pages
WHERE document_id = 1;

-- Если категория не specification, переклассифицировать
PUT /api/documents/1/classify
```

### Проблема: "Таблицы не распознаются"

**Решение:**
Проверьте текст страницы. Парсер ищет ключевые слова в заголовке:
- "спецификация"
- "ведомость"
- "перечень"
- "позиция", "наименование", "кол-во"

Если заголовок отличается, добавьте паттерны в метод `_parse_specification_page`.

---

## Тестирование

```bash
# Запустить тесты
pytest tests/test_specification_parser.py -v

# С покрытием
pytest tests/test_specification_parser.py --cov=app.utils.specification_parser
```

---

## Будущие улучшения

- [ ] Поддержка пользовательских паттернов заголовков
- [ ] Распознавание сложных многоуровневых таблиц
- [ ] Автоматическое определение единиц измерения
- [ ] Валидация данных спецификаций
- [ ] Импорт отредактированных спецификаций обратно в БД
- [ ] Сравнение версий спецификаций
- [ ] Поддержка OCR для сканированных документов

---

## Поддержка

При возникновении проблем:

1. Проверьте, что документ классифицирован
2. Убедитесь, что processed JSON файл существует
3. Посмотрите логи для детальной информации об ошибках
4. Создайте issue в репозитории с примером данных