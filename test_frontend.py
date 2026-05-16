#!/usr/bin/env python
"""Test frontend endpoint"""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8000"

# Логин
r = requests.post(f"{BASE_URL}/api/users/login", json={
    "username": "admin",
    "password": "admin"
})
if r.status_code != 200:
    print(f"Login failed: {r.text}")
    sys.exit(1)

session_key = r.json().get('session_key')
cookies = {'session_key': session_key}
print(f"Logged in, session: {session_key[:20]}...")

# GET /projects/6
print("\nGET /projects/6")
r = requests.get(f"{BASE_URL}/projects/6", cookies=cookies, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    print("OK - page loaded")
else:
    print(f"Error: {r.text[:300]}")
