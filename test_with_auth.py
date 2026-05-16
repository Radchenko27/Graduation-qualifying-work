#!/usr/bin/env python
"""Test API с авторизацией"""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8000"

def test_with_login():
    # Логин
    print("Logging in...")
    r = requests.post(f"{BASE_URL}/api/users/login", json={
        "username": "admin",
        "password": "admin"
    })
    print(f"Login status: {r.status_code}")
    
    if r.status_code != 200:
        print(f"Login failed: {r.text}")
        return
    
    session_key = r.json().get('session_key')
    headers = {'X-Session-Key': session_key}
    print(f"Got session key: {session_key[:20]}...")
    
    # GET /api/projects/
    print("\nGET /api/projects/")
    r = requests.get(f"{BASE_URL}/api/projects/", headers=headers)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        projects = r.json()
        print(f"Projects count: {len(projects)}")
        for p in projects[:3]:
            print(f"  - {p['id']}: {p['name']}")
    else:
        print(f"Error: {r.text}")
    
    # GET /api/projects/9
    print("\nGET /api/projects/9")
    r = requests.get(f"{BASE_URL}/api/projects/9", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:300]}")
    
    # DELETE /api/projects/9 (без фактического удаления)
    print("\nDELETE /api/projects/9")
    r = requests.delete(f"{BASE_URL}/api/projects/9", headers=headers)
    print(f"Status: {r.status_code}")
    print(f"Body: {r.text[:300]}")

if __name__ == '__main__':
    test_with_login()
