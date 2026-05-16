#!/usr/bin/env python
"""Тест API проектов"""
import sys
sys.path.insert(0, '.')

import httpx
import asyncio

async def test_projects():
    print("Testing /api/projects/...")
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            print("\n1. GET /api/projects/")
            resp = await client.get('http://127.0.0.1:8000/api/projects/', headers={'X-Session-Key': 'test'})
            print(f"   Status: {resp.status_code}")
            print(f"   Body: {resp.text[:300]}")
            
            print("\n2. GET /api/projects/9")
            resp = await client.get('http://127.0.0.1:8000/api/projects/9', headers={'X-Session-Key': 'test'})
            print(f"   Status: {resp.status_code}")
            print(f"   Body: {resp.text[:300]}")
            
        except httpx.TimeoutException:
            print("   TIMEOUT!")
        except Exception as e:
            print(f"   ERROR: {e}")

if __name__ == '__main__':
    asyncio.run(test_projects())
