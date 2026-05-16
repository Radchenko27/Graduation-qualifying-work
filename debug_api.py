#!/usr/bin/env python
"""Debug API проектов"""
import sys
sys.path.insert(0, '.')

import requests

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    print("=" * 60)
    print("Testing Projects API")
    print("=" * 60)
    
    # 1. GET /api/projects/
    print("\n1. GET /api/projects/")
    try:
        r = requests.get(f"{BASE_URL}/api/projects/", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Body: {r.text[:300]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 2. GET /api/projects/9
    print("\n2. GET /api/projects/9")
    try:
        r = requests.get(f"{BASE_URL}/api/projects/9", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Body: {r.text[:300]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # 3. DELETE /api/projects/9
    print("\n3. DELETE /api/projects/9")
    try:
        r = requests.delete(f"{BASE_URL}/api/projects/9", timeout=5)
        print(f"   Status: {r.status_code}")
        print(f"   Body: {r.text[:300]}")
    except Exception as e:
        print(f"   ERROR: {e}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    test_api()
