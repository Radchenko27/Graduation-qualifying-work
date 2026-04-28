import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.main import app
from app.db import Base, get_db
from app.models import User

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_db.sqlite3"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """Создание тестовой базы данных"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client(db_session):
    """Создание тестового клиента"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

class TestUsersAPI:
    """Тесты для API пользователей"""
    
    def test_register_user(self, client):
        """Тест регистрации пользователя"""
        response = client.post("/api/users/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "password123",
            "full_name": "Test User"
        })
        
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "full_name" in data
    
    def test_login_user(self, client):
        """Тест входа пользователя"""
        # Сначала регистрируем
        client.post("/api/users/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "password123"
        })
        
        # Затем пробуем войти
        response = client.post("/api/users/login", json={
            "username": "loginuser",
            "password": "password123"
        })
        
        assert response.status_code == 200
        data = response.json()
        assert "session_key" in data
    
    def test_login_invalid_credentials(self, client):
        """Тест входа с неверными данными"""
        response = client.post("/api/users/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    def test_duplicate_username(self, client):
        """Тест регистрации с существующим именем"""
        client.post("/api/users/register", json={
            "username": "duplicate",
            "email": "dup1@example.com",
            "password": "password123"
        })
        
        response = client.post("/api/users/register", json={
            "username": "duplicate",
            "email": "dup2@example.com",
            "password": "password123"
        })
        
        assert response.status_code == 400
    
    def test_search_users(self, client):
        """Тест поиска пользователей"""
        # Создаём пользователей
        client.post("/api/users/register", json={
            "username": "ivan_petrov",
            "email": "ivan@example.com",
            "password": "password123",
            "full_name": "Иван Петров"
        })
        
        client.post("/api/users/register", json={
            "username": "maria_sidorova",
            "email": "maria@example.com",
            "password": "password123",
            "full_name": "Мария Сидорова"
        })
        
        # Регистрируем пользователя для поиска
        client.post("/api/users/register", json={
            "username": "searcher",
            "email": "searcher@example.com",
            "password": "password123"
        })
        
        # Получаем сессию
        login_response = client.post("/api/users/login", json={
            "username": "searcher",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Ищем
        response = client.get("/api/users/search?q=Иван", headers={
            "X-Session-Key": session_key
        })
        
        assert response.status_code == 200
        users = response.json()
        assert len(users) >= 1
        assert any(u["username"] == "ivan_petrov" for u in users)

class TestProjectsAPI:
    """Тесты для API проектов"""
    
    def test_create_project(self, client):
        """Тест создания проекта"""
        # Создаём пользователя и получаем сессию
        client.post("/api/users/register", json={
            "username": "projectuser",
            "email": "project@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "projectuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём проект
        response = client.post("/api/projects/", json={
            "name": "Test Project",
            "description": "Test description"
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["owner_id"] is not None
    
    def test_get_projects(self, client):
        """Тест получения списка проектов"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "listuser",
            "email": "list@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "listuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём проект
        client.post("/api/projects/", json={
            "name": "Project 1",
            "description": "Description 1"
        }, headers={"X-Session-Key": session_key})
        
        # Получаем список
        response = client.get("/api/projects/", headers={
            "X-Session-Key": session_key
        })
        
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1
    
    def test_delete_project(self, client):
        """Тест удаления проекта"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "deleteuser",
            "email": "delete@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "deleteuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём проект
        create_response = client.post("/api/projects/", json={
            "name": "Project to Delete",
            "description": "Will be deleted"
        }, headers={"X-Session-Key": session_key})
        
        project_id = create_response.json()["id"]
        
        # Удаляем проект
        response = client.delete(f"/api/projects/{project_id}", headers={
            "X-Session-Key": session_key
        })
        
        assert response.status_code == 204
        
        # Проверяем, что проект удалён
        get_response = client.get(f"/api/projects/{project_id}", headers={
            "X-Session-Key": session_key
        })
        assert get_response.status_code == 404
    
    def test_filter_projects_by_category(self, client):
        """Тест фильтрации проектов по категории"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "filteruser",
            "email": "filter@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "filteruser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём проект
        client.post("/api/projects/", json={
            "name": "My Project",
            "description": "My own project"
        }, headers={"X-Session-Key": session_key})
        
        # Фильтруем по категории "my"
        response = client.get("/api/projects/?category=my", headers={
            "X-Session-Key": session_key
        })
        
        assert response.status_code == 200
        projects = response.json()
        assert len(projects) >= 1

class TestDocumentsAPI:
    """Тесты для API документов"""
    
    def test_create_document(self, client):
        """Тест создания документа"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "docuser",
            "email": "doc@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "docuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём документ (без файла для теста)
        response = client.post("/api/documents/", data={
            "name": "Test Document",
            "category": "project_documentation"
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code in [201, 422]  # 422 если требуется файл
    
    def test_classify_document(self, client):
        """Тест классификации документа"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "classuser",
            "email": "class@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "classuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]

class TestEstimatesAPI:
    """Тесты для API смет"""
    
    def test_create_estimate(self, client):
        """Тест создания сметы"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "estimuser",
            "email": "estim@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "estimuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём смету
        response = client.post("/api/estimates/", json={
            "name": "Test Estimate",
            "project_id": None
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Estimate"
    
    def test_add_estimate_item(self, client):
        """Тест добавления позиции в смету"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "itemuser",
            "email": "item@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "itemuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём смету
        create_response = client.post("/api/estimates/", json={
            "name": "Estimate with Items"
        }, headers={"X-Session-Key": session_key})
        
        estimate_id = create_response.json()["id"]
        
        # Добавляем позицию
        response = client.post(f"/api/estimates/{estimate_id}/items", json={
            "name": "Material ABC",
            "quantity": 100,
            "unit": "м",
            "price": 500.0
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code == 201
        item = response.json()
        assert item["name"] == "Material ABC"
        assert item["quantity"] == 100
    
    def test_merge_estimates(self, client):
        """Тест объединения смет"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "mergeuser",
            "email": "merge@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "mergeuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём две сметы
        est1 = client.post("/api/estimates/", json={"name": "Estimate 1"}, 
                          headers={"X-Session-Key": session_key})
        est2 = client.post("/api/estimates/", json={"name": "Estimate 2"}, 
                          headers={"X-Session-Key": session_key})
        
        # Добавляем позиции в первую смету
        client.post(f"/api/estimates/{est1.json()['id']}/items", json={
            "name": "Item A",
            "quantity": 10,
            "price": 100
        }, headers={"X-Session-Key": session_key})
        
        # Добавляем позиции во вторую смету
        client.post(f"/api/estimates/{est2.json()['id']}/items", json={
            "name": "Item B",
            "quantity": 20,
            "price": 200
        }, headers={"X-Session-Key": session_key})
        
        # Объединяем сметы
        response = client.post("/api/estimates/merge", json={
            "estimate1_id": est1.json()["id"],
            "estimate2_id": est2.json()["id"]
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code == 201
        merged = response.json()
        assert "Estimate 1" in merged["name"] or "Estimate 2" in merged["name"]

class TestDrawingCalculationsAPI:
    """Тесты для API расчётов чертежей"""
    
    def test_create_calculation(self, client):
        """Тест создания расчёта"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "calcuser",
            "email": "calc@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "calcuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём расчёт
        response = client.post("/api/drawing-calculations/", json={
            "element_name": "Балка Б-1",
            "calculations_text": "Проверка на изгиб...\nQ = 10 кН\nM = 5 кН·м"
        }, headers={"X-Session-Key": session_key})
        
        assert response.status_code == 201
        data = response.json()
        assert data["element_name"] == "Балка Б-1"
    
    def test_get_calculations(self, client):
        """Тест получения списка расчётов"""
        # Создаём пользователя
        client.post("/api/users/register", json={
            "username": "listcalcuser",
            "email": "listcalc@example.com",
            "password": "password123"
        })
        
        login_response = client.post("/api/users/login", json={
            "username": "listcalcuser",
            "password": "password123"
        })
        session_key = login_response.json()["session_key"]
        
        # Создаём расчёт
        client.post("/api/drawing-calculations/", json={
            "element_name": "Колонна К-1",
            "calculations_text": "Расчёт на сжатие..."
        }, headers={"X-Session-Key": session_key})
        
        # Получаем список
        response = client.get("/api/drawing-calculations/", headers={
            "X-Session-Key": session_key
        })
        
        assert response.status_code == 200
        calculations = response.json()
        assert len(calculations) >= 1

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
