import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import os
os.environ["DATABASE_URL"] = "postgresql://postgres:postgres_password@localhost:5432/construction_docs"

from app.db import SessionLocal
from app import models
from collections import Counter

db = SessionLocal()
pages = db.query(models.DocumentPage).all()

print(f"Pages: {len(pages)}")
cats = Counter(p.category for p in pages)
print(f"Categories: {dict(cats)}")

db.close()
