#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Скрипт для тестирования создания проекта и документа"""

import requests
import json

BASE_URL = "http://localhost:8000"
SESSION_KEY = None

def register_user():
    """Регистрация тестового пользователя"""
    url = f"{BASE_URL}/api/users/register"
    data = {
        "username": "test.user",
        "password": "password123",
        "first_name": "Test",
        "last_name": "User"
    }
    
    response = requests.post(url, json=data)
    print(f"📝 Регистрация: {response.status_code}")
    print(response.json())
    return response.status_code == 201

def login():
    """Вход в систему"""
    global SESSION_KEY
    url = f"{BASE_URL}/api/users/login"
    data = {
        "username": "test.user",
        "password": "password123"
    }
    
    response = requests.post(url, json=data)
    print(f"\n🔐 Вход: {response.status_code}")
    
    if response.status_code == 200:
        SESSION_KEY = response.cookies.get("session_key")
        print(f"Session Key: {SESSION_KEY[:20]}...")
        return True
    else:
        print(response.json())
        return False

def create_project():
    """Создание проекта"""
    global SESSION_KEY
    url = f"{BASE_URL}/api/projects/"
    data = {
        "name": "Тестовый проект",
        "description": "Проект для тестирования"
    }
    
    headers = {"X-Session-Key": SESSION_KEY}
    response = requests.post(url, json=data, headers=headers)
    print(f"\n📁 Создание проекта: {response.status_code}")
    print(response.json())
    return response.status_code == 201, response.json().get("id") if response.status_code == 201 else None

def create_document(project_id):
    """Создание документа"""
    global SESSION_KEY
    url = f"{BASE_URL}/api/documents/"
    data = {
        "project_id": project_id,
        "name": "Тестовый документ.pdf",
        "doc_type": "specification",
        "category": "project_documentation"
    }
    
    headers = {"X-Session-Key": SESSION_KEY}
    response = requests.post(url, json=data, headers=headers)
    print(f"\n📄 Создание документа: {response.status_code}")
    print(response.json())
    return response.status_code == 201

def get_projects():
    """Получение списка проектов"""
    global SESSION_KEY
    url = f"{BASE_URL}/api/projects/"
    headers = {"X-Session-Key": SESSION_KEY}
    response = requests.get(url, headers=headers)
    print(f"\n📋 Проекты: {response.status_code}")
    print(response.json())
    return response.json()

def get_documents():
    """Получение списка документов"""
    global SESSION_KEY
    url = f"{BASE_URL}/api/documents/"
    headers = {"X-Session-Key": SESSION_KEY}
    response = requests.get(url, headers=headers)
    print(f"\n📚 Документы: {response.status_code}")
    print(response.json())
    return response.json()

def main():
    print("=" * 50)
    print("ТЕСТИРОВАНИЕ СОЗДАНИЯ ПРОЕКТА И ДОКУМЕНТА")
    print("=" * 50)
    
    # 1. Регистрация
    if not register_user():
        print("❌ Не удалось зарегистрировать пользователя")
        return
    
    # 2. Вход
    if not login():
        print("❌ Не удалось войти")
        return
    
    # 3. Получить проекты
    projects = get_projects()
    
    # 4. Создать проект
    success, project_id = create_project()
    if not success:
        print("❌ Не удалось создать проект")
        return
    
    # 5. Получить проекты после создания
    print("\n--- Проекты после создания ---")
    get_projects()
    
    # 6. Создать документ
    if project_id:
        create_document(project_id)
    
    # 7. Получить документы
    print("\n--- Документы ---")
    get_documents()
    
    print("\n✅ Тестирование завершено!")

if __name__ == "__main__":
    main()
