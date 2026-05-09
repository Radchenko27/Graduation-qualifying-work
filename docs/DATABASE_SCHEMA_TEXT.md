# Схема базы данных (текстовая версия)

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CONSTRUCTION DB SCHEMA                              │
└─────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│      USERS       │         │   AUTH_SESSION   │         │     PROJECTS     │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄───────│ id (PK)          │         │ id (PK)          │
│ first_name       │         │ user_id (FK)     │         │ owner_id (FK)────┤
│ middle_name      │         │ session_key (UK) │         │ name             │
│ last_name        │         │ created_at       │         │ description      │
│ username (UK)    │         │ expires_at       │         │ address          │
│ password_hash    │         └──────────────────┘         │ work_scope       │
│ phone            │                                      │ start_date       │
│ email            │                                      │ end_date         │
│ photo_url        │                                      └──────────────────┘
└──────────────────┘                                             │
       │                                                         │
       │ 1:N                      ┌──────────────────┐           │ 1:N
       │                          │  PROJECT_USERS   │           │
       └─────────────────────────►│├──────────────────┤           │
                                  ││ id (PK)          │           │
                                  ││ user_id (FK)     │◄──────────┘
                                  ││ project_id (FK)  │
                                  ││ access_rights    │
                                  ││ created_at       │
                                  └──────────────────┘
                                         │
                                         │ N:N
                                         │
                                  ┌──────────────────┐
                                  │ PROJECT_SHARES   │
                                  ├──────────────────┤
                                  │ id (PK)          │
                                  │ project_id (FK)  │
                                  │ owner_id (FK)    │
                                  │ shared_with (FK) │
                                  │ access_level     │
                                  │ shared_at        │
                                  └──────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│    DOCUMENTS     │         │     DRAWINGS     │         │ DRAWING_CALC     │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄───────│ id (PK)          │         │ id (PK)          │
│ project_id (FK)  │        │ document_id (FK) │────┬────│ drawing_id (FK)──┤
│ doc_type         │        │ project_id (FK)  │    │    │ project_id (FK)  │
│ category (3.1.1) │        │ number           │    │    │ element_name     │
│ created_at       │        │ name             │    │    │ element_type     │
│ name             │        │ type             │    │    │ quantity         │
│ file_path        │        │ scale            │    │    │ unit             │
│ file_hash        │        │ area             │    │    │ calculation_res  │
│ page_count       │        │ page_number(3.1.5)│   │    │ created_at       │
└──────────────────┘        └──────────────────┘    │    └──────────────────┘
       │                                             │           │
       │ 1:N                                 1:N     │           │ 1:N
       │                                             │           │
       └─────────────────────────────────────────────┘           │
                                                                 │
                                  ┌──────────────────┐           │
                                  │  MATERIALS       │           │
                                  ├──────────────────┤           │
                                  │ id (PK)          │           │
                                  │ type             │           │
                                  │ name             │           │
                                  │ price            │           │
                                  │ mark             │           │
                                  └──────────────────┘           │
                                         │                       │
                                         │ N:1                    │
                                         │                       │
                                  ┌──────────────────┐           │
                                  │  MATERIAL_DRAW   │◄──────────┘
                                  ├──────────────────┤
                                  │ id (PK)          │
                                  │ material_id (FK) │
                                  │ document_id (FK) │
                                  │ drawing_id (FK)  │
                                  │ project_id (FK)  │
                                  │ qty_on_drawing   │
                                  │ cost_on_drawing  │
                                  └──────────────────┘

┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│     ESTIMATES    │         │   ESTIMATE_ITEM  │         │     REPORTS      │
├──────────────────┤         ├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄───────│ id (PK)          │         │ id (PK)          │
│ project_id (FK)  │        │ estimate_id (FK) │────┬────│ material_draw_id │
│ name             │        │ calc_id (FK)─────┘    │    │ material_id (FK) │
│ description      │        │ quantity             │    │ drawing_id (FK)  │
│ total_cost       │        │ unit_cost            │    │ document_id (FK) │
│ total_quantity   │        │ total_cost           │    │ project_id (FK)  │
│ created_at       │        └──────────────────┘    │    │ view             │
│ updated_at       │                                │    │ total_cost       │
└──────────────────┘                                │    │ total_quantity   │
       │                                            │    └──────────────────┘
       │ 1:N                                        │
       └────────────────────────────────────────────┘

Legend:
───────►  Foreign Key relationship
   1:N   One-to-Many
   N:1   Many-to-One
   N:N   Many-to-Many (through junction table)
   (PK)  Primary Key
   (FK)  Foreign Key
   (UK)  Unique Key
   (3.1.x) Reference to Technical Specification section
```

---

## Краткое описание таблиц

### Основные сущности

| Таблица | Назначение | Функции ТЗ |
|---------|------------|------------|
| **users** | Пользователи системы | - |
| **projects** | Проекты | - |
| **documents** | Документы (PDF, спецификации) | 3.1.1 |
| **drawings** | Чертежи | 3.1.5 |
| **materials** | Материалы и оборудование | 3.1.2, 3.1.3 |

### Связующие таблицы

| Таблица | Назначение |
|---------|------------|
| **project_users** | Участники проектов (права доступа) |
| **project_shares** | Совместный доступ к проектам |
| **material_drawings** | Материалы в чертежах |

### Расчёты и сметы

| Таблица | Назначение | Функции ТЗ |
|---------|------------|------------|
| **drawing_calculations** | Расчёты элементов чертежа | 3.1.3, 3.1.4 |
| **estimates** | Сметы | 3.1.2, 3.1.6 |
| **estimate_items** | Элементы сметы | 3.1.6 |
| **reports** | Отчёты | - |

### Аутентификация

| Таблица | Назначение |
|---------|------------|
| **auth_sessions** | Сессии пользователей (cookie) |

---

## Диаграмма данных

```
USER
  │
  ├─► PROJECT (владелец)
  │     │
  │     ├─► DOCUMENT ───► DRAWING ───► DRAWING_CALCULATION
  │     │     │             │              │
  │     │     │             │              └─────────────┐
  │     │     │             │                            │
  │     │     │             └──────────┐                 │
  │     │     │                        │                 │
  │     │     └──────────┐             │                 │
  │     │                │             │                 │
  │     └────────┐       │             │                 │
  │              │       │             │                 │
  └──────────────┼───────┼─────────────┼─────────────────┤
                 │       │             │                 │
                 ▼       ▼             ▼                 ▼
            MATERIAL  MATERIAL_DRAW  ESTIMATE  ESTIMATE_ITEM
                 │       │             │             ▲
                 │       │             │             │
                 └───────┴─────────────┴─────────────┘
                           (REPORT)
```

---

## Поддержка функций ТЗ 3.1

### 3.1.1 Классификация документации
```sql
-- Добавлено поле category в documents
ALTER TABLE documents ADD COLUMN category VARCHAR(100);

-- Пример категорий:
-- 'specification' - спецификация
-- 'drawing' - чертёж
-- 'estimate' - смета
-- 'explanatory_note' - пояснительная записка
```

### 3.1.2 Составление сметы
```sql
-- Таблицы: estimates, estimate_items, materials
-- materials.price хранит стоимость единицы
-- estimate_items.total_cost = quantity * unit_cost
-- estimates.total_cost суммирует все элементы
```

### 3.1.3 Выбор элементов чертежа
```sql
-- drawing_calculations.element_type классифицирует элементы
-- drawing_calculations.quantity хранит количество
```

### 3.1.4 Получение расчёта
```sql
-- drawing_calculations.calculation_result хранит формулу/результат
-- Можно получить расчёт по ID чертежа
```

### 3.1.5 Выбор страницы чертежа
```sql
-- drawings.page_number указывает на страницу в PDF
-- Связь с PDF просмотрщиком
```

### 3.1.6 Объединение смет
```sql
-- estimate_items ссылается на drawing_calculations
-- Можно объединять элементы из разных смет
-- estimates.total_cost пересчитывается при объединении
```

---

## Статистика базы данных

```sql
-- Количество таблиц
SELECT COUNT(*) FROM information_schema.tables 
WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
-- Результат: 13 таблиц

-- Количество записей в каждой таблице
SELECT 'users' as table_name, COUNT(*) as count FROM users
UNION ALL SELECT 'projects', COUNT(*) FROM projects
UNION ALL SELECT 'documents', COUNT(*) FROM documents
UNION ALL SELECT 'drawings', COUNT(*) FROM drawings
UNION ALL SELECT 'materials', COUNT(*) FROM materials
UNION ALL SELECT 'estimates', COUNT(*) FROM estimates
UNION ALL SELECT 'drawing_calculations', COUNT(*) FROM drawing_calculations;
```

---

## Миграции

Текущие миграции:
- `001_initial` - Initial migration for PostgreSQL
- `002_tz_features` - Add features from TZ 3.1

Проверить статус:
```bash
alembic current
# Ожидаемый результат: 002_tz_features (head)
```
