import sys
sys.path.insert(0, '.')

from app.utils.document_parser import DocumentParser

doc_id = 32
print(f"Экспорт документа {doc_id} в Excel...")

with DocumentParser(doc_id, processed_dir='processed') as parser:
    output_path = parser.export_to_excel('output/documents/test_spec_export.xlsx')
    print(f"✓ Сохранено: {output_path}")
