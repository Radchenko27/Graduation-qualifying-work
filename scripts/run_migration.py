import sys
import os

# Явно указываем PostgreSQL
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, models
from sqlalchemy import text

try:
    engine = db.get_db().__next__().bind.engine
    connection = engine.connect()
    
    dialect = connection.dialect.name
    print(f"Database dialect: {dialect}")
    
    if dialect == 'postgresql':
        # 1. Проверка поля created_at в projects
        result = connection.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'projects' AND column_name = 'created_at'
        """))
        
        if not result.fetchone():
            print("Adding created_at to projects...")
            connection.execute(text("ALTER TABLE projects ADD COLUMN created_at DATE"))
            connection.commit()
            print("OK: created_at added to projects")
        else:
            print("OK: created_at already exists in projects")
        
        # 2. Проверка поля category в documents
        result = connection.execute(text("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'category'
        """))
        
        if result.fetchone():
            print("Removing category from documents...")
            connection.execute(text("ALTER TABLE documents DROP COLUMN category"))
            connection.commit()
            print("OK: category removed from documents")
        else:
            print("OK: category already removed from documents")
        
        # 3. Обновление индексов
        print("Updating indexes...")
        models.Base.metadata.create_all(bind=engine)
        print("OK: Indexes updated")
        
        print("\nSUCCESS: Migration completed!")
    else:
        print(f"ERROR: Expected PostgreSQL, got: {dialect}")
    
    connection.close()
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

