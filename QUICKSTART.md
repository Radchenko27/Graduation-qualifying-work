# 🚀 Быстрый старт (Windows)

## Требования

- **Docker Desktop** версии 20.10+ (с включённым Docker Compose)
- **Python** 3.12+
- **PowerShell** или **Command Prompt (cmd)**

> 💡 **Архитектура:** PostgreSQL и MinIO в Docker контейнерах, FastAPI с фронтендом локально

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

### Шаг 2: Запуск инфраструктуры (PostgreSQL + MinIO)

**Вариант А: Автоматический запуск (рекомендуется)**

```powershell
# Запустить PostgreSQL и MinIO, применить миграции
.\scripts\start_infra.ps1
```

**Вариант Б: Ручной запуск**

```powershell
# Запустить только PostgreSQL и MinIO (без FastAPI)
docker-compose up -d db minio

# Дождаться готовности (5-10 секунд)
Start-Sleep -Seconds 10

# Применить миграции
alembic upgrade head

# Инициализировать тестовые данные
python scripts/init_db.py
```

### Шаг 3: Запуск FastAPI с фронтендом

**В новом окне PowerShell:**

```powershell
# Запуск с автоперезагрузкой (для разработки)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или без автоперезагрузки (для production)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## ⚡ Быстрый запуск (все команды вместе)

```powershell
# 1. Запустить инфраструктуру
.\scripts\start_infra.ps1

# 2. В новом окне запустить FastAPI
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

## Локальный запуск (без Docker)

```powershell
# Установка зависимостей
pip install -r requirements.txt

# Применение миграций
alembic upgrade head

# Запуск приложения
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

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

### Базa данных не инициализируется

```powershell
# Применить миграции вручную
alembic upgrade head

# Проверить статус миграций
alembic current

# Инициализировать тестовые данные
python scripts/init_db.py
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

## Дополнительные документы

- [FRONTEND_README.md](FRONTEND_README.md) — Подробно о фронтенде и тестах
- [DEPLOYMENT.md](DEPLOYMENT.md) — Развёртывание в production
- [MINIO_SETUP.md](MINIO_SETUP.md) — Настройка MinIO
