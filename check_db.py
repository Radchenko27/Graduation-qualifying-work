import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import engine
import sqlalchemy as sa

conn = engine.connect()

# Проверяем таблицы
tables_result = conn.execute(sa.text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
tables = [r[0] for r in tables_result]
print("Tables in DB:", sorted(tables))
print()

# Проверяем колонки documents
if 'documents' in tables:
    cols_result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='documents'"))
    cols = [r[0] for r in cols_result]
    print("documents columns:", sorted(cols))
    print("Has 'category':", 'category' in cols)
    print("Has 'page_count':", 'page_count' in cols)
else:
    print("documents table NOT FOUND")

print()

# Проверяем document_pages
print("Has document_pages:", 'document_pages' in tables)

# Проверяем drawing_calculations
print("Has drawing_calculations:", 'drawing_calculations' in tables)

# Проверяем estimates
print("Has estimates:", 'estimates' in tables)

# Проверяем project_shares access_level
if 'project_shares' in tables:
    cols_result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='project_shares'"))
    cols = [r[0] for r in cols_result]
    print("project_shares columns:", sorted(cols))
    print("Has 'access_level':", 'access_level' in cols)

# Проверяем materials type/price/mark
if 'materials' in tables:
    cols_result = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_name='materials'"))
    cols = [r[0] for r in cols_result]
    print("materials columns:", sorted(cols))

# Проверяем alembic_version
version_result = conn.execute(sa.text("SELECT version_num FROM alembic_version"))
versions = [r[0] for r in version_result]
print("\nAlembic versions:", versions)

conn.close()
