#!/usr/bin/env python3
"""
Скрипт для обновления схемы БД:
1. Добавление поля created_at в таблицу projects
2. Удаление поля category из таблицы documents
"""

import sys
import os
import locale

# Устанавливаем UTF-8 для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Добавляем корень проекта в путь
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db, models
from sqlalchemy import text
from sqlalchemy.exc import OperationalError, ProgrammingError

def main():
    engine = db.get_db().__next__().bind.engine
    connection = engine.connect()
    
    # Проверка поддержки SQLite/PostgreSQL
    dialect = connection.dialect.name
    print(f"Database dialect: {dialect}")
    
    try:
        # 1. Добавляем created_at в projects если нет
        print("\n[1/3] Проверка поля created_at в projects...")
        
        if dialect == 'sqlite':
            # Для SQLite проверяем наличие колонки
            result = connection.execute(text("PRAGMA table_info(projects)"))
            columns = [row[1] for row in result]
            
            if 'created_at' not in columns:
                print("  Добавляем created_at в projects...")
                connection.execute(text("ALTER TABLE projects ADD COLUMN created_at DATE"))
                connection.commit()
                print("  OK: Поле created_at добавлено")
            else:
                print("  OK: Поле created_at уже существует")
        
        elif dialect == 'postgresql':
            # Для PostgreSQL проверяем наличие колонки
            result = connection.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'projects' AND column_name = 'created_at'
            """))
            
            if not result.fetchone():
                print("  Добавляем created_at в projects...")
                connection.execute(text("ALTER TABLE projects ADD COLUMN created_at DATE"))
                connection.commit()
                print("  OK: Поле created_at добавлено")
            else:
                print("  OK: Поле created_at уже существует")
        
        # 2. Удаляем category из documents если есть
        print("\n[2/3] Проверка поля category в documents...")
        
        if dialect == 'sqlite':
            # Для SQLite нужно пересоздать таблицу
            result = connection.execute(text("PRAGMA table_info(documents)"))
            columns = [row[1] for row in result]
            
            if 'category' in columns:
                print("  Удаляем category из documents...")
                # Создаём временную таблицу без category
                connection.execute(text("""
                    CREATE TABLE documents_new AS 
                    SELECT id, project_id, doc_type, created_at, name, 
                           file_path, file_hash, page_count 
                    FROM documents
                """))
                
                # Удаляем старую таблицу
                connection.execute(text("DROP TABLE documents"))
                
                # Переименовываем новую
                connection.execute(text("ALTER TABLE documents_new RENAME TO documents"))
                connection.commit()
                print("  OK: Поле category удалено")
            else:
                print("  OK: Поле category уже не существует")
        
        elif dialect == 'postgresql':
            # Для PostgreSQL просто удаляем колонку
            result = connection.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'documents' AND column_name = 'category'
            """))
            
            if result.fetchone():
                print("  Удаляем category из documents...")
                connection.execute(text("ALTER TABLE documents DROP COLUMN category"))
                connection.commit()
                print("  OK: Поле category удалено")
            else:
                print("  OK: Поле category уже не существует")
        
        # 3. Обновляем индексы
        print("\n[3/3] Обновление индексов...")
        try:
            models.Base.metadata.create_all(bind=engine)
            print("  OK: Индексы обновлены")
        except Exception as e:
            print(f"  WARNING: Предупреждение при обновлении индексов: {e}")
        
        print("\nSUCCESS: Обновление схемы БД завершено успешно!")
        
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
        sys.exit(1)
    finally:
        connection.close()

if __name__ == "__main__":
    main()
