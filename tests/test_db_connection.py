import sys
import os
sys.path.insert(0, '.')

# Устанавливаем кодировку
os.environ['PYTHONIOENCODING'] = 'utf-8'

from app.db import SessionLocal, engine
from app.models import Base

print("Подключение к БД...")
print(f"Engine: {engine.url}")

try:
    db = SessionLocal()
    result = db.execute("SELECT version();")
    version = result.fetchone()
    print(f"OK: PostgreSQL версия: {version[0]}")
    
    # Проверка таблиц
    from sqlalchemy import inspect
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    print(f"\nTables in DB: {tables}")
    
    # Проверка пользователей
    from app.models import User
    user_count = db.query(User).count()
    print(f"\nUsers count: {user_count}")
    
    db.close()
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
