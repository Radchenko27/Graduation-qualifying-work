# Аутентификация через Cookies

## 📋 Обзор

Теперь сессия пользователя хранится в HTTP-only cookies на стороне клиента вместо передачи через заголовок `X-Session-Key`.

---

## 🔐 Как это работает

### Регистрация/Login

1. Пользователь регистрируется или логинится
2. Сервер создаёт сессию в БД
3. Сервер устанавливает cookie `session_key` в браузере

### Запросы к API

1. Браузер автоматически отправляет cookie с каждым запросом
2. Сервер проверяет cookie и получает пользователя из БД
3. Запрос выполняется, если сессия валидна

### Logout

1. Пользователь нажимает "Выйти"
2. Сервер удаляет сессию из БД
3. Сервер удаляет cookie из браузера

---

## 🍪 Параметры Cookie

```python
response.set_cookie(
    key="session_key",
    value=auth_session.session_key,
    httponly=True,    # Недоступен через JavaScript (защита от XSS)
    secure=False,     # True для HTTPS (production)
    samesite="lax",   # Защита от CSRF
    max_age=86400     # 24 часа
)
```

| Параметр | Значение | Описание |
|----------|----------|----------|
| `httponly` | `True` | Cookie недоступен через JavaScript |
| `secure` | `False` (dev) / `True` (prod) | Отправляется только по HTTPS |
| `samesite` | `lax` | Защита от CSRF атак |
| `max_age` | `86400` | 24 часа в секундах |

---

## 📡 API Эндпоинты

### Регистрация с cookie

```http
POST /api/users/register
Content-Type: application/json

{
  "username": "ivan.petrov",
  "password": "password123",
  "first_name": "Иван",
  "last_name": "Петров",
  "email": "ivan@example.com"
}
```

**Ответ:**
```json
{
  "id": 1,
  "username": "ivan.petrov",
  "first_name": "Иван",
  "last_name": "Петров",
  "email": "ivan@example.com"
}
```

**Cookie устанавливается автоматически!**

---

### Логин с cookie

```http
POST /api/users/login
Content-Type: application/json

{
  "username": "ivan.petrov",
  "password": "password123"
}
```

**Ответ:**
```json
{
  "id": 1,
  "user_id": 1,
  "session_key": "abc123...",
  "created_at": "2025-01-01T10:00:00",
  "expires_at": "2025-01-02T10:00:00"
}
```

**Cookie устанавливается автоматически!**

---

### Защищённые запросы

Теперь **НЕ НУЖНО** отправлять заголовок `X-Session-Key`!

```http
GET /api/projects/
# Cookie отправляется автоматически

GET /api/users/me
# Cookie отправляется автоматически
```

**Раньше:**
```http
GET /api/projects/
X-Session-Key: abc123...
```

**Теперь:**
```http
GET /api/projects/
# Cookie отправляется автоматически браузером
```

---

### Logout

```http
POST /api/users/logout
```

**Ответ:** `204 No Content`

**Cookie удаляется автоматически!**

---

## 🌐 Обратная совместимость

Для обратной совместимости заголовок `X-Session-Key` всё ещё работает!

Приоритет проверки:
1. **Cookie** (если есть)
2. **Заголовок** `X-Session-Key` (если нет cookie)

Это позволяет использовать оба способа одновременно.

---

## 💻 Использование в JavaScript

### Fetch API

```javascript
// Логин - cookie устанавливается автоматически
const response = await fetch('http://localhost:8000/api/users/login', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include',  // Важно для cookies!
  body: JSON.stringify({
    username: 'ivan.petrov',
    password: 'password123'
  })
});

// Защищённый запрос - cookie отправляется автоматически
const projectsResponse = await fetch('http://localhost:8000/api/projects/', {
  credentials: 'include'  // Важно для cookies!
});

const projects = await projectsResponse.json();
```

### Axios

```javascript
import axios from 'axios';

// Настройка axios для отправки cookies
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true  // Важно для cookies!
});

// Логин
const login = async () => {
  const response = await api.post('/users/login', {
    username: 'ivan.petrov',
    password: 'password123'
  });
  return response.data;
};

// Защищённый запрос - cookie отправляется автоматически
const getProjects = async () => {
  const response = await api.get('/projects/');
  return response.data;
};
```

### React + Axios

```javascript
import axios from 'axios';
import { useState, useEffect } from 'react';

const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  withCredentials: true
});

function App() {
  const [user, setUser] = useState(null);

  const login = async () => {
    const response = await api.post('/users/login', {
      username: 'ivan.petrov',
      password: 'password123'
    });
    setUser(response.data);
  };

  const logout = async () => {
    await api.post('/users/logout');
    setUser(null);
  };

  const fetchProjects = async () => {
    const response = await api.get('/projects/');
    return response.data;
  };

  return (
    <div>
      {user ? (
        <button onClick={logout}>Выйти</button>
      ) : (
        <button onClick={login}>Войти</button>
      )}
    </div>
  );
}
```

---

## 🧪 Тестирование

### Через Swagger

1. Откройте `http://localhost:8000/docs`
2. Выполните `POST /api/users/login`
3. Cookie устанавливается автоматически!
4. Выполняйте защищённые запросы без заголовка `X-Session-Key`

### Через cURL

```bash
# Логин - cookie сохраняется в файл
curl -c cookies.txt -X POST "http://localhost:8000/api/users/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"ivan.petrov","password":"password123"}'

# Защищённый запрос - cookie отправляется из файла
curl -b cookies.txt "http://localhost:8000/api/projects/"

# Logout - cookie удаляется
curl -b cookies.txt -c cookies.txt -X POST "http://localhost:8000/api/users/logout"
```

### Через браузер

1. Откройте DevTools (F12)
2. Перейдите в вкладку **Application** → **Cookies**
3. Выполните логин
4. Увидите cookie `session_key`

---

## 🔒 Безопасность

### Защита от XSS

```python
httponly=True  # Cookie недоступен через JavaScript
```

### Защита от CSRF

```python
samesite="lax"  # Cookie не отправляется с cross-site запросами
```

### Защита от перехвата (production)

```python
secure=True  # Cookie отправляется только по HTTPS
```

### Хеширование паролей

Пароли хешируются через SHA-256 перед сохранением в БД.

---

## 🚀 Production настройки

### В `app/routers/users.py`:

```python
# Для production
response.set_cookie(
    key="session_key",
    value=auth_session.session_key,
    httponly=True,
    secure=True,      # True для HTTPS
    samesite="strict", # Строгая защита от CSRF
    max_age=86400
)
```

### В `app/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",  # Укажите конкретные домены
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📝 Резюме

| Параметр | Было | Стало |
|----------|------|-------|
| **Хранение** | Заголовок `X-Session-Key` | HTTP-only Cookie |
| **Отправка** | Вручную в каждом запросе | Автоматически браузером |
| **Безопасность** | XSS уязвимость | `httponly=True` |
| **CSRF защита** | Нет | `samesite="lax"` |
| **Обратная совместимость** | - | Заголовок всё ещё работает |

**Преимущества cookies:**
- ✅ Автоматическая отправка браузером
- ✅ Защита от XSS (httponly)
- ✅ Защита от CSRF (samesite)
- ✅ Удобнее для веб-приложений
- ✅ Обратная совместимость с заголовком
