# 🔧 Проблема: RequestTimeTooSkewed

## Ошибка

```
[ERROR] Ошибка создания бакета documents: An error occurred (RequestTimeTooSkewed)
when calling the CreateBucket operation: The difference between the request time
and the server's time is too large.
```

## Причина

Ошибка `RequestTimeTooSkewed` возникает, когда разница между временем клиента (вашего компьютера) и сервера (MinIO) превышает допустимое значение (обычно 15 минут).

Это происходит из-за:
- Несинхронизированных системных часов
- Неправильного часового пояса
- Разницы во времени между хостом и Docker контейнером

---

## ✅ Решения

### Решение 1: Синхронизация системного времени (рекомендуется)

#### Windows

**Через настройки:**
1. Откройте **Параметры** → **Время и язык** → **Дата и время**
2. Включите **"Автоматическая установка времени"**
3. Нажмите **"Синхронизировать сейчас"**

**Через командную строку:**
```powershell
# Синхронизация с интернет-серверами
w32tm /resync

# Проверка статуса
w32tm /query /status
```

**Установка часового пояса:**
```powershell
# Для Москвы
Set-TimeZone -Id "Russian Standard Time"

# Проверка текущего часового пояса
Get-TimeZone
```

#### Linux

```bash
# Синхронизация времени
sudo timedatectl set-ntp true

# Проверка статуса
timedatectl status

# Установка часового пояса
sudo timedatectl set-timezone Europe/Moscow

# Перезапуск Docker
sudo systemctl restart docker
```

---

### Решение 2: Настройка Docker контейнеров

#### Обновление docker-compose.yml

Добавьте синхронизацию времени в контейнеры:

```yaml
minio:
  image: minio/minio:latest
  container_name: minio_storage
  command: server /data --console-address ":9001"
  environment:
    MINIO_ROOT_USER: ${MINIO_ROOT_USER:-minioadmin}
    MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD:-minioadmin_password}
    TZ: ${TZ:-Europe/Moscow}  # ← Добавить
  volumes:
    - minio_data:/data
    - /etc/localtime:/etc/localtime:ro  # ← Добавить

app:
  build: .
  container_name: fastapi_app
  environment:
    # ... другие переменные ...
    TZ: ${TZ:-Europe/Moscow}  # ← Добавить
  volumes:
    - ./data:/app/data
    - /etc/localtime:/etc/localtime:ro  # ← Добавить
```

#### Обновление .env

Добавьте настройку часового пояса:

```env
# Timezone (для синхронизации времени в Docker контейнерах)
TZ=Europe/Moscow
```

#### Перезапуск контейнеров

```bash
# Остановить контейнеры
docker-compose down

# Запустить контейнеры
docker-compose up -d
```

---

### Решение 3: Использование диагностического скрипта

Запустите скрипт для автоматической диагностики:

```bash
python scripts/fix_time_sync.py
```

Скрипт выполнит:
- ✅ Проверку системного времени
- ✅ Проверку времени в Docker контейнерах
- ✅ Проверку соединения с MinIO
- ✅ Синхронизацию времени (на Windows)
- ✅ Покажет детальное решение проблемы

---

## 🔍 Диагностика

### Проверка системного времени

**Windows:**
```powershell
# Текущее время
Get-Date

# Часовой пояс
Get-TimeZone

# Статус NTP
w32tm /query /status
```

**Linux:**
```bash
# Текущее время
date

# Часовой пояс
timedatectl

# Статус NTP
timedatectl status
```

### Проверка времени в Docker контейнерах

```bash
# Время в контейнере MinIO
docker exec minio_storage date

# Время в контейнере приложения
docker exec fastapi_app date

# Сравнение с хостом
date
```

### Проверка соединения с MinIO

```python
from app.services.minio_client import MinIOClient

try:
    client = MinIOClient()
    print("✅ Подключение успешно!")
except Exception as e:
    print(f"❌ Ошибка: {e}")
```

---

## 📋 Полный процесс исправления

### Шаг 1: Синхронизируйте системное время

```powershell
# Windows
w32tm /resync
```

или

```bash
# Linux
sudo timedatectl set-ntp true
```

### Шаг 2: Обновите .env файл

```env
TZ=Europe/Moscow
```

### Шаг 3: Обновите docker-compose.yml

Добавьте переменную `TZ` и volume `/etc/localtime` для сервисов.

### Шаг 4: Перезапустите Docker контейнеры

```bash
docker-compose down
docker-compose up -d
```

### Шаг 5: Проверьте результат

```bash
# Проверьте время в контейнерах
docker exec minio_storage date
docker exec fastapi_app date

# Запустите приложение
python -m uvicorn app.main:app --reload
```

---

## ⚠️ Если проблема сохраняется

### Проверьте BIOS/UEFI

1. Перезагрузите компьютер
2. Войдите в BIOS/UEFI (обычно F2, Del, F12)
3. Найдите настройки времени/даты
4. Отключите NTP в BIOS
5. Используйте только NTP в операционной системе

### Перезагрузите компьютер

Иногда помогает простая перезагрузка для синхронизации всех системных часов.

### Проверьте сетевые настройки

Убедитесь, что:
- Компьютер подключён к интернету
- Фаервол не блокирует NTP (порт 123)
- Настройки прокси не мешают синхронизации

---

## 📚 Дополнительные ресурсы

- [Документация MinIO](https://min.io/docs/minio/linux/operations/concepts/ntp-sync.html)
- [Windows Time Service](https://docs.microsoft.com/en-us/windows-server/networking/windows-time-service/windows-time-service-overview)
- [systemd-timesyncd](https://man7.org/linux/man-pages/systemd-timesyncd.service.html)

---

## 🆘 Быстрое решение

Если нужно быстро запустить приложение без синхронизации времени:

```bash
# 1. Синхронизируйте время
w32tm /resync

# 2. Перезапустите Docker
docker-compose restart

# 3. Запустите приложение
python -m uvicorn app.main:app --reload
```

---

**Дата создания:** 2025-01-15
**Версия:** 1.0