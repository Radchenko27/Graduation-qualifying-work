# Резюме: Парсер спецификаций из классифицированных документов

## Что было создано

### 1. Основной модуль: `app/utils/specification_parser.py`

Класс `SpecificationParser` для извлечения спецификаций из документов после классификации страниц.

**Основные возможности:**
- Автоматический поиск страниц с категорией `specification`
- Парсинг таблиц спецификаций (позиции, обозначения, наименования, количества)
- Экспорт в JSON формат
- Экспорт в Excel формат (несколько листов)
- Получение сводной информации о спецификациях

**Ключевые методы:**
- `extract_specification_tables()` — извлечение таблиц
- `export_to_json(path)` — экспорт в JSON
- `export_to_excel(path)` — экспорт в Excel
- `get_summary()` — сводная информация

### 2. Скрипт командной строки: `scripts/parse_specifications.py`

Удобный интерфейс для парсинга из терминала:

```bash
# Парсинг одного документа
python scripts/parse_specifications.py --document 1 json
python scripts/parse_specifications.py --document 1 excel

# Пакетная обработка проекта
python scripts/parse_specifications.py --project 1 json

# Просмотр списка документов
python scripts/parse_specifications.py --list

# Просмотр страниц со спецификациями
python scripts/parse_specifications.py --list-pages 1
```

### 3. Тесты: `tests/test_specification_parser.py`

Полный набор тестов для проверки функциональности:
- Тест инициализации
- Тест парсинга заголовков
- Тест парсинга строк
- Тест экспорта в JSON/Excel
- Тест пакетной обработки

### 4. Документация: `docs/SPECIFICATION_PARSER_GUIDE.md`

Полное руководство по использованию с примерами.

### 5. Примеры: `examples/specification_parser_example.py`

4 примера использования:
- Парсинг одного документа
- Детальный парсинг и анализ
- Пакетная обработка проекта
- Кастомная обработка спецификаций

## Установка зависимостей

Перед использованием необходимо установить pandas и openpyxl:

```bash
pip install pandas openpyxl
```

Или обновить requirements.txt:

```bash
pip install -r requirements.txt
```

## Как это работает

```
1. Документ загружается в систему (PDF → MinIO)
   ↓
2. PDF обрабатывается (pdf_processor)
   → Текст извлекается постранично
   → Сохраняется в processed/*.json
   ↓
3. Страницы классифицируются (document_classifier_v2)
   → Определяется категория каждой страницы
   → Сохраняется в document_pages таблицу
   ↓
4. Парсятся спецификации (specification_parser)
   → Выбираются страницы с category='specification'
   → Извлекаются таблицы спецификаций
   → Экспортируются в JSON или Excel
```

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
      "rows": [...],
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
1. **Сводка** — общая информация
2. **Спецификация_стрN** — каждая таблица на отдельном листе
3. **Все_спецификации** — объединённая таблица

## Примеры использования

### Программно

```python
from app.utils.specification_parser import parse_document_specifications

# Экспорт в JSON
json_path = parse_document_specifications(
    document_id=1,
    output_format='json',
    output_dir='output/specifications'
)

# Экспорт в Excel
excel_path = parse_document_specifications(
    document_id=1,
    output_format='excel',
    output_dir='output/specifications'
)
```

### С использованием класса

```python
from app.utils.specification_parser import SpecificationParser

with SpecificationParser(document_id=1) as parser:
    # Сводная информация
    summary = parser.get_summary()
    
    # Извлечение спецификаций
    specs = parser.extract_specification_tables()
    
    # Экспорт
    parser.export_to_json('output/spec.json')
    parser.export_to_excel('output/spec.xlsx')
```

## Требования

Для работы модуля необходимы:

1. ✅ **Классифицированные страницы** — документ должен быть обработан через `document_classifier_v2`
2. ✅ **Processed JSON файл** — должен существовать файл в `processed/` с извлечённым текстом
3. ✅ **База данных** — должна быть доступна таблица `document_pages` с категориями

Проверка классификации:

```sql
SELECT document_id, page_number, category, confidence
FROM document_pages
WHERE document_id = 1 AND category = 'specification'
ORDER BY page_number;
```

## Интеграция с API

Можно добавить endpoint:

```python
@router.post("/documents/{document_id}/parse-specifications")
def parse_specifications(
    document_id: int,
    format: str = "json",
    db: Session = Depends(get_db)
):
    output_path = parse_document_specifications(
        document_id=document_id,
        output_format=format
    )
    return {"status": "success", "output_path": output_path}
```

## Файлы проекта

```
app/utils/
├── __init__.py (обновлён)
└── specification_parser.py (новый)

scripts/
└── parse_specifications.py (новый)

tests/
└── test_specification_parser.py (новый)

docs/
└── SPECIFICATION_PARSER_GUIDE.md (новый)

examples/
└── specification_parser_example.py (новый)

requirements.txt (обновлён)
```

## Следующие шаги

1. Установить зависимости:
   ```bash
   pip install pandas openpyxl
   ```

2. Проверить классификацию документов:
   ```bash
   python scripts/parse_specifications.py --list
   ```

3. Протестировать на реальном документе:
   ```bash
   python scripts/parse_specifications.py --document 1 excel
   ```

4. Запустить тесты:
   ```bash
   pytest tests/test_specification_parser.py -v
   ```

## Возможные улучшения

- [ ] Поддержка пользовательских паттернов заголовков
- [ ] Распознавание сложных многоуровневых таблиц
- [ ] Автоматическое определение единиц измерения
- [ ] Валидация данных спецификаций
- [ ] Импорт отредактированных спецификаций обратно в БД
- [ ] Сравнение версий спецификаций

---

**Дата создания:** 2025-01-15
**Версия:** 1.0