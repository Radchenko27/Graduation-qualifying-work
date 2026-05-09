import requests

BASE_URL = "http://localhost:8000"

# 1. Login
print("Login...")
login_data = {"username": "test.user", "password": "password123"}
response = requests.post(f"{BASE_URL}/api/users/login", json=login_data)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    session_key = response.cookies.get("session_key")
    print(f"Session Key: {session_key[:20]}...")
    
    # 2. Create document
    print("\nCreate document...")
    doc_data = {
        "project_id": 1,
        "name": "Тестовый документ.pdf",
        "doc_type": "specification",
        "category": "project_documentation"
    }
    
    headers = {"X-Session-Key": session_key}
    response = requests.post(f"{BASE_URL}/api/documents/", json=doc_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
else:
    print(f"Login failed: {response.json()}")
