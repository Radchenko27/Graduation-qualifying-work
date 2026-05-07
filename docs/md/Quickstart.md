# 🚀 Быстрый старт (Windows)

## Требования

- **Docker Desktop** версии 20.10+ (с включённым Docker Compose)
- **Python** 3.12+
- **PowerShell** или **Command Prompt (cmd)**

> 💡 **Архитектура:** PostgreSQL и MinIO в Docker контейнерах, FastAPI с фронтендом локально

---

## 📋 Пошаговая инструкция

### Шаг 1: Подготовка окружения

```powershell
# Перейти в папку проекта
cd C:\Users\dimar\Desktop\BMSTU_IU5\Graduation-qualifying-work

# Активировать виртуальное окружение
.\venv\Scripts\Activate.ps1

# Установить зависимости
pip install -r requirements.txt
```

### Шаг 2: Запуск инфраструктуры (PostgreSQL + MinIO)

```powershell
# Запустить PostgreSQL и MinIO
.\scripts\start_infra.ps1

# Проверить статус контейнеров
docker-compose ps
# Ожидаем: STATUS = Up для db и minio
```

### Шаг 3: Применение миграций БД

**⚠️ Важно: Всегда применяй миграции после клонирования проекта или изменений в моделях!**

```powershell
# 1. Проверить текущую версию миграции
alembic current
# Ожидаемо: 002_tz_features (head)

# 2. Применить все миграции
alembic upgrade head

# 3. Проверить историю миграций
alembic history
# Ожидаемо: 2 миграции
```

**Если ошибка "table projects has no column named owner_id":**

```powershell
# Пересоздать базу:
docker-compose down -v
.\scripts\start_infra.ps1
alembic upgrade head
```

### Шаг 4: Запуск FastAPI

**В новом окне PowerShell:**

```powershell
# Запуск с автоперезагрузкой (для разработки)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или без автоперезагрузки (для production)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## ⚡ Быстрый запуск (все команды)

```powershell
# 1. Запустить инфраструктуру
.\scripts\start_infra.ps1

# 2. Применить миграции
alembic upgrade head

# 3. В новом окне запустить FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🌐 Доступ к сервисам

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| **Веб-интерфейс** | http://localhost:8000 | - |
| **API Swagger** | http://localhost:8000/docs | - |
| **MinIO Console** | http://localhost:9001 | minioadmin / minioadmin_password |
| **PostgreSQL** | localhost:5432 | postgres / postgres_password |

---

## 🔧 Управление миграциями

### Проверить статус

```powershell
# Текущая версия
alembic current

# История миграций
alembic history

# Все доступные версии
alembic heads
```

### Применить миграции

```powershell
# Применить все миграции до head
alembic upgrade head

# Применить до конкретной версии
alembic upgrade 001_initial

# Применить одну миграцию вперёд
alembic upgrade +1
```

### Откатить миграции

```powershell
# Откатить одну миграцию назад
alembic downgrade -1

# Откатить до конкретной версии
alembic downgrade 001_initial

# Откатить полностью (удалить все таблицы)
alembic downgrade base
```

### Создать новую миграцию

**После изменений в `app/models.py`:**

```powershell
# 1. Создать миграцию с автогенерацией
alembic revision --autogenerate -m "Описание изменений"

# 2. Проверить сгенерированный файл в alembic/versions/

# 3. Применить миграцию
alembic upgrade head
```

---

## 🔄 Типичные сценарии

### Первый запуск проекта

```powershell
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить инфраструктуру
.\scripts\start_infra.ps1

# 3. Применить миграции
alembic upgrade head

# 4. Запустить FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### После клонирования репозитория

```powershell
# 1. Установить зависимости
pip install -r requirements.txt

# 2. Запустить Docker контейнеры
docker-compose up -d db minio

# 3. Дождаться готовности (10 сек)
Start-Sleep -Seconds 10

# 4. Применить миграции
alembic upgrade head

# 5. Запустить FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### После изменений в моделях (app/models.py)

```powershell
# 1. Создать миграцию
alembic revision --autogenerate -m "Описание изменений"

# 2. Проверить файл миграции (опционально)
Get-Content alembic/versions/*.py | Select-String -Pattern "def upgrade"

# 3. Применить миграцию
alembic upgrade head
```

### Ошибка подключения к БД

```powershell
# 1. Проверить статус контейнеров
docker-compose ps

# 2. Перезапустить PostgreSQL
docker-compose restart db

# 3. Проверить логи
docker-compose logs db

# 4. Переподключиться к БД
alembic current
```

### Полная пересоздание БД

```powershell
# 1. Остановить и удалить контейнеры с данными
docker-compose down -v

# 2. Запустить заново
.\scripts\start_infra.ps1

# 3. Применить миграции
alembic upgrade head
```

---

## 🐛 Устранение проблем

### Ошибка: "table projects has no column named owner_id"

```powershell
# Решение 1: Пересоздать БД
docker-compose down -v
.\scripts\start_infra.ps1
alembic upgrade head

# Решение 2: Проверить миграции
alembic current
alembic history
alembic upgrade head
```

### Ошибка: "Multiple head revisions are present"

```powershell
# Решение: Удалить лишние миграции или пересоздать БД
docker-compose down -v
.\scripts\start_infra.ps1
alembic upgrade head
```

### PostgreSQL не запускается

```powershell
# 1. Проверить порт 5432
netstat -ano | findstr :5432

# 2. Освободить порт (если занят)
Stop-Process -Id <PID> -Force

# 3. Перезапустить
docker-compose restart db
```

### FastAPI не запускается

```powershell
# 1. Проверить порт 8000
netstat -ano | findstr :8000

# 2. Освободить порт
Stop-Process -Id <PID> -Force

# 3. Перезапустить
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 📝 Полезные команды

### Docker

```powershell
# Статус контейнеров
docker-compose ps

# Логи PostgreSQL
docker-compose logs -f db

# Логи MinIO
docker-compose logs -f minio

# Остановить все
docker-compose stop

# Перезапустить всё
docker-compose restart

# Удалить всё (ОСТОРОЖНО!)
docker-compose down -v
```

### База данных

```powershell
# Подключиться к PostgreSQL
docker exec -it postgres_db psql -U postgres -d construction_docs

# Показать все таблицы
\dt

# Показать структуру таблицы
\d projects

# Выйти
\q
```

---

## ✅ Чек-лист проверки

После запуска проверь:

- [ ] Контейнеры запущены: `docker-compose ps` → STATUS = Up
- [ ] Миграции применены: `alembic current` → 002_tz_features (head)
- [ ] FastAPI запущен: http://localhost:8000/docs → Swagger UI
- [ ] Веб-интерфейс доступен: http://localhost:8000 → Главная страница
- [ ] MinIO доступен: http://localhost:9001 → Console

---

## 📚 Дополнительные документы

- [DATABASE_SCHEMA.md](../DATABASE_SCHEMA.md) — Схема базы данных
- [PROCESSING_ALGORITHMS.md](../PROCESSING_ALGORITHMS.md) — Алгоритмы обработки
- [DOCUMENTATION_WORKFLOW.md](../DOCUMENTATION_WORKFLOW.md) — Жизненный цикл документов
- [TECHNOLOGY_SELECTION.md](../TECHNOLOGY_SELECTION.md) — Выбор технологий
- [FRONTEND_README.md](FRONTEND_README.md) — Фронтенд и тесты
- [DEPLOYMENT.md](DEPLOYMENT.md) — Production развёртывание

---

## 🆘 Нужна помощь?

Если возникли проблемы:

1. Проверь логи: `docker-compose logs db`
2. Проверь миграции: `alembic current`
3. Пересоздай БД: `docker-compose down -v` + `alembic upgrade head`
4. Обратись к документации выше
