"""
Скрипт для парсинга спецификаций из классифицированных документов.

Использование:
    python scripts/parse_specifications.py --document <document_id> [format]
    python scripts/parse_specifications.py --project <project_id> [format]

Примеры:
    python scripts/parse_specifications.py --document 1 json
    python scripts/parse_specifications.py --document 1 excel
    python scripts/parse_specifications.py --project 1 json
"""

import argparse
import sys
from pathlib import Path

# Добавляем корневую директорию в путь для импортов
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.specification_parser import (
    parse_document_specifications,
    batch_parse_specifications
)
from app.db import SessionLocal
from app import models


def list_documents(project_id=None):
    """Вывести список документов"""
    db = SessionLocal()
    
    try:
        query = db.query(models.Document)
        if project_id:
            query = query.filter(models.Document.project_id == project_id)
        
        documents = query.all()
        
        if not documents:
            print("Документы не найдены")
            return
        
        print(f"\n{'ID':<6} {'Название':<50} {'Проект':<10}")
        print("-" * 70)
        
        for doc in documents:
            project_name = f"Проект {doc.project_id}"
            print(f"{doc.id:<6} {doc.name[:47]:<50} {project_name:<10}")
        
        print()
    
    finally:
        db.close()


def list_specification_pages(document_id):
    """Вывести список страниц со спецификациями"""
    db = SessionLocal()
    
    try:
        pages = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == document_id,
            models.DocumentPage.category == 'specification'
        ).order_by(models.DocumentPage.page_number).all()
        
        if not pages:
            print(f"Страниц со спецификациями для документа {document_id} не найдено")
            return
        
        print(f"\nДокумент ID: {document_id}")
        print(f"{'Страница':<10} {'Категория':<15} {'Уверенность':<12} {'Тип содержимого'}")
        print("-" * 60)
        
        for page in pages:
            confidence = f"{page.confidence:.2%}"
            content_type = page.content_type or '-'
            print(f"{page.page_number:<10} {page.category:<15} {confidence:<12} {content_type}")
        
        print()
    
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Парсинг спецификаций из классифицированных документов'
    )
    
    # Группа действий
    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument(
        '--document',
        type=int,
        metavar='ID',
        help='ID документа для обработки'
    )
    action_group.add_argument(
        '--project',
        type=int,
        metavar='ID',
        help='ID проекта для пакетной обработки всех документов'
    )
    action_group.add_argument(
        '--list',
        action='store_true',
        help='Вывести список документов'
    )
    action_group.add_argument(
        '--list-pages',
        type=int,
        metavar='ID',
        help='Вывести список страниц со спецификациями для документа'
    )
    
    # Дополнительные параметры
    parser.add_argument(
        '--format',
        choices=['json', 'excel'],
        default='json',
        help='Формат вывода (по умолчанию: json)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output/specifications',
        help='Директория для сохранения результатов (по умолчанию: output/specifications)'
    )
    parser.add_argument(
        '--processed-dir',
        type=str,
        default='processed',
        help='Директория с processed JSON файлами (по умолчанию: processed)'
    )
    
    args = parser.parse_args()
    
    # Вывод списка документов
    if args.list:
        list_documents()
        return
    
    # Вывод списка страниц со спецификациями
    if args.list_pages:
        list_specification_pages(args.list_pages)
        return
    
    # Парсинг спецификаций
    if args.document:
        print(f"Парсинг спецификаций документа {args.document}...")
        print(f"Формат: {args.format}")
        print(f"Выходная директория: {args.output}")
        print()
        
        try:
            output_path = parse_document_specifications(
                document_id=args.document,
                output_format=args.format,
                output_dir=args.output,
                processed_dir=args.processed_dir
            )
            
            print(f"✓ Готово! Файл сохранён: {output_path}")
            
            # Вывод статистики
            from app.utils.specification_parser import SpecificationParser
            with SpecificationParser(args.document, args.processed_dir) as parser:
                summary = parser.get_summary()
                print(f"\nСтатистика:")
                print(f"  Документ: {summary['document_name']}")
                print(f"  Страниц со спецификациями: {summary['specification_pages_count']}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            sys.exit(1)
    
    elif args.project:
        print(f"Пакетный парсинг спецификаций проекта {args.project}...")
        print(f"Формат: {args.format}")
        print(f"Выходная директория: {args.output}")
        print()
        
        try:
            output_files = batch_parse_specifications(
                project_id=args.project,
                output_format=args.format,
                output_dir=args.output,
                processed_dir=args.processed_dir
            )
            
            print(f"✓ Готово! Создано файлов: {len(output_files)}")
            for f in output_files:
                print(f"  - {f}")
                
        except Exception as e:
            print(f"✗ Ошибка: {e}")
            sys.exit(1)


if __name__ == '__main__':
    main()