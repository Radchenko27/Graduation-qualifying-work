import requests
import json

BASE_URL = "http://localhost:8000"

# 1. Login
print("Login as Dimon...")
login_data = {"username": "Dimon", "password": "password123"}
response = requests.post(f"{BASE_URL}/api/users/login", json=login_data)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    session_key = response.json()["session_key"]
    print(f"Session Key: {session_key}")
    
    # 2. Test /users/me endpoint
    print("\nTesting /api/users/me...")
    headers = {"X-Session-Key": session_key}
    response = requests.get(f"{BASE_URL}/api/users/me", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    # 3. Check cookies
    print(f"\nCookies: {response.cookies.get_dict()}")
else:
    print(f"Login failed: {response.json()}")
