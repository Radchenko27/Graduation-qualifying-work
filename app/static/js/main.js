// API базовый URL
const API_BASE = '/api';

// Вспомогательная функция для получения токена сессии
function getSessionKey() {
    return localStorage.getItem('session_key') || document.querySelector('meta[name="session-key"]')?.content;
}

// Вспомогательная функция для установки токена сессии
function setSessionKey(key) {
    localStorage.setItem('session_key', key);
}

// Удаление токена сессии
function clearSessionKey() {
    localStorage.removeItem('session_key');
}

// Функция для выполнения API запросов
async function apiRequest(endpoint, options = {}) {
    const sessionKey = getSessionKey();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
    };
    
    if (sessionKey) {
        headers['X-Session-Key'] = sessionKey;
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Ошибка сервера' }));
        throw new Error(error.detail || 'Произошла ошибка');
    }

    return response.json();
}

// Показать сообщение
function showMessage(text, type = 'info') {
    const messagesContainer = document.querySelector('.messages') || createMessagesContainer();
    const message = document.createElement('div');
    message.className = `message ${type}`;
    message.textContent = text;
    messagesContainer.appendChild(message);
    
    setTimeout(() => message.remove(), 5000);
}

// Создать контейнер сообщений
function createMessagesContainer() {
    const container = document.createElement('div');
    container.className = 'messages';
    document.querySelector('.container').insertBefore(container, document.querySelector('.container').firstChild);
    return container;
}

// Форматирование даты
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Форматирование цены
function formatPrice(price) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB'
    }).format(price);
}

// Модальные окна
function openModal(modalId) {
    document.getElementById(modalId)?.classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId)?.classList.remove('active');
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    // Обработка форм
    document.querySelectorAll('form[data-api]').forEach(form => {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const endpoint = form.dataset.api;
            const method = form.dataset.method || 'POST';
            const data = Object.fromEntries(new FormData(form));

            try {
                const result = await apiRequest(endpoint, {
                    method,
                    body: JSON.stringify(data),
                });
                
                showMessage('Операция выполнена успешно', 'success');
                
                if (form.dataset.redirect) {
                    setTimeout(() => {
                        window.location.href = form.dataset.redirect;
                    }, 1000);
                }
            } catch (error) {
                showMessage(error.message, 'error');
            }
        });
    });

    // Обработка кнопок удаления
    document.querySelectorAll('[data-delete]').forEach(button => {
        button.addEventListener('click', async (e) => {
            e.preventDefault();
            
            if (!confirm('Вы уверены, что хотите удалить эту запись?')) return;
            
            const endpoint = button.dataset.delete;
            
            try {
                await apiRequest(endpoint, { method: 'DELETE' });
                showMessage('Запись удалена', 'success');
                
                if (button.dataset.redirect) {
                    window.location.href = button.dataset.redirect;
                } else {
                    button.closest('tr')?.remove();
                }
            } catch (error) {
                showMessage(error.message, 'error');
            }
        });
    });
});
