import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import engine
import sqlalchemy as sa

conn = engine.connect()
r = conn.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_name='document_pages'"))
row = r.fetchone()
print("document_pages exists:", row is not None)
if row:
    # Проверим колонки
    cols = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='document_pages'"))
    print("Columns:", [c[0] for c in cols])
conn.close()
