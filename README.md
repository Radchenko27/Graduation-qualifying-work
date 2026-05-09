# Construction Technical Docs Service

Сервис для управления строительной технической документацией с поддержкой обработки PDF, чертежей и материалов.

## 🚀 Возможности

- **Управление проектами** — создание и управление строительными проектами
- **Работа с документами** — загрузка и хранение PDF документов
- **Обработка PDF** — извлечение текста, конвертация страниц в изображения
- **Чертежи** — управление чертежами с привязкой к документам и проектам
- **Материалы** — каталог строительных материалов
- **Связи материалов и чертежей** — учёт материалов на чертежах
- **Отчёты** — генерация отчётов по проектам
- **Пользователи и права доступа** — система авторизации и разграничения прав
- **Хранение файлов** — MinIO S3-совместимое хранилище с presigned URL
- **REST API** — полный REST API с документацией Swagger

## 📋 Требования

- Docker
- Docker Compose

## 🛠️ Быстрый старт

### 1. Запуск сервисов

```bash
docker-compose up -d
```

### 2. Применение миграций

```bash
docker-compose exec app alembic upgrade head
```

### 3. Инициализация тестовыми данными

```bash
docker-compose exec app python scripts/init_db.py
```

### 4. Доступ к сервисам

| Сервис | URL |
|--------|-----|
| API | http://localhost:8000 |
| Документация API | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |
| PostgreSQL | localhost:5432 |

## 👤 Тестовые пользователи

После инициализации будут созданы тестовые пользователи:

| Username | Password | Session Key |
|----------|----------|-------------|
| ivan.petrov | password123 | session_key_ivan.petrov |
| maria.sidorova | password123 | session_key_maria.sidorova |
| alexey.kozlov | password123 | session_key_alexey.kozlov |

## 📚 API Документация

Полная документация доступна по адресу http://localhost:8000/docs

### Основные эндпоинты

- `POST /api/users/register` — Регистрация
- `POST /api/users/login` — Авторизация
- `POST /api/projects/` — Создать проект
- `GET /api/projects/` — Список проектов
- `POST /api/minio-files/upload` — Загрузить файл в MinIO
- `GET /api/minio-files/{object_name}/url` — Получить presigned URL

Подробнее в [QUICKSTART.md](QUICKSTART.md)

## 📦 Структура проекта

```
app/
├── models.py           # SQLAlchemy модели
├── schemas.py          # Pydantic схемы
├── crud.py             # CRUD операции
├── storage.py          # MinIO клиент
├── dependencies.py     # Аутентификация
├── main.py             # Точка входа
└── routers/            # API роутеры
```

## 📚 Дополнительная документация

- [QUICKSTART.md](docs/md/Quickstart.md) — Быстрый старт
- [DEPLOYMENT.md](docs/md/DEPLOYMENT.md) — Руководство по развертыванию
- [MINIO_SETUP.md](docs/md/MINIO_SETUP.md) — Настройка MinIO

