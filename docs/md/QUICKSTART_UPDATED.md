# 🚀 Быстрый старт (Windows)

## Требования

- **Docker Desktop** версии 20.10+ (с включённым Docker Compose)
- **Python** 3.12+
- **PowerShell** или **Command Prompt (cmd)**

> 💡 **Архитектура:** PostgreSQL и MinIO в Docker контейнерах, FastAPI с фронтендом локально

> ⚠️ **Важно:** По умолчанию для локальной разработки используется **SQLite**. PostgreSQL в Docker нужен только для production-тестирования.

---

## 📋 Пошаговая инструкция по запуску

### Шаг 1: Подготовка окружения

Откройте **PowerShell** в папке проекта:

```powershell
# Перейти в папку проекта
cd C:\Users\dimar\Desktop\BMSTU_IU5\Graduation-qualifying-work

# Активировать виртуальное окружение (если используется)
.\venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Выбор базы данных

Приложение поддерживает **две базы данных**:

#### **Вариант А: SQLite (рекомендуется для разработки)**

**Преимущества:**
- Не требует Docker
- Быстрее старт
- Проще отладка
- Файловая БД (можно открыть в DB Browser)

**Настройка:**
```powershell
# .env файл уже настроен по умолчанию
# DATABASE_URL=sqlite:///./data/app.db
```

**Применить миграции:**
```powershell
alembic upgrade head
```

#### **Вариант Б: PostgreSQL (для production-тестирования)**

**Преимущества:**
- Полная совместимость с production
- Расширенные функции SQL
- Тестирование в реальной среде

**Настройка:**
```powershell
# Запустить PostgreSQL в Docker
.\scripts\start_infra.ps1

# В файле .env раскомментировать PostgreSQL и закомментировать SQLite
# DATABASE_URL=postgresql://postgres:postgres_password@localhost:5432/construction_docs
```

**Применить миграции:**
```powershell
alembic upgrade head
```

> 💡 **Почему SQLite по умолчанию?**
> 1. Быстрый старт без Docker
> 2. Проще отладка (файловая БД)
> 3. Миграции работают стабильнее (batch mode для SQLite)
> 4. PostgreSQL нужен только для тестирования production-окружения
> 5. SQLite идеально подходит для локальной разработки и тестирования API

### Шаг 3: Применение миграций

**Для SQLite:**
```powershell
# Удалить старую базу (если есть)
if (Test-Path "data\app.db") { Remove-Item -Path "data\app.db" -Force }

# Применить миграции
alembic upgrade head

# Проверить статус
alembic current
# Ожидаемый результат: 8d7f7b060f5e (head)
```

**Для PostgreSQL:**
```powershell
# Запустить PostgreSQL
.\scripts\start_infra.ps1

# Применить миграции
alembic upgrade head

# Проверить статус
alembic current
```

> ⚠️ **Проблема с миграциями:** Если ошибка `table projects has no column named owner_id`
> 1. Удали старую БД: `Remove-Item -Path "data\app.db" -Force`
> 2. Переустанови миграции: `alembic upgrade head`
> 3. Убедись, что `alembic/env.py` содержит `render_as_batch=True`

### Шаг 4: Запуск FastAPI с фронтендом

**В новом окне PowerShell:**

```powershell
# Запуск с автоперезагрузкой (для разработки)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или без автоперезагрузки (для production)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## ⚡ Быстрый запуск (все команды вместе)

### Для SQLite (локальная разработка):

```powershell
# 1. Применить миграции
alembic upgrade head

# 2. Запустить FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Для PostgreSQL (production-тестирование):

```powershell
# 1. Запустить инфраструктуру
.\scripts\start_infra.ps1

# 2. Применить миграции
alembic upgrade head

# 3. В новом окне запустить FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Доступ к сервисам

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| **Веб-интерфейс** | http://localhost:8000 | - |
| **API Swagger** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin_password |
| **PostgreSQL** | localhost:5432 | postgres / postgres_password |

---

## 📌 Управление миграциями

### Проверить статус миграций

```powershell
# Текущая версия
alembic current

# История миграций
alembic history

# Все доступные миграции
alembic heads
```

### Откат миграций

```powershell
# Откатить одну миграцию
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade 001_initial

# Откатить до начала (удалить все таблицы)
alembic downgrade base
```

### Создать новую миграцию

```powershell
# После изменений в моделях (app/models.py)
alembic revision --autogenerate -m "Описание изменений"

# Применить
alembic upgrade head
```

---

## Локальный запуск (без Docker)

```powershell
# Установка зависимостей
pip install -r requirements.txt

# Применение миграций (SQLite по умолчанию)
alembic upgrade head

# Запуск приложения
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Запуск тестов

```powershell
# Установка pytest (если ещё не установлен)
pip install pytest pytest-cov

# Запуск всех тестов
pytest

# Запуск с покрытием
pytest --cov=app

# Запуск конкретных тестов
pytest tests/test_api.py::TestUsersAPI -v
```

---

## Управление сервисами

### Остановка инфраструктуры

```powershell
# Остановить PostgreSQL и MinIO
.\scripts\stop_infra.ps1

# Или вручную
docker-compose stop db minio
```

### Перезапуск

```powershell
# Остановить
docker-compose stop db minio

# Запустить заново
.\scripts\start_infra.ps1
```

### Просмотр логов

```powershell
# Логи PostgreSQL
docker-compose logs -f db

# Логи MinIO
docker-compose logs -f minio

# Логи FastAPI (в процессе запуска uvicorn)
```

---

## Тестовые пользователи

После инициализации базы данных будут созданы тестовые пользователи:

| Username | Password |
|----------|----------|
| ivan.petrov | password123 |
| maria.sidorova | password123 |
| alexey.kozlov | password123 |

---

## Устранение проблем

### Конфликт портов

Если порт 5432 или 9000 занят:

```powershell
# Проверить, кто использует порт
netstat -ano | findstr :5432
netstat -ano | findstr :9000

# Остановить конфликтующие процессы
Stop-Process -Id <PID> -Force
```

### PostgreSQL не подключается

```powershell
# Проверить статус контейнера
docker-compose ps db

# Перезапустить
docker-compose restart db

# Проверить логи
docker-compose logs db
```

### MinIO недоступен

```powershell
# Проверить статус
docker-compose ps minio

# Перезапустить
docker-compose restart minio

# Открыть консоль MinIO
Start-Process http://localhost:9001
```

### База данных не инициализируется

```powershell
# Применить миграции вручную
alembic upgrade head

# Проверить статус миграций
alembic current

# Инициализировать тестовые данные
python scripts/init_db.py
```

### Ошибка: "table projects has no column named owner_id"

```powershell
# 1. Удалить старую базу данных
Remove-Item -Path "data\app.db" -Force

# 2. Применить миграции заново
alembic upgrade head

# 3. Проверить статус
alembic current
# Ожидаемый результат: 8d7f7b060f5e (head)
```

### Ошибка: "Multiple head revisions are present"

```powershell
# Удалить старую базу
Remove-Item -Path "data\app.db" -Force

# Применить миграции
alembic upgrade head
```

---

## Полезные команды Docker

```powershell
# Статус всех контейнеров
docker-compose ps

# Список всех контейнеров (включая остановленные)
docker ps -a

# Остановить все контейнеры
docker-compose stop

# Удалить все контейнеры и данные (ОСТОРОЖНО!)
docker-compose down -v
```

---

## Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Jinja2 Templates](https://jinja.palletsprojects.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Docker Documentation](https://docs.docker.com/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)

---

## Дополнительные документы

- [FRONTEND_README.md](FRONTEND_README.md) — Подробно о фронтенде и тестах
- [DEPLOYMENT.md](DEPLOYMENT.md) — Развёртывание в production
- [MINIO_SETUP.md](MINIO_SETUP.md) — Настройка MinIO
- [DOCUMENTATION_WORKFLOW.md](../DOCUMENTATION_WORKFLOW.md) — Жизненный цикл документов
- [PROCESSING_ALGORITHMS.md](../PROCESSING_ALGORITHMS.md) — Алгоритмы обработки
- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) — Схема базы данных
- [TECHNOLOGY_SELECTION.md](../TECHNOLOGY_SELECTION.md) — Выбор технологий
