# 🚀 Парсер спецификаций — Быстрый старт

## Что это?

Модуль для автоматического извлечения спецификаций из PDF документов после классификации страниц.

Преобразует страницы с категорией **"Спецификация"** в редактируемые **JSON** или **Excel** файлы.

## ⚡ Быстрый старт

### 1. Установка зависимостей

```bash
pip install pandas openpyxl
```

### 2. Проверка документов

```bash
# Посмотреть список документов
python scripts/parse_specifications.py --list

# Проверить страницы со спецификациями
python scripts/parse_specifications.py --list-pages 1
```

### 3. Парсинг спецификаций

```bash
# Один документ в JSON
python scripts/parse_specifications.py --document 1 json

# Один документ в Excel
python scripts/parse_specifications.py --document 1 excel

# Все документы проекта
python scripts/parse_specifications.py --project 1 excel
```

## 💻 Использование в коде

```python
from app.utils.specification_parser import parse_document_specifications

# Экспорт в Excel
excel_path = parse_document_specifications(
    document_id=1,
    output_format='excel',
    output_dir='output/specifications'
)
print(f"Сохранено: {excel_path}")
```

## 📁 Выходные файлы

### JSON
```json
{
  "document_id": 1,
  "document_name": "Спецификация.pdf",
  "specifications": [
    {
      "page_number": 2,
      "rows": [
        {"position": "1", "name": "Кабель ВВГнг", "quantity": 100, "unit": "м"}
      ]
    }
  ]
}
```

### Excel
- Лист **Сводка** — общая информация
- Лист **Спецификация_стрN** — каждая таблица
- Лист **Все_спецификации** — объединённая таблица

## 📋 Требования

- ✅ Документ классифицирован (есть страницы с `category='specification'`)
- ✅ Существует `processed/*.json` файл
- ✅ База данных доступна

## 🔧 Примеры

Запуск примеров:

```bash
python examples/specification_parser_example.py
```

Доступные примеры:
1. Парсинг одного документа
2. Детальный парсинг и анализ
3. Пакетная обработка проекта
4. Кастомная обработка спецификаций

## 📚 Документация

Полное руководство: [docs/SPECIFICATION_PARSER_GUIDE.md](docs/SPECIFICATION_PARSER_GUIDE.md)

## 🧪 Тесты

```bash
pytest tests/test_specification_parser.py -v
```

## ❓ Устранение проблем

### "Processed JSON файл не найден"
```bash
# Проверить наличие файлов
ls processed/*_processed.json
```

### "Страниц со спецификациями не найдено"
```sql
-- Проверить классификацию
SELECT document_id, page_number, category, confidence
FROM document_pages
WHERE document_id = 1 AND category = 'specification';
```

---

**Подробная информация:** [SPECIFICATION_PARSER_SUMMARY.md](SPECIFICATION_PARSER_SUMMARY.md)