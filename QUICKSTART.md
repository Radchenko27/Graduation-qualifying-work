# 🚀 Быстрый старт (Windows)

## Требования

- **Docker Desktop** версии 20.10+ (с включённым Docker Compose)
- **PowerShell** или **Command Prompt (cmd)**

> 💡 **Рекомендация:** Установите `make` для удобства:
> - Через **Chocolatey**: `choco install make`
> - Через **Winget**: `winget install GnuWin32.Make`
> - Или используйте команды `docker-compose` напрямую (см. ниже)

---

## 📋 Пошаговая инструкция по запуску

### Шаг 1: Подготовка окружения

Откройте **PowerShell** или **Command Prompt** в папке проекта:

```cmd
:: Клонировать репозиторий (выполните в Git Bash или PowerShell)
git clone <репозиторий>
cd <папка проекта>

:: Создать файл переменных окружения (опционально)
:: По умолчанию используются тестовые значения из docker-compose.yml
copy .env.example .env
```

### Шаг 2: Сборка Docker образов

```cmd
:: Вариант А: через make (если установлен)
make build

:: Вариант Б: через docker-compose (PowerShell)
docker-compose build

:: Вариант В: через docker-compose (cmd)
docker-compose build
```

### Шаг 3: Запуск инфраструктуры (PostgreSQL + MinIO + App)

```cmd
:: Вариант А: через make
make up

:: Вариант Б: через docker-compose
docker-compose up -d

:: Проверить статус всех сервисов
docker-compose ps
```

**После запуска будут доступны:**
- 🌐 **API** — http://localhost:8000
- 📚 **Swagger UI** — http://localhost:8000/docs  
- 📦 **MinIO Console** — http://localhost:9001 (логин: `minioadmin` / пароль: `minioadmin_password`)
- 🗄️ **PostgreSQL** — localhost:5432

### Шаг 4: Применение миграций базы данных

```cmd
:: Вариант А: через make
make migrate

:: Вариант Б: через docker-compose
docker-compose exec app alembic upgrade head

:: Вариант В: через docker
docker exec fastapi_app alembic upgrade head
```

**Проверить статус миграций:**
```cmd
docker-compose exec app alembic current
```

### Шаг 5: Инициализация базы данных (тестовые данные)

```cmd
:: Вариант А: через make
make init-db

:: Вариант Б: через docker-compose
docker-compose exec app python scripts/init_db.py
```

### Шаг 6: Проверка работоспособности

```cmd
:: Вариант А: через make
make health-check

:: Вариант Б: вручную (PowerShell)
Invoke-WebRequest -Uri http://localhost:8000/health

:: Вариант В: вручную (cmd)
curl http://localhost:8000/health

:: Проверить логи
docker-compose logs -f
```

---

## ⚡ Быстрый запуск (все команды вместе)

```cmd
:: Выполнить последовательно:
docker-compose build
docker-compose up -d
docker-compose exec app alembic upgrade head
docker-compose exec app python scripts/init_db.py
```

---

## Доступ к сервисам

| Сервис | URL | Логин/Пароль |
|--------|-----|--------------|
| API | http://localhost:8000 | - |
| Документация API | http://localhost:8000/docs | - |
| MinIO Console | http://localhost:9001 | minioadmin / minioadmin_password |
| PostgreSQL | localhost:5432 | postgres / postgres_password |

## Тестовые пользователи

После инициализации базы данных будут созданы тестовые пользователи:

| Username | Password | Session Key |
|----------|----------|-------------|
| ivan.petrov | password123 | session_key_ivan.petrov |
| maria.sidorova | password123 | session_key_maria.sidorova |
| alexey.kozlov | password123 | session_key_alexey.kozlov |

## Пример запроса с аутентификацией

```cmd
:: PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/api/users/1" -Headers @{"X-Session-Key"="session_key_ivan.petrov"}

:: cmd
curl -X GET "http://localhost:8000/api/users/1" -H "X-Session-Key: session_key_ivan.petrov"
```

## Основные команды

| Команда make | Команда docker-compose | Описание |
|--------------|------------------------|----------|
| `make up` | `docker-compose up -d` | Запустить сервисы |
| `make down` | `docker-compose down` | Остановить сервисы |
| `make logs` | `docker-compose logs -f` | Показать логи |
| `make logs-app` | `docker-compose logs -f app` | Логи приложения |
| `make db-shell` | `docker-compose exec db psql -U postgres -d construction_docs` | Подключиться к PostgreSQL |
| `make migrate` | `docker-compose exec app alembic upgrade head` | Применить миграции |
| `make migrate-status` | `docker-compose exec app alembic current` | Статус миграций |
| `make health-check` | `docker-compose exec app python scripts/health_check.py` | Проверить работоспособность |
| `make clean` | `docker-compose down -v` | Удалить все данные (осторожно!) |

## Структура проекта

```
.
├── app/                    # Приложение FastAPI
│   ├── models.py          # SQLAlchemy модели
│   ├── schemas.py         # Pydantic схемы
│   ├── crud.py            # CRUD операции
│   ├── routers/           # API роутеры
│   ├── storage.py         # MinIO клиент
│   └── dependencies.py    # Зависимости
├── alembic/               # Миграции БД
├── scripts/               # Скрипты
│   ├── init_db.py        # Инициализация БД
│   └── health_check.py   # Проверка работоспособности
├── docker-compose.yml     # Docker Compose конфигурация
├── Dockerfile             # Docker образ приложения
├── Makefile               # Удобные команды
└── .env                   # Переменные окружения
```

## Следующие шаги

1. Изучите [DEPLOYMENT.md](DEPLOYMENT.md) для подробной информации
2. Откройте http://localhost:8000/docs для интерактивной документации API

## Устранение проблем

### Сервисы не запускаются

```cmd
:: Проверить логи
docker-compose logs -f

:: Перезапустить
docker-compose restart
```

### База данных не инициализируется

```cmd
:: Проверить миграции
docker-compose exec app alembic current

:: Применить миграции
docker-compose exec app alembic upgrade head

:: Инициализировать заново
docker-compose exec app python scripts/init_db.py
```

### MinIO недоступен

```cmd
:: Проверить статус
docker-compose ps minio

:: Перезапустить MinIO
docker-compose restart minio
```

### Docker Desktop не запущен

Убедитесь, что **Docker Desktop** запущен (иконка в системном трее).

---

## Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Docker Documentation](https://docs.docker.com/)
