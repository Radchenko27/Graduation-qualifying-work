import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models

db = SessionLocal()

# Проверяем project_id=6 (проект документа id=15)
project = db.query(models.Project).get(6)
print(f"Project id=6: owner_id={project.owner_id if project else 'NOT FOUND'}")

# Проверяем project_users
pu = db.query(models.ProjectUser).filter(
    models.ProjectUser.project_id == 6
).all()
print(f"ProjectUsers for project 6:")
for p in pu:
    print(f"  user_id={p.user_id}, access_rights={p.access_rights}")

# Проверяем document id=15
doc = db.query(models.Document).get(15)
print(f"\nDocument id=15: project_id={doc.project_id}, name={doc.name}")

# Проверяем page_count
documents = db.query(models.Document).all()
for d in documents:
    pages_count = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == d.id
    ).count()
    print(f"Doc '{d.name}': page_count={d.page_count}, classified_pages={pages_count}")

db.close()
