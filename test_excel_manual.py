import sys
sys.path.insert(0, '.')

from app.utils.document_parser import DocumentParser

doc_id = 32
print(f"Экспорт документа {doc_id} в Excel...")

try:
    with DocumentParser(doc_id, processed_dir='processed') as parser:
        print(f"DocumentParser создан: {parser.document.name}")
        print(f"Страниц: {len(parser.all_pages)}")
        
        output_path = parser.export_to_excel('output/documents/test_spec_export.xlsx')
        print(f"OK: {output_path}")
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
