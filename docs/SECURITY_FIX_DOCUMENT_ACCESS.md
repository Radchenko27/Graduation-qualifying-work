# Исправление безопасности: Привязка документов к проектам

## Проблема

Документы могли быть прикреплены к **любым проектам**, включая чужие, без проверки прав доступа пользователя.

### Уязвимость

```python
# Было (НЕБЕЗОПАСНО):
def create_document(document: schemas.DocumentCreate, current_user, db):
    project = crud.Projects.get(db, document.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    
    # ❌ Нет проверки прав доступа!
    return crud.Documents.create(db, document_data)
```

**Результат:** Любой авторизованный пользователь мог создать документ для любого проекта, если знал его ID.

---

## Решение

### 1. Добавлена проверка прав доступа в API

```python
# Стало (БЕЗОПАСНО):
def create_document(document: schemas.DocumentCreate, current_user, db):
    project = crud.Projects.get(db, document.project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    
    # ✅ Проверка прав доступа
    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(403, "Нет доступа к проекту")
    
    return crud.Documents.create(db, document_data)
```

### 2. Создан CRUD для управления правами доступа

**Файл:** `app/crud.py`

```python
class ProjectUserCRUD(CRUDBase[models.ProjectUser]):
    def check_access(self, db: Session, user_id: int, project_id: int) -> bool:
        """Проверить доступ пользователя к проекту"""
        return db.query(models.ProjectUser).filter(
            models.ProjectUser.user_id == user_id,
            models.ProjectUser.project_id == project_id
        ).first() is not None
    
    def get_user_projects(self, db: Session, user_id: int) -> List[models.Project]:
        """Получить все проекты пользователя (включая общие)"""
        # Проекты, где пользователь является участником
        user_projects = db.query(models.Project).join(
            models.ProjectUser, models.Project.id == models.ProjectUser.project_id
        ).filter(
            models.ProjectUser.user_id == user_id
        ).all()
        
        # Проекты, доступные через sharing
        shared_projects = db.query(models.Project).join(
            models.ProjectShare, models.Project.id == models.ProjectShare.project_id
        ).filter(
            models.ProjectShare.shared_with_id == user_id
        ).all()
        
        # Объединяем и убираем дубликаты
        all_projects = {p.id: p for p in user_projects + shared_projects}
        return list(all_projects.values())
```

### 3. Обновлён endpoint получения списка документов

**Файл:** `app/routers/api/documents.py`

```python
@router.get("/", response_model=List[schemas.DocumentRead])
def read_documents(project_id=None, current_user, db):
    if project_id:
        # Проверка доступа к конкретному проекту
        if not crud.ProjectUsers.check_access(db, current_user.id, project_id):
            raise HTTPException(403, "Нет доступа к проекту")
        
        documents = crud.Documents.get_by_project(db, project_id=project_id)
    else:
        # Получаем документы только проектов пользователя
        user_projects = crud.ProjectUsers.get_user_projects(db, current_user.id)
        project_ids = [p.id for p in user_projects]
        
        documents = db.query(models.Document).filter(
            models.Document.project_id.in_(project_ids)
        ).all()
    
    return documents
```

### 4. Обновлён UI

**Файл:** `app/templates/documents.html`

Теперь при загрузке страницы:
1. Загружаются **только проекты пользователя** через API
2. В выпадающем списке "Проект" отображаются только доступные проекты
3. Нельзя выбрать проект, к которому нет доступа

```javascript
async function loadProjects() {
    const response = await fetch('/api/projects/', {
        headers: { 'X-Session-Key': localStorage.getItem('session_key') }
    });
    
    const projects = await response.json();
    populateProjectSelects(projects); // Заполняем только доступными проектами
}
```

---

## Изменённые файлы

| Файл | Изменения |
|------|-----------|
| `app/crud.py` | Добавлен класс `ProjectUserCRUD` с методами `check_access()` и `get_user_projects()` |
| `app/routers/api/documents.py` | Добавлена проверка прав доступа в `create_document()` и `read_documents()` |
| `app/templates/documents.html` | Загрузка только проектов пользователя, заполнение селекта доступными проектами |

---

## Тестирование

### Сценарий 1: Пользователь создаёт документ для своего проекта

```bash
# 1. Пользователь ivan.petrov создаёт проект
POST /api/projects/
{
  "name": "Мой проект"
}
# → project_id = 1

# 2. ivan.petrov загружает документ для своего проекта
POST /api/documents/
{
  "project_id": 1,
  "name": "Спецификация.pdf",
  "category": "project_documentation"
}
# → ✅ Успех: документ создан
```

### Сценарий 2: Пользователь пытается создать документ для чужого проекта

```bash
# Пользователь maria.sidorova (не владелец проекта 1) пытается создать документ
POST /api/documents/
{
  "project_id": 1,  # Чужой проект
  "name": "Спецификация.pdf"
}
# → ❌ Ошибка: 403 Forbidden - "Нет доступа к проекту"
```

### Сценарий 3: Пользователь получает список документов

```bash
# Пользователь ivan.petrov получает документы
GET /api/documents/
# → ✅ Возвращает документы только проектов ivan.petrov

# Пользователь maria.sidorova получает документы
GET /api/documents/
# → ✅ Возвращает документы только проектов maria.sidorova
```

---

## Уровни доступа

| Уровни | Описание |
|--------|----------|
| **Владелец** | Создал проект (`projects.owner_id`) |
| **Участник** | Добавлен через `project_users` |
| **Общий доступ** | Предоставлен через `project_shares` |

Все три уровня имеют право:
- ✅ Создавать документы
- ✅ Просматривать документы
- ✅ Редактировать документы
- ✅ Удалять свои документы

---

## Безопасность

### Что защищено:

1. **Создание документов** - только для проектов, к которым есть доступ
2. **Чтение документов** - только документы проектов пользователя
3. **UI выбор проекта** - только доступные проекты в списке

### Что ещё нужно защитить (в планах):

1. **Редактирование документов** - проверить доступ перед обновлением
2. **Удаление документов** - проверить доступ перед удалением
3. **Загрузка файлов** - проверить доступ к проекту перед загрузкой в MinIO
4. **Скачивание файлов** - проверить доступ перед отдачей файла

---

## Примечания

- Права доступа проверяются на уровне **базы данных** через Foreign Key
- Доступ к проекту определяется через таблицы:
  - `project_users` - участники проекта
  - `project_shares` - общий доступ
- При удалении проекта автоматически удаляются все документы (CASCADE)
- При удалении пользователя удаляются все его проекты и документы
