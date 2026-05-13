# 🔧 Исправление ошибки: Processed JSON файл не найден

## Проблема

Ошибка при парсинге спецификаций:
```
[ERROR] Processed JSON файл для документа 24 не найден
HTTP 400 Bad Request
```

## Причина

Для документа 24 не найден обработанный JSON файл в директории `processed/`. Это происходит когда:
1. PDF файл ещё не был обработан через `pdf_processor`
2. Обработка не завершилась успешно
3. Файл был удалён или перемещён

## Решение

### Вариант 1: Переобработка PDF (рекомендуется)

```bash
python scripts/reprocess_document.py 24
```

Этот скрипт:
1. Находит PDF файл документа 24 в базе данных
2. Запускает обработку через `pdf_processor`
3. Сохраняет processed JSON в `processed/{id}_{name}/`

### Вариант 2: Создание заглушки (для тестирования)

```bash
python scripts/create_dummy_processed.py 24 14
```

Создаёт заглушку processed файла с 14 страницами для тестирования парсера спецификаций.

### Вариант 3: Ручная обработка PDF

Если PDF файл находится в MinIO или локально:

```bash
# Обработать PDF и сохранить в processed/
python -m app.services.pdf_processor "путь/к/файлу.pdf" processed/
```

## Проверка результата

После выполнения одного из скриптов проверьте:

```bash
# Показать все processed файлы
python -c "
from pathlib import Path
for f in Path('processed').rglob('*_processed.json'):
    print(f)
"
```

Затем попробуйте снова экспортировать спецификации:
- Через интерфейс: кнопка **📋 Спецификации**
- Через API: `POST /api/documents/24/parse-specifications?format=excel`

## Диагностика

### Проверка статуса документа

```bash
python scripts/check_document_status.py 24
```

Покажет:
- Классифицированы ли страницы
- Найден ли processed файл
- Есть ли страницы со спецификациями

### Проверка наличия страниц со спецификациями

Документ должен иметь страницы с категорией `specification`:

```python
from app.db import SessionLocal
from app import models

db = SessionLocal()
spec_pages = db.query(models.DocumentPage).filter(
    models.DocumentPage.document_id == 24,
    models.DocumentPage.category == 'specification'
).all()

print(f"Страниц со спецификациями: {len(spec_pages)}")
db.close()
```

Если страниц нет (0), нужно переклассифицировать документ через интерфейс.

## Улучшения в коде

Для упрощения поиска processed файлов добавлена улучшенная логика в `specification_parser.py`:

1. **Поиск по ID документа** в имени файла или папки
2. **Поиск по части имени** документа
3. **Логирование** всех найденных candidate файлов
4. **Более подробные сообщения** об ошибках

## Полный чеклист исправления

```bash
# 1. Проверить статус документа
python scripts/check_document_status.py 24

# 2. Переобработать PDF
python scripts/reprocess_document.py 24

# 3. Или создать заглушку для теста
python scripts/create_dummy_processed.py 24 14

# 4. Проверить результат
python scripts/check_document_status.py 24

# 5. Экспортировать спецификации
python scripts/parse_specifications.py --document 24 excel
```

## Если ничего не помогает

1. **Проверьте путь к PDF файлу** в базе данных
2. **Проверьте права доступа** к файлу
3. **Перезагрузите документ** через интерфейс
4. **Проверьте логи pdf_processor** на ошибки

---

**Дата:** 2025-01-15
**Версия:** 1.0