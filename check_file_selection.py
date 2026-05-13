import sys
sys.path.insert(0, '.')

from pathlib import Path
from app.db import SessionLocal
from app import crud
from app.utils.document_parser import DocumentParser

db = SessionLocal()
doc = crud.Documents.get(db, 32)
print(f"Document: {doc.name}")

parser = DocumentParser(32, processed_dir='processed')
# Имитируем _load_processed_json
candidate_files = []
doc_name = Path(doc.name).stem if doc.name else ""

processed_dir = Path('processed')
if processed_dir.exists():
    for json_file in processed_dir.glob("**/*_processed.json"):
        stem = json_file.stem
        parent = json_file.parent.name
        print(f"  Found: {json_file.parent.name}/{json_file.name}")
        
        if stem.startswith(f"{32}_"):
            candidate_files.append((json_file, 4))
            print(f"    -> Priority 4 (id prefix)")
        elif str(32) in stem or str(32) in parent:
            candidate_files.append((json_file, 3))
            print(f"    -> Priority 3 (id in name)")
        elif doc_name and any(part in stem or part in parent for part in doc_name.split('-') if len(part) > 3):
            candidate_files.append((json_file, 2))
            print(f"    -> Priority 2 (name match)")
        else:
            candidate_files.append((json_file, 1))
            print(f"    -> Priority 1 (fallback)")

candidate_files.sort(key=lambda x: x[1], reverse=True)
print(f"\nSelected: {candidate_files[0][0] if candidate_files else 'NONE'}")
