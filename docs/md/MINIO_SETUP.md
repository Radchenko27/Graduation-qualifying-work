# Настройка MinIO для хранения файлов

## Обзор

Проект использует MinIO как S3-совместимое хранилище файлов. Файлы хранятся в защищённом бакете, а доступ осуществляется через временные presigned URL.

## Быстрый старт

1. Запустите Docker Compose:
```bash
docker-compose up -d
```

2. MinIO будет доступен по адресу:
- API: http://localhost:9000
- Консоль: http://localhost:9001
- Логин: `minioadmin`
- Пароль: `minioadmin_password`

3. Бакет `documents` будет создан автоматически при первом запуске приложения.

## API эндпоинты для работы с файлами

Все эндпоинты требуют аутентификацию (заголовок `X-Session-Key`).

### Загрузка файла
```http
POST /api/minio-files/upload
Content-Type: multipart/form-data
X-Session-Key: session_key_ivan.petrov

file: <файл>
project_id: 1 (опционально)
document_id: 1 (опционально)
```

**Ответ:**
```json
{
  "filename": "document.pdf",
  "object_name": "550e8400-e29b-41d4-a716-446655440000.pdf",
  "file_size": 123456,
  "content_type": "application/pdf",
  "project_id": 1,
  "document_id": null,
  "uploaded_by": 1
}
```

### Скачивание файла
```http
GET /api/minio-files/{object_name}/download
X-Session-Key: session_key_ivan.petrov
```

### Получить presigned URL
```http
GET /api/minio-files/{object_name}/url
X-Session-Key: session_key_ivan.petrov
```

**Ответ:**
```json
{
  "url": "http://localhost:9000/documents/550e8400-e29b-41d4-a716-446655440000.pdf?X-Amz-Algorithm=...",
  "object_name": "550e8400-e29b-41d4-a716-446655440000.pdf",
  "expires_in": 3600
}
```

### Удалить файл
```http
DELETE /api/minio-files/{object_name}
X-Session-Key: session_key_ivan.petrov
```

### Список всех файлов
```http
GET /api/minio-files/
X-Session-Key: session_key_ivan.petrov
```

### Информация о файле
```http
GET /api/minio-files/{object_name}/info
X-Session-Key: session_key_ivan.petrov
```

## Примеры использования

### Загрузка файла через curl
```bash
curl -X POST "http://localhost:8000/api/minio-files/upload" \
  -H "X-Session-Key: session_key_ivan.petrov" \
  -F "file=@/path/to/document.pdf" \
  -F "project_id=1"
```

### Загрузка файла через Python
```python
import requests

url = "http://localhost:8000/api/minio-files/upload"
headers = {"X-Session-Key": "session_key_ivan.petrov"}
files = {"file": open("document.pdf", "rb")}
data = {"project_id": 1}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

### Скачивание файла через presigned URL
```python
# 1. Получаем presigned URL
response = requests.get(
    f"http://localhost:8000/api/minio-files/{object_name}/url",
    headers={"X-Session-Key": "session_key_ivan.petrov"}
)
presigned_url = response.json()["url"]

# 2. Скачиваем файл по presigned URL
file_response = requests.get(presigned_url)
with open("downloaded.pdf", "wb") as f:
    f.write(file_response.content)
```

## Presigned URL

### Что это такое?
Presigned URL — это временная ссылка на файл, которая содержит подпись для аутентификации. Это позволяет:

1. **Безопасный доступ** к файлам без передачи ключей
2. **Временный доступ** — URL истекает через заданное время (по умолчанию 1 час)
3. **Контроль доступа** — можно устанавливать разные сроки действия

### Преимущества перед публичным доступом

- **Безопасность** — файлы не доступны публично
- **Гибкость** — разные URL для разных пользователей
- **Контроль** — можно отозвать доступ, удалив объект

### Настройка времени действия

В `app/storage.py` можно изменить время действия presigned URL:

```python
# По умолчанию 3600 секунд (1 час)
presigned_url = self.client.presigned_get_object(
    self.bucket_name,
    object_name,
    expires=3600  # Измените это значение
)
```

## Настройка бакета

### Автоматическое создание
Бакет создаётся автоматически при первом запуске приложения в `app/storage.py`.

### Ручная настройка через MinIO Console

1. Откройте http://localhost:9001
2. Войдите: `minioadmin` / `minioadmin_password`
3. Перейдите в раздел **Buckets**
4. Создайте бакет `documents` (если ещё не создан)
5. **Политика доступа** — не требуется, используется presigned URL

### Через MinIO Client (mc)

```bash
# Установите алиас
docker run --rm -it minio/mc alias set myminio http://localhost:9000 minioadmin minioadmin_password

# Создайте бакет
docker run --rm -it minio/mc mb myminio/documents

# Проверьте бакет
docker run --rm -it minio/mc ls myminio/documents
```

## Хранение ссылок в БД

Для связывания файлов с сущностями приложения рекомендуется:

1. **Сохранять `object_name`** в базе данных (уникальное имя файла в MinIO)
2. **Использовать presigned URL** для доступа к файлам
3. **Не хранить полные URL** — они временные

Пример структуры в БД:
```python
# В модели документа
file_object_name: str  # Например: "550e8400-e29b-41d4-a716-446655440000.pdf"
file_size: int
content_type: str
```

## Устранение проблем

### Бакет не создаётся автоматически

```bash
# Проверьте логи приложения
docker-compose logs app | grep -i minio

# Создайте бакет вручную
docker-compose exec app python -c "
from app.storage import storage
storage._ensure_bucket_exists()
"
```

### Presigned URL не работает

1. Проверьте, что файл существует:
```bash
docker-compose exec app python -c "
from app.storage import storage
print(storage.file_exists('object_name'))
"
```

2. Проверьте время системы (должно быть синхронизировано)

3. Увеличьте время действия URL в коде

### Ошибка "Access Denied"

- Убедитесь, что используете правильные ключи доступа
- Проверьте переменные окружения в `.env`
- Перезапустите контейнер приложения:
```bash
docker-compose restart app
```

## Безопасность в production

### Рекомендации:

1. **Измените пароли** по умолчанию в `.env`:
```env
MINIO_ROOT_PASSWORD=<сильный-пароль>
SECRET_KEY=<сильный-секретный-ключ>
```

2. **Используйте SSL/TLS**:
```env
MINIO_USE_SSL=true
```

3. **Ограничьте время действия presigned URL** для чувствительных файлов:
```python
# Для документов: 1 час
expires=3600

# Для временных файлов: 5 минут
expires=300
```

4. **Настройте логирование** для отслеживания доступа к файлам

5. **Регулярно создавайте резервные копии** бакета MinIO:
```bash
docker run --rm -v minio_data:/data -v $(pwd):/backup alpine tar czf /backup/minio_backup.tar.gz -C /data .
```

## Мониторинг

### Проверка состояния MinIO:
```bash
# Логи
docker-compose logs -f minio

# Статус контейнера
docker-compose ps minio

# Проверка здоровья
curl http://localhost:9000/minio/health/live
```

### Статистика через консоль:
- Откройте http://localhost:9001
- Перейдите в раздел **Monitoring**
- Просмотрите метрики использования хранилища

## Дополнительные ресурсы

- [MinIO Documentation](https://min.io/docs/minio/linux/index.html)
- [Presigned URLs](https://min.io/docs/minio/linux/developers/python/minio-py.html#presigned-operations)
- [FastAPI Upload Files](https://fastapi.tiangolo.com/tutorial/request-files/)
