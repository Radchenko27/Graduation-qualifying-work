import sys
sys.path.insert(0, r'C:\Users\dimar\Desktop\BMSTU_IU5\Graduation-qualifying-work')

try:
    from app.crud import Documents, Projects
    print("Import OK")
    print(f"Documents.remove: {Documents.remove}")
    print(f"Projects.remove: {Projects.remove}")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
