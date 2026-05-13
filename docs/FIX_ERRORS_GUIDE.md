# 🔧 Руководство по исправлению ошибок

## Ошибка 1: No module named 'openpyxl'

**Причина:** Модуль `openpyxl` не установлен (необходим для экспорта в Excel).

**Решение:**

```bash
pip install openpyxl
```

**Проверка:**

```bash
python -c "import openpyxl; print(openpyxl.__version__)"
```

Если выводит версию (например `3.1.5`) — всё работает.

---

## Ошибка 2: Expecting value: line X column Y — повреждённый JSON

**Причина:** Файл `processed/..._processed.json` повреждён или неполный.

**Решение 1: Исправление через скрипт**

```bash
# Исправить конкретный файл
python scripts/fix_processed_json.py "processed/название_файла_processed.json"

# Или проверить все файлы
python scripts/fix_processed_json.py
```

**Решение 2: Переобработка документа**

```bash
# Переобработать PDF
python -m app.services.pdf_processor "documents/1/файл.pdf" processed/
```

**Решение 3: Удалить и загрузить документ заново**

1. Удалите документ из интерфейса
2. Загрузите PDF заново (с включённой автоматической классификацией)

---

## Ошибка 3: RequestTimeTooSkewed (MinIO)

**Причина:** Разница во времени между компьютером и сервером MinIO.

**Решение:**

```powershell
# Windows — синхронизация времени
w32tm /resync

# Перезапуск Docker
docker-compose down
docker-compose up -d

# Запуск приложения
python -m uvicorn app.main:app --reload
```

---

## Быстрый чеклист

```bash
# 1. Установка зависимостей
pip install pandas openpyxl

# 2. Проверка JSON файлов
python scripts/fix_processed_json.py

# 3. Синхронизация времени (Windows)
w32tm /resync

# 4. Перезапуск Docker
docker-compose restart

# 5. Запуск приложения
python -m uvicorn app.main:app --reload
```

---

## Проверка после исправлений

1. Откройте документ в интерфейсе
2. Нажмите **📋 Спецификации**
3. Попробуйте экспорт в **JSON** и **Excel**

Если всё работает — отобразится панель с информацией о спецификациях и кнопками экспорта.

---

## Если ничего не помогает

1. Очистите папку `processed/` (кроме нужных файлов)
2. Удалите и заново загрузите документы
3. Убедитесь, что Docker контейнеры запущены:
   ```bash
   docker ps
   ```
4. Проверьте логи MinIO:
   ```bash
   docker logs minio_storage
   ```

---

**Дата:** 2025-01-15