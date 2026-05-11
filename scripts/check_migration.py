import sys
import os

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app import db
from sqlalchemy import text

engine = db.get_db().__next__().bind.engine
conn = engine.connect()

# Check projects.created_at
r = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'projects' AND column_name = 'created_at'"))
print("projects.created_at:", "EXISTS" if r.fetchone() else "MISSING")

# Check documents.category
r = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'documents' AND column_name = 'category'"))
print("documents.category:", "EXISTS" if r.fetchone() else "MISSING")

conn.close()
