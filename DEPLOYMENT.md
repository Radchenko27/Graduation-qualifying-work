# Развертывание проекта с Docker, PostgreSQL и MinIO

## Требования

- Docker
- Docker Compose

## Структура проекта

```
.
├── app/                    # Приложение FastAPI
├── alembic/               # Миграции базы данных
├── docker-compose.yml     # Конфигурация Docker Compose
├── Dockerfile             # Образ приложения
├── .env                   # Переменные окружения
├── requirements.txt       # Зависимости Python
└── DEPLOYMENT.md          # Этот файл
```

## Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# PostgreSQL Database
POSTGRES_DB=construction_docs
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql://postgres:postgres_password@db:5432/construction_docs

# MinIO Object Storage
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin_password
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_password
MINIO_BUCKET=documents
MINIO_USE_SSL=false

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=your-secret-key-change-this-in-production
```

## Быстрый запуск

1. **Запуск сервисов:**

```bash
docker-compose up -d
```

2. **Проверка статуса:**

```bash
docker-compose ps
```

3. **Просмотр логов:**

```bash
# Все сервисы
docker-compose logs -f

# Конкретный сервис
docker-compose logs -f app
docker-compose logs -f db
docker-compose logs -f minio
```

## Доступ к сервисам

### FastAPI Application
- URL: http://localhost:8000
- API документация: http://localhost:8000/docs
- Альтернативная документация: http://localhost:8000/redoc

### PostgreSQL
- Host: localhost
- Port: 5432
- Database: construction_docs
- Username: postgres
- Password: postgres_password

Подключение через psql:
```bash
psql -h localhost -U postgres -d construction_docs
```

Подключение через Docker:
```bash
docker-compose exec db psql -U postgres -d construction_docs
```

### MinIO
- API: http://localhost:9000
- Console: http://localhost:9001
- Access Key: minioadmin
- Secret Key: minioadmin_password

## Миграции базы данных

Миграции запускаются автоматически при старте контейнера приложения.

### Ручное управление миграциями

```bash
# Создать новую миграцию
docker-compose exec app alembic revision --autogenerate -m "Description"

# Применить миграции
docker-compose exec app alembic upgrade head

# Откатить миграцию
docker-compose exec app alembic downgrade -1

# Просмотр истории миграций
docker-compose exec app alembic history

# Текущая версия
docker-compose exec app alembic current
```

## Работа с файлами

Файлы хранятся в MinIO S3-совместимом хранилище.

### API эндпоинты для работы с файлами:

- `POST /api/files/upload` - Загрузка файла
- `GET /api/files/{file_id}` - Информация о файле
- `GET /api/files/{file_id}/download` - Скачивание файла
- `GET /api/files/{file_id}/url` - Получить URL для доступа
- `DELETE /api/files/{file_id}` - Удаление файла
- `GET /api/files/` - Список файлов

### Пример загрузки файла через curl:

```bash
curl -X POST "http://localhost:8000/api/files/upload" \
  -H "X-Session-Key: your-session-key" \
  -F "file=@/path/to/file.pdf" \
  -F "project_id=1"
```

## Управление контейнерами

### Остановка сервисов:

```bash
docker-compose stop
```

### Запуск сервисов:

```bash
docker-compose start
```

### Перезапуск сервисов:

```bash
docker-compose restart
```

### Остановка и удаление контейнеров:

```bash
docker-compose down
```

### Остановка и удаление контейнеров с томами (данными):

```bash
docker-compose down -v
```

### Пересборка образа приложения:

```bash
docker-compose build app
docker-compose up -d app
```

## Резервное копирование

### Резервное копирование базы данных:

```bash
docker-compose exec db pg_dump -U postgres construction_docs > backup.sql
```

### Восстановление базы данных:

```bash
docker-compose exec -T db psql -U postgres construction_docs < backup.sql
```

### Резервное копирование MinIO данных:

Данные MinIO хранятся в томе `minio_data`. Для резервного копирования:

```bash
docker run --rm -v minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup.tar.gz -C /data .
```

## Мониторинг

### Просмотр использования ресурсов:

```bash
docker stats
```

### Логи конкретного сервиса:

```bash
docker-compose logs -f app
```

## Устранение проблем

### База данных не подключается:

```bash
# Проверить статус контейнера
docker-compose ps db

# Проверить логи
docker-compose logs db

# Перезапустить базу данных
docker-compose restart db
```

### MinIO не доступен:

```bash
# Проверить статус контейнера
docker-compose ps minio

# Проверить логи
docker-compose logs minio

# Пересоздать бакет
docker-compose restart minio_init
```

### Приложение не запускается:

```bash
# Проверить логи
docker-compose logs app

# Пересобрать образ
docker-compose build --no-cache app
docker-compose up -d app
```

## Безопасность

### Для production окружения:

1. **Измените все пароли и секретные ключи** в файле `.env`
2. **Используйте SSL/TLS** для MinIO (MINIO_USE_SSL=true)
3. **Ограничьте доступ** к базе данных через firewall
4. **Настройте обратный прокси** (nginx) для HTTPS
5. **Используйте защищенные секреты** вместо переменных окружения
6. **Настройте логирование** и мониторинг
7. **Регулярно создавайте резервные копии**

### Пример защищённого .env для production:

```env
POSTGRES_PASSWORD=<strong-random-password>
MINIO_ROOT_PASSWORD=<strong-random-password>
SECRET_KEY=<strong-random-secret-key>
MINIO_USE_SSL=true
```

## Масштабирование

### Масштабирование приложения:

```bash
docker-compose up -d --scale app=3
```

Примечание: Для масштабирования необходимо настроить общий доступ к сессиям (например, через Redis).

## Полезные команды

### Войти в контейнер приложения:

```bash
docker-compose exec app bash
```

### Войти в контейнер базы данных:

```bash
docker-compose exec db bash
```

### Просмотреть список миграций:

```bash
docker-compose exec app alembic history
```

### Очистить все данные (осторожно!):

```bash
docker-compose down -v
docker system prune -a
```

## Поддержка

При возникновении проблем:

1. Проверьте логи: `docker-compose logs`
2. Проверьте статус контейнеров: `docker-compose ps`
3. Проверьте переменные окружения: `docker-compose config`
4. Перезапустите проблемный сервис
