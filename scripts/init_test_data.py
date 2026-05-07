#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Инициализация тестовых данных в базе данных"""

import sys
from pathlib import Path

# Добавляем корень проекта в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.orm import Session
from app.db import SessionLocal, engine
from app.models import Base, User, Project, ProjectUser
import hashlib

def create_test_data():
    """Создание тестовых данных"""
    
    # Создаём таблицы если их нет
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    
    try:
        # 1. Создаём тестового пользователя
        print("1. Создание тестового пользователя...")
        
        existing_user = db.query(User).filter(User.username == "test.user").first()
        if existing_user:
            print(f"   ⚠️  Пользователь 'test.user' уже существует (ID: {existing_user.id})")
            user = existing_user
        else:
            password_hash = hashlib.sha256("password123".encode()).hexdigest()
            user = User(
                username="test.user",
                password_hash=password_hash,
                first_name="Test",
                last_name="User"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print(f"   ✅ Пользователь создан: ID={user.id}")
        
        # 2. Создаём тестовый проект
        print("\n2. Создание тестового проекта...")
        
        existing_project = db.query(Project).filter(Project.name == "Тестовый проект").first()
        if existing_project:
            print(f"   ⚠️  Проект уже существует (ID: {existing_project.id})")
            project = existing_project
        else:
            project = Project(
                name="Тестовый проект",
                description="Проект для тестирования системы",
                owner_id=user.id
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            print(f"   ✅ Проект создан: ID={project.id}")
        
        # 3. Добавляем пользователя как участника проекта
        print("\n3. Добавление участника в проект...")
        
        existing_member = db.query(ProjectUser).filter(
            ProjectUser.user_id == user.id,
            ProjectUser.project_id == project.id
        ).first()
        
        if existing_member:
            print(f"   ⚠️  Пользователь уже участник проекта")
        else:
            project_user = ProjectUser(
                user_id=user.id,
                project_id=project.id,
                access_rights="admin",
                created_at="2025-01-01"
            )
            db.add(project_user)
            db.commit()
            print(f"   ✅ Пользователь добавлен как участник")
        
        # 4. Выводим итоговую информацию
        print("\n" + "="*50)
        print("📊 ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ")
        print("="*50)
        print(f"\n👤 Пользователь:")
        print(f"   Username: test.user")
        print(f"   Password: password123")
        print(f"   ID: {user.id}")
        
        print(f"\n📁 Проект:")
        print(f"   Name: Тестовый проект")
        print(f"   ID: {project.id}")
        print(f"   Owner: test.user")
        
        print("\n🔐 Логин через API:")
        print(f"   POST http://localhost:8000/api/users/login")
        print(f"   {{\"username\": \"test.user\", \"password\": \"password123\"}}")
        
        print("\n✅ Готово!")
        
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    create_test_data()
