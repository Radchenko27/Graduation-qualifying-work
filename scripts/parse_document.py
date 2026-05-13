#!/usr/bin/env python3
"""
CLI скрипт для универсального парсинга документов.

Обрабатывает ВЕСЬ документ и создаёт структурированный JSON/Excel.

Использование:
    python scripts/parse_document.py --document <id> [json|excel]
    python scripts/parse_document.py --project <project_id> [json|excel]
    python scripts/parse_document.py --all [json|excel]
"""

import sys
import argparse
from pathlib import Path

# Добавляем родительскую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.utils.document_parser import (
    parse_document_to_json,
    parse_document_to_excel,
    batch_parse_documents
)


def main():
    parser = argparse.ArgumentParser(
        description='Универсальный парсер документов'
    )
    parser.add_argument(
        '--document', '-d',
        type=int,
        help='ID документа для обработки'
    )
    parser.add_argument(
        '--project', '-p',
        type=int,
        help='ID проекта для пакетной обработки'
    )
    parser.add_argument(
        '--all', '-a',
        action='store_true',
        help='Обработать все документы'
    )
    parser.add_argument(
        '--format', '-f',
        choices=['json', 'excel'],
        default='json',
        help='Формат выходного файла (по умолчанию: json)'
    )
    parser.add_argument(
        '--output-dir', '-o',
        default='output/documents',
        help='Директория для выходных файлов'
    )

    args = parser.parse_args()

    if args.document:
        print(f"Обработка документа {args.document}...")
        if args.format == 'excel':
            output_path = parse_document_to_excel(
                args.document,
                output_dir=args.output_dir
            )
        else:
            output_path = parse_document_to_json(
                args.document,
                output_dir=args.output_dir
            )
        print(f"\n✅ Готово! Файл сохранён: {output_path}")

    elif args.project:
        print(f"Пакетная обработка проекта {args.project}...")
        output_files = batch_parse_documents(
            project_id=args.project,
            output_format=args.format,
            output_dir=args.output_dir
        )
        print(f"\n✅ Готово! Обработано документов: {len(output_files)}")
        for f in output_files:
            print(f"  • {f}")

    elif args.all:
        print("Обработка ВСЕХ документов...")
        output_files = batch_parse_documents(
            output_format=args.format,
            output_dir=args.output_dir
        )
        print(f"\n✅ Готово! Обработано документов: {len(output_files)}")
        for f in output_files:
            print(f"  • {f}")

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
