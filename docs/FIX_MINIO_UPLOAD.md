# 🔧 Исправление проблемы: Файлы не загружаются в MinIO

## Симптомы

При прикреплении файла к проекту:
- Файл не появляется в MinIO
- Ошибка в логах приложения
- Статус 500 или 400 при загрузке

---

## Диагностика

### 1. Проверка статуса MinIO

```bash
docker ps
```

**Ожидаемый результат:**
```
CONTAINER ID   IMAGE          STATUS
minio_storage  Up (healthy)
```

Если контейнер не запущен:
```bash
docker-compose up -d minio
```

---

### 2. Проверка переменных окружения

Проверьте файл `.env`:

```env
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin_password
MINIO_BUCKET=documents
MINIO_USE_SSL=false
```

---

### 3. Проверка синхронизации времени

Ошибка `RequestTimeTooSkewed` возникает при рассинхронизации времени.

**Windows:**
```powershell
# Проверка статуса
w32tm /query /status

# Синхронизация
w32tm /resync
```

**Проверка в приложении:**
```bash
python scripts/test_minio_upload.py
```

---

### 4. Тест загрузки через скрипт

```bash
python scripts/test_minio_upload.py
```

**Ожидаемый вывод:**
```
✅ Клиент создан успешно
✅ Бакет 'documents' существует
✅ Файл успешно загружен: documents/1/test_upload.txt
✅ Контент совпадает!
✅ ВСЕ ТЕСТЫ УСПЕШНЫ!
```

**Если есть ошибки:**
- Проверьте логи MinIO: `docker logs minio_storage`
- Проверьте синхронизацию времени
- Проверьте credentials в `.env`

---

### 5. Проверка логов приложения

При загрузке файла через интерфейс смотрите логи:

```
[INFO] Загрузка файла в MinIO:
  Bucket: documents
  Object Key: documents/1/файл.pdf
  File Name: файл.pdf
  Size: 123456 bytes
[OK] Файл успешно загружен: documents/1/файл.pdf
```

**Если ошибка:**
```
[ERROR] Ошибка загрузки в MinIO:
  Code: RequestTimeTooSkewed
  Message: The difference between the request time and the server's time is too large.
```

**Решение:** Синхронизируйте время!

---

## Возможные причины

### 1. RequestTimeTooSkewed

**Причина:** Рассинхронизация времени между хостом и MinIO

**Решение:**
```powershell
# Синхронизация времени Windows
w32tm /resync

# Перезапуск MinIO
docker-compose restart minio
```

---

### 2. Неправильные credentials

**Причина:** Неверные MINIO_ACCESS_KEY или MINIO_SECRET_KEY

**Проверка:**
```bash
# Проверьте .env
cat .env | findstr MINIO

# Или в PowerShell
Get-Content .env | Select-String MINIO
```

**Решение:** Исправьте в `.env` и перезапустите контейнеры:
```bash
docker-compose restart app
```

---

### 3. Бакет не существует

**Причина:** Бакет `documents` не был создан

**Решение:**
```bash
# Клиент создаст бакет автоматически при запуске
# Если не работает - создайте вручную через MinIO Console

# Откройте браузер: http://localhost:9001
# Login: minioadmin / minioadmin_password
# Создайте бакет: documents
```

---

### 4. Проблемы с сетью

**Причина:** Приложение не может достучаться до MinIO

**Проверка:**
```bash
# Проверьте что MinIO слушает порты
netstat -an | findstr 9000

# Пропингуйте контейнер
docker exec minio_storage ping -c 3 localhost
```

**Решение:** Перезапустите контейнеры:
```bash
docker-compose down
docker-compose up -d
```

---

### 5. Дублирование кода в documents.py

**Причина:** Ранее был дублирующийся код в endpoint

**Проверка:**
```bash
# Проверьте что дубликат удалён
git diff app/routers/api/documents.py
```

**Решение:** Код уже исправлен, перезапустите приложение:
```bash
# Если работает через uvicorn
Ctrl+C
python -m uvicorn app.main:app --reload
```

---

## Полный процесс исправления

```bash
# 1. Проверьте что MinIO запущен
docker ps

# 2. Синхронизируйте время
w32tm /resync

# 3. Проверьте переменные окружения
Get-Content .env | Select-String MINIO

# 4. Протестируйте загрузку
python scripts/test_minio_upload.py

# 5. Перезапустите приложение
docker-compose restart app

# 6. Попробуйте загрузить файл через интерфейс
```

---

## Проверка после исправления

1. Откройте проект в интерфейсе
2. Нажмите "Добавить документ"
3. Выберите PDF файл
4. Включите "Автоматическая классификация"
5. Нажмите "Загрузить"

**Ожидаемый результат:**
- ✅ Файл загружен
- ✅ Страницы классифицированы
- ✅ В логах: `[OK] Файл успешно загружен`

---

## Логи для диагностики

### Успешная загрузка:
```
[INFO] Загрузка файла в MinIO:
  Bucket: documents
  Object Key: documents/1/мой-документ.pdf
  File Name: мой-документ.pdf
  Size: 2345678 bytes
[OK] Файл успешно загружен: documents/1/мой-документ.pdf
[OK] Auto-classified 10 pages for document 25
```

### Ошибка времени:
```
[ERROR] Ошибка загрузки в MinIO:
  Code: RequestTimeTooSkewed
  Message: The difference between the request time and the server's time is too large.
[ERROR] Проблема с синхронизацией времени!
[ERROR] Синхронизируйте системное время: w32tm /resync
```

### Ошибка credentials:
```
[ERROR] Ошибка загрузки в MinIO:
  Code: AccessDenied
  Message: Access Denied
```

---

**Дата:** 2025-01-15
**Версия:** 1.0
