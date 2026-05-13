# 📖 Руководство: Использование парсера спецификаций в интерфейсе

## 🎯 Обзор

Парсер спецификаций интегрирован в веб-интерфейс приложения. Вы можете извлекать спецификации из классифицированных документов прямо из браузера.

---

## 🚀 Быстрый старт

### 1. Страница документа (`/documents/{id}`)

На странице просмотра документа есть кнопка **📋 Спецификации** в правом верхнем углу.

![Кнопка спецификаций](https://via.placeholder.com/800x200?text=Кнопка+Спецификации+на+странице+документа)

### 2. Список документов (`/documents`)

В таблице документов есть кнопка **📋 Спецификации** для быстрого парсинга.

![Кнопка спецификаций в списке](https://via.placeholder.com/800x200?text=Кнопка+Спецификации+в+списке+документов)

---

## 📋 Пошаговое использование

### Способ 1: Через страницу документа

#### Шаг 1: Откройте документ

Перейдите на страницу документа:
- Из списка документов: нажмите кнопку **👁 Открыть**
- Или напрямую: `/documents/{id}`

#### Шаг 2: Нажмите кнопку "Спецификации"

В правом верхнем углу страницы нажмите кнопку **📋 Спецификации**.

#### Шаг 3: Просмотрите сводную информацию

Откроется панель со сведениями о спецификациях:

```
📋 Спецификации

Найдено спецификаций
3 страниц со спецификациями

[Страниц: 3] [Формат: JSON / Excel]

Страницы со спецификациями:
[Стр. 2 (85%)] [Стр. 5 (92%)] [Стр. 8 (78%)]
```

#### Шаг 4: Экспортируйте спецификации

Выберите формат экспорта:
- **📄 Экспорт в JSON** — для программной обработки
- **📊 Экспорт в Excel** — для редактирования в Excel

После успешного экспорта:

```
✅ Успешно!

Спецификации экспортированы в Excel

Путь к файлу:
output/specifications/Спецификация_specifications.xlsx

[🔄 Вернуться к спецификациям] [✕ Закрыть]
```

---

### Способ 2: Через список документов

#### Шаг 1: Откройте список документов

Перейдите на `/documents`

#### Шаг 2: Нажмите кнопку "Спецификации"

В строке нужного документа нажмите кнопку **📋 Спецификации**.

#### Шаг 3: Подтвердите действие

Появится диалоговое окно:

```
Парсинг спецификаций документа:

Спецификация оборудования.pdf

Экспортировать спецификации в Excel?

[Отмена] [OK]
```

#### Шаг 4: Результат

После успешного парсинга:

```
✅ Спецификации экспортированы:
output/specifications/Спецификация_specifications.xlsx

Открыть страницу документа для просмотра деталей?
[OK] [Отмена]
```

---

## 📊 Форматы экспорта

### JSON

**Когда использовать:**
- Для программной обработки
- Для интеграции с другими системами
- Для хранения данных

**Структура:**
```json
{
  "document_id": 1,
  "document_name": "Спецификация.pdf",
  "project_id": 1,
  "exported_at": "2025-01-15T10:30:00",
  "specification_pages": 3,
  "specifications": [
    {
      "page_number": 2,
      "confidence": 0.85,
      "header": "Спецификация оборудования",
      "columns": ["position", "name", "quantity", "unit"],
      "rows": [
        {"position": "1", "name": "Кабель ВВГнг", "quantity": 100, "unit": "м"}
      ],
      "row_count": 1
    }
  ],
  "summary": {
    "total_tables": 3,
    "total_rows": 45
  }
}
```

### Excel

**Когда использовать:**
- Для ручного редактирования
- Для анализа в Excel
- Для передачи заказчикам

**Структура файла:**

1. **Лист "Сводка"** — общая информация:
   - Документ
   - ID документа
   - ID проекта
   - Страниц со спецификациями
   - Всего таблиц
   - Всего строк
   - Экспортировано

2. **Листы "Спецификация_стрN"** — каждая таблица на отдельном листе

3. **Лист "Все_спецификации"** — объединённая таблица всех спецификаций:
   - position
   - designation
   - name
   - quantity
   - unit
   - note
   - page_number

---

## 🔧 API Endpoints

### Получить сводку спецификаций

```http
GET /api/documents/{document_id}/specification-summary
```

**Ответ:**
```json
{
  "document_id": 1,
  "document_name": "Спецификация.pdf",
  "project_id": 1,
  "specification_pages_count": 3,
  "specification_pages": [
    {
      "page_number": 2,
      "confidence": 0.85,
      "content_type": "table"
    }
  ]
}
```

### Парсинг спецификаций

```http
POST /api/documents/{document_id}/parse-specifications?format=json
```

**Параметры:**
- `format`: `json` или `excel`

**Ответ:**
```json
{
  "status": "success",
  "document_id": 1,
  "document_name": "Спецификация.pdf",
  "format": "json",
  "output_path": "output/specifications/Спецификация_specifications.json",
  "message": "Спецификации успешно экспортированы в JSON"
}
```

---

## 💻 JavaScript функции

### `showSpecificationPanel()`

Показать панель спецификаций на странице документа.

```javascript
// Показать панель спецификаций
async function showSpecificationPanel() {
    const panel = document.getElementById('specificationPanel');
    const content = document.getElementById('specificationContent');
    
    panel.style.display = 'block';
    // ... загрузка и отображение данных
}
```

### `parseSpecifications(format)`

Парсинг спецификаций в указанном формате.

```javascript
// Парсинг спецификаций
async function parseSpecifications(format) {
    try {
        const response = await fetch(
            `/api/documents/${DOCUMENT_ID}/parse-specifications?format=${format}`,
            {
                method: 'POST',
                headers: { 'X-Session-Key': localStorage.getItem('session_key') }
            }
        );
        
        const result = await response.json();
        showMessage(`Спецификации экспортированы: ${result.output_path}`, 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    }
}
```

### `quickParseSpecifications(documentId, documentName)`

Быстрый парсинг спецификаций из списка документов.

```javascript
// Быстрый парсинг спецификаций из списка документов
async function quickParseSpecifications(documentId, documentName) {
    if (!confirm(`Парсинг спецификаций документа:\n\n${documentName}\n\nЭкспортировать спецификации в Excel?`)) {
        return;
    }

    showMessage('Парсинг спецификаций...', 'info');

    try {
        const response = await fetch(
            `/api/documents/${documentId}/parse-specifications?format=excel`,
            {
                method: 'POST',
                headers: { 'X-Session-Key': localStorage.getItem('session_key') }
            }
        );

        const result = await response.json();
        showMessage(`Спецификации экспортированы:\n${result.output_path}`, 'success');
    } catch (error) {
        showMessage(error.message, 'error');
    }
}
```

---

## 🎨 Визуальные элементы

### Панель спецификаций

```html
<div id="specificationPanel" class="card">
    <div class="card-header">
        <h4>📋 Спецификации</h4>
        <button onclick="hideSpecificationPanel()">✕</button>
    </div>
    <div class="card-body">
        <div id="specificationContent">
            <!-- Содержимое панели -->
        </div>
    </div>
</div>
```

### Кнопки действий

```html
<!-- На странице документа -->
<button class="btn btn-success" onclick="showSpecificationPanel()">
    📋 Спецификации
</button>

<!-- В списке документов -->
<button class="btn btn-success btn-sm"
        onclick="quickParseSpecifications(${doc.id}, '${doc.name}')">
    📋
</button>
```

### Бейджи спецификаций

```javascript
// Отображение страниц со спецификациями
data.specification_pages.forEach(page => {
    const confidence = Math.round((page.confidence || 0) * 100);
    html += `
        <span class="badge" style="background: #ffc107; color: #000;">
            Стр. ${page.page_number} (${confidence}%)
        </span>
    `;
});
```

---

## ❓ Устранение проблем

### Проблема: "Спецификации не найдены"

**Причина:** В документе нет страниц с категорией `specification`.

**Решение:**
1. Переклассифицируйте документ (кнопка **🔄 Переклассифицировать**)
2. Проверьте результаты классификации (кнопка **🔄 Страницы**)

### Проблема: "Processed файл не найден"

**Причина:** Отсутствует обработанный JSON файл в директории `processed/`.

**Решение:**
1. Убедитесь, что документ был обработан через `pdf_processor`
2. Проверьте наличие файла в `processed/`

### Проблема: "Ошибка парсинга спецификаций"

**Причины:**
- Неверный формат документа
- Нет распознанных таблиц на страницах
- Проблемы с доступом к файлам

**Решение:**
1. Проверьте логи на сервере
2. Убедитесь, что документ является PDF
3. Переклассифицируйте документ

---

## 📚 Связанная документация

- [Полное руководство по парсеру](SPECIFICATION_PARSER_GUIDE.md)
- [Резюме реализации](SPECIFICATION_PARSER_SUMMARY.md)
- [Примеры использования](../examples/specification_parser_example.py)

---

## 🔄 Рабочий процесс

```
1. Загрузка документа
   ↓
2. Автоматическая классификация страниц
   ↓
3. Проверка результатов классификации
   ↓
4. Нажмите "📋 Спецификации"
   ↓
5. Просмотр сводной информации
   ↓
6. Выбор формата экспорта (JSON/Excel)
   ↓
7. Получение файла для редактирования
```

---

**Дата создания:** 2025-01-15
**Версия:** 1.0