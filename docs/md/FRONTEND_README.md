# Frontend и тесты

## Структура приложения

Приложение теперь включает в себя:

### API (RESTful)
- `/api/users/*` — Управление пользователями
- `/api/projects/*` — Управление проектами
- `/api/documents/*` — Управление документами
- `/api/drawing-calculations/*` — Расчёты элементов чертежей
- `/api/estimates/*` — Управление сметами

### Frontend (MVC шаблоны)
- `/` — Главная страница
- `/login` — Вход в систему
- `/register` — Регистрация
- `/projects` — Список проектов
- `/documents` — Список документов
- `/drawing-calculations` — Расчёты чертежей
- `/estimates` — Сметы
- `/profile` — Профиль пользователя

## Запуск приложения

### Вариант 1: Через Docker (рекомендуется)

```cmd
:: Сборка и запуск
docker-compose build
docker-compose up -d

:: Применение миграций
docker-compose exec app alembic upgrade head

:: Инициализация БД (тестовые данные)
docker-compose exec app python scripts/init_db.py
```

**Доступ:**
- Frontend: http://localhost:8000
- API Swagger: http://localhost:8000/docs
- MinIO Console: http://localhost:9001

### Вариант 2: Локально (без Docker)

```powershell
# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

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

# Запуск тестов с покрытием
pytest --cov=app

# Запуск конкретных тестов
pytest tests/test_api.py::TestUsersAPI -v

# Запуск с подробным выводом
pytest -v --tb=short
```

## Тестовые данные

После `init_db.py` создаются тестовые пользователи:

| Username | Password |
|----------|----------|
| ivan.petrov | password123 |
| maria.sidorova | password123 |
| alexey.kozlov | password123 |

## Структура файлов

```
app/
├── main.py                 # Основной файл приложения
├── models.py               # SQLAlchemy модели
├── schemas.py              # Pydantic схемы
├── crud.py                 # CRUD операции
├── db.py                   # Конфигурация БД
├── dependencies.py         # Зависимости FastAPI
├── storage.py              # MinIO клиент
├── routers/
│   ├── api/                # RESTful API роутеры
│   │   ├── users.py
│   │   ├── projects.py
│   │   ├── documents.py
│   │   ├── drawing_calculations.py
│   │   └── estimates.py
│   └── frontend.py         # MVC шаблоны (HTML)
├── templates/              # Jinja2 шаблоны
│   ├── base.html           # Базовый шаблон
│   ├── home.html           # Главная страница
│   ├── login.html          # Вход
│   ├── register.html       # Регистрация
│   ├── projects.html       # Проекты
│   ├── documents.html      # Документы
│   ├── drawing_calculations.html  # Расчёты
│   ├── estimates.html      # Сметы
│   └── profile.html        # Профиль
└── static/                 # Статические файлы
    ├── css/
    │   └── style.css       # Стили
    └── js/
        └── main.js         # JavaScript
```

## Особенности реализации

### 1. RESTful API
- Все API эндпоинты возвращают JSON
- Аутентификация через `X-Session-Key` заголовок
- Полная документация в Swagger UI

### 2. MVC Frontend
- Jinja2 шаблоны для рендеринга HTML
- Bootstrap-подобные стили (кастомные)
- JavaScript для AJAX запросов к API
- localStorage для хранения session_key

### 3. Аутентификация
- Сессии через session_key
- Поддержка cookie и заголовков
- Автоматическое перенаправление на /login при отсутствии сессии

### 4. Тестирование
- pytest для unit-тестов
- TestClient для тестирования API
- Тестовая SQLite база данных
- Покрытие всех основных CRUD операций

## API примеры

### Вход в систему
```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{"username": "ivan.petrov", "password": "password123"}'
```

### Получить проекты
```bash
curl -X GET "http://localhost:8000/api/projects/" \
  -H "X-Session-Key: session_key_ivan.petrov"
```

### Создать проект
```bash
curl -X POST "http://localhost:8000/api/projects/" \
  -H "Content-Type: application/json" \
  -H "X-Session-Key: session_key_ivan.petrov" \
  -d '{"name": "Новый проект", "description": "Описание"}'
```

## Дополнительная информация

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health
