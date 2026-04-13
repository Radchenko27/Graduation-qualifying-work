"""
Скрипт для инициализации базы данных тестовыми данными.
Запускается внутри контейнера приложения.
"""
import sys
from pathlib import Path

# Добавляем путь к приложению
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db import get_db, engine
from app import models, crud
from datetime import date, datetime, timedelta
import random
import hashlib


def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def init_database():
    """Инициализация базы данных тестовыми данными."""
    # Создаем все таблицы
    models.Base.metadata.create_all(bind=engine)

    db = next(get_db())

    try:
        # Проверяем, есть ли уже данные
        existing_users = db.query(models.User).count()
        if existing_users > 0:
            print("База данных уже содержит данные. Пропускаем инициализацию.")
            return

        print("Создание тестовых данных...")

        # Создаем пользователей
        users_data = [
            {
                "first_name": "Иван",
                "middle_name": "Иванович",
                "last_name": "Петров",
                "username": "ivan.petrov",
                "password_hash": hash_password("password123"),
                "phone": "+79001234567",
                "email": "ivan.petrov@example.com"
            },
            {
                "first_name": "Мария",
                "middle_name": "Сергеевна",
                "last_name": "Сидорова",
                "username": "maria.sidorova",
                "password_hash": hash_password("password123"),
                "phone": "+79007654321",
                "email": "maria.sidorova@example.com"
            },
            {
                "first_name": "Алексей",
                "middle_name": None,
                "last_name": "Козлов",
                "username": "alexey.kozlov",
                "password_hash": hash_password("password123"),
                "phone": "+79001112233",
                "email": "alexey.kozlov@example.com"
            }
        ]

        users = []
        for user_data in users_data:
            user = crud.Users.create(db, user_data)
            users.append(user)
            print(f"  Создан пользователь: {user.username}")

        # Создаем проекты
        projects_data = [
            {
                "name": "ЖК Солнечный",
                "description": "Жилой комплекс бизнес-класса",
                "address": "г. Москва, ул. Солнечная, 1",
                "work_scope": "Строительство 5 жилых домов",
                "start_date": date(2024, 1, 1),
                "end_date": date(2026, 12, 31)
            },
            {
                "name": "БЦ Технопарк",
                "description": "Бизнес-центр класса А+",
                "address": "г. Москва, Технопарк, д. 5",
                "work_scope": "Строительство офисного центра",
                "start_date": date(2024, 6, 1),
                "end_date": date(2025, 12, 31)
            },
            {
                "name": "Школа №123",
                "description": "Реконструкция школы",
                "address": "г. Москва, ул. Школьная, 123",
                "work_scope": "Капитальный ремонт",
                "start_date": date(2024, 3, 1),
                "end_date": date(2024, 12, 31)
            }
        ]

        projects = []
        for project_data in projects_data:
            project = crud.Projects.create(db, project_data)
            projects.append(project)
            print(f"  Создан проект: {project.name}")

        # Создаем документы для проектов
        documents_data = []
        for project in projects:
            for i in range(1, 4):
                doc_data = {
                    "project_id": project.id,
                    "doc_type": random.choice(["Чертеж", "Спецификация", "Смета", "Акт"]),
                    "name": f"Документ {i} для {project.name}",
                    "created_at": date.today() - timedelta(days=random.randint(1, 100)),
                    "file_path": f"/uploads/{project.name.replace(' ', '_')}_doc_{i}.pdf",
                    "file_hash": f"hash_{random.randint(1000, 9999)}"
                }
                doc = crud.Documents.create(db, doc_data)
                documents_data.append(doc)
                print(f"    Создан документ: {doc.name}")

        # Создаем чертежи
        for doc in documents_data:
            for i in range(1, 4):
                drawing_data = {
                    "document_id": doc.id,
                    "project_id": doc.project_id,
                    "number": f"ЧТ-{doc.project_id}-{i:03d}",
                    "name": f"Чертеж {i}",
                    "type": random.choice(["Архитектурный", "Конструктивный", "Инженерный"]),
                    "scale": random.choice(["1:100", "1:200", "1:500"]),
                    "area": round(random.uniform(50, 500), 2),
                    "page_number": i
                }
                drawing = crud.Drawings.create(db, drawing_data)
                print(f"      Создан чертеж: {drawing.number}")

        # Создаем материалы
        materials_data = [
            {"name": "Бетон М300", "description": "Бетон марки 300", "unit": "м³", "cost": 4500.0},
            {"name": "Арматура Ø12", "description": "Арматурная сталь 12мм", "unit": "т", "cost": 55000.0},
            {"name": "Кирпич керамический", "description": "Кирпич красный", "unit": "шт", "cost": 12.0},
            {"name": "Песок", "description": "Песок строительный", "unit": "м³", "cost": 800.0},
            {"name": "Цемент М500", "description": "Цемент марки 500", "unit": "т", "cost": 6500.0},
            {"name": "Гипсокартон", "description": "Лист гипсокартона 12.5мм", "unit": "м²", "cost": 350.0},
            {"name": "Утеплитель", "description": "Минвата 100мм", "unit": "м²", "cost": 450.0},
            {"name": "Краска фасадная", "description": "Акриловая краска", "unit": "кг", "cost": 280.0}
        ]

        materials = []
        for material_data in materials_data:
            material = crud.Materials.create(db, material_data)
            materials.append(material)
            print(f"  Создан материал: {material.name}")

        # Создаем связи материалы-чертежи
        for doc in documents_data:
            for material in random.sample(materials, random.randint(2, 5)):
                material_drawing_data = {
                    "material_id": material.id,
                    "document_id": doc.id,
                    "drawing_id": doc.drawings[0].id if doc.drawings else None,
                    "project_id": doc.project_id,
                    "quantity": round(random.uniform(1, 100), 2)
                }
                crud.MaterialDrawings.create(db, material_drawing_data)

        print("  Созданы связи материалы-чертежи")

        # Создаем отчёты
        for project in projects:
            for i in range(1, 3):
                report_data = {
                    "project_id": project.id,
                    "name": f"Отчёт {i} - {project.name}",
                    "description": f"Ежемесячный отчёт по строительству",
                    "created_at": date.today() - timedelta(days=random.randint(1, 60)),
                    "file_path": f"/reports/{project.name.replace(' ', '_')}_report_{i}.pdf"
                }
                crud.Reports.create(db, report_data)
                print(f"    Создан отчёт: {report_data['name']}")

        # Создаем связи пользователи-проекты
        access_rights = ["read", "write", "admin"]
        for project in projects:
            for user in random.sample(users, random.randint(1, len(users))):
                project_user_data = {
                    "user_id": user.id,
                    "project_id": project.id,
                    "access_rights": random.choice(access_rights),
                    "created_at": date.today() - timedelta(days=random.randint(1, 100))
                }
                crud.ProjectUsers.create(db, project_user_data)

        print("  Созданы связи пользователи-проекты")

        # Создаем сессии авторизации для тестирования
        for user in users:
            auth_session_data = {
                "user_id": user.id,
                "session_key": f"session_key_{user.username}",
                "expires_at": datetime.now() + timedelta(days=30),
                "created_at": datetime.now()
            }
            crud.AuthSessions.create(db, auth_session_data)
            print(f"  Создана сессия для пользователя: {user.username}")

        print("\nИнициализация базы данных завершена успешно!")
        print("\nТестовые пользователи:")
        print("  Username: ivan.petrov, Password: password123, Session Key: session_key_ivan.petrov")
        print("  Username: maria.sidorova, Password: password123, Session Key: session_key_maria.sidorova")
        print("  Username: alexey.kozlov, Password: password123, Session Key: session_key_alexey.kozlov")

    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    init_database()
