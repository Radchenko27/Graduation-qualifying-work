"""
Тесты для specification_parser
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.utils.specification_parser import (
    SpecificationParser,
    parse_document_specifications,
    batch_parse_specifications
)
from app import models, crud


@pytest.fixture
def mock_document():
    """Фикстура с мок-документом"""
    doc = Mock(spec=models.Document)
    doc.id = 1
    doc.name = "Тестовая спецификация.pdf"
    doc.project_id = 1
    return doc


@pytest.fixture
def mock_spec_pages():
    """Фикстура с мок-страницами спецификаций"""
    pages = []
    for i in range(1, 4):
        page = Mock(spec=models.DocumentPage)
        page.id = i
        page.document_id = 1
        page.page_number = i
        page.category = 'specification'
        page.confidence = 0.85 + (i * 0.05)
        page.content_type = 'table'
        pages.append(page)
    return pages


@pytest.fixture
def sample_processed_data():
    """Фикстура с примером processed данных"""
    return {
        "metadata": {
            "file_name": "Тестовая спецификация.pdf",
            "page_count": 10,
            "title": "Спецификация оборудования"
        },
        "text": {
            "0": "Текст титульной страницы",
            "1": """
            Спецификация оборудования
            Поз  Обозначение  Наименование       Кол-во  Ед.изм.  Примечание
            1    АБВГ.001     Кабель ВВГнг 3x2.5  100     м        Для освещения
            2    АБВГ.002     Розетка 16А         50      шт       С заземлением
            """,
            "2": """
            Ведомость материалов
            Поз  Наименование      Кол-во  Единица
            3    Лампа LED 10W     200     шт
            4    Патрон E27        200     шт
            """
        }
    }


class TestSpecificationParser:
    """Тесты класса SpecificationParser"""
    
    def test_init_success(self, mock_document, mock_spec_pages, sample_processed_data):
        """Тест успешной инициализации"""
        with patch('app.utils.specification_parser.crud.Documents.get') as mock_get:
            with patch('app.utils.specification_parser.SessionLocal') as mock_db:
                mock_get.return_value = mock_document
                mock_db_instance = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
                mock_db.return_value.__exit__ = Mock(return_value=False)
                mock_db_instance.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_spec_pages
                
                # Мокаем загрузку JSON
                with patch.object(SpecificationParser, '_load_processed_json', return_value=sample_processed_data):
                    parser = SpecificationParser(1, processed_dir="processed")
                    
                    assert parser.document_id == 1
                    assert parser.document == mock_document
                    assert len(parser.spec_pages) == 3
                    assert parser.processed_data == sample_processed_data
    
    def test_get_specification_pages(self, mock_document, mock_spec_pages):
        """Тест получения страниц со спецификациями"""
        with patch('app.utils.specification_parser.crud.Documents.get') as mock_get:
            with patch('app.utils.specification_parser.SessionLocal') as mock_db:
                mock_get.return_value = mock_document
                mock_db_instance = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
                mock_db.return_value.__exit__ = Mock(return_value=False)
                mock_db_instance.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_spec_pages
                
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1, processed_dir="processed")
                    pages = parser._get_specification_pages()
                    
                    assert len(pages) == 3
                    assert all(p.category == 'specification' for p in pages)
    
    def test_parse_header_columns(self):
        """Тест парсинга заголовка таблицы"""
        with patch('app.utils.specification_parser.crud.Documents.get'):
            with patch('app.utils.specification_parser.SessionLocal'):
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1)
                    
                    # Тест стандартного заголовка
                    header = "Поз  Обозначение  Наименование       Кол-во  Ед.изм.  Примечание"
                    columns = parser._parse_header_columns(header)
                    
                    assert 'position' in columns
                    assert 'designation' in columns
                    assert 'name' in columns
                    assert 'quantity' in columns
                    assert 'unit' in columns
                    assert 'note' in columns
    
    def test_parse_spec_row(self):
        """Тест парсинга строки спецификации"""
        with patch('app.utils.specification_parser.crud.Documents.get'):
            with patch('app.utils.specification_parser.SessionLocal'):
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1)
                    
                    columns = ['position', 'designation', 'name', 'quantity', 'unit', 'note']
                    line = "1    АБВГ.001     Кабель ВВГнг 3x2.5  100     м        Для освещения"
                    
                    row = parser._parse_spec_row(line, columns)
                    
                    assert row['position'] == '1'
                    assert row['designation'] == 'АБВГ.001'
                    assert row['name'] == 'Кабель ВВГнг 3x2.5'
                    assert row['quantity'] == '100'  # Остаётся строкой для редактирования
                    assert row['unit'] == 'м'
                    assert row['note'] == 'Для освещения'
    
    def test_extract_specification_tables(self, mock_document, mock_spec_pages, sample_processed_data):
        """Тест извлечения таблиц спецификаций"""
        with patch('app.utils.specification_parser.crud.Documents.get') as mock_get:
            with patch('app.utils.specification_parser.SessionLocal') as mock_db:
                mock_get.return_value = mock_document
                mock_db_instance = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
                mock_db.return_value.__exit__ = Mock(return_value=False)
                mock_db_instance.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_spec_pages
                
                with patch.object(SpecificationParser, '_load_processed_json', return_value=sample_processed_data):
                    parser = SpecificationParser(1, processed_dir="processed")
                    specs = parser.extract_specification_tables()
                    
                    assert len(specs) == 2  # Две страницы с таблицами
                    assert 'page_2' in specs
                    assert 'page_3' in specs
                    assert specs['page_2']['page_number'] == 2
                    assert specs['page_2']['row_count'] == 2
                    assert specs['page_3']['page_number'] == 3
                    # Каждая страница имеет свои columns
                    assert len(specs['page_2']['columns']) >= 3
    
    def test_export_to_json(self, mock_document, mock_spec_pages, sample_processed_data, tmp_path):
        """Тест экспорта в JSON"""
        with patch('app.utils.specification_parser.crud.Documents.get') as mock_get:
            with patch('app.utils.specification_parser.SessionLocal') as mock_db:
                mock_get.return_value = mock_document
                mock_db_instance = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
                mock_db.return_value.__exit__ = Mock(return_value=False)
                mock_db_instance.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_spec_pages
                
                with patch.object(SpecificationParser, '_load_processed_json', return_value=sample_processed_data):
                    parser = SpecificationParser(1, processed_dir="processed")
                    
                    output_path = tmp_path / "test_spec.json"
                    result_path = parser.export_to_json(str(output_path))
                    
                    assert Path(result_path).exists()
                    
                    with open(result_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    assert data['document_id'] == 1
                    assert 'specifications' in data
                    assert 'all_rows_flat' in data
                    assert 'schema_note' in data
                    assert data['summary']['total_tables'] == 2
    
    def test_get_summary(self, mock_document, mock_spec_pages):
        """Тест получения сводной информации"""
        with patch('app.utils.specification_parser.crud.Documents.get') as mock_get:
            with patch('app.utils.specification_parser.SessionLocal') as mock_db:
                mock_get.return_value = mock_document
                mock_db_instance = Mock()
                mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
                mock_db.return_value.__exit__ = Mock(return_value=False)
                mock_db_instance.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_spec_pages
                
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1, processed_dir="processed")
                    summary = parser.get_summary()
                    
                    assert summary['document_id'] == 1
                    assert summary['document_name'] == mock_document.name
                    assert summary['specification_pages_count'] == 3
                    assert len(summary['specification_pages']) == 3

    def test_detect_columns(self):
        """Тест определения столбцов по заголовку"""
        with patch('app.utils.specification_parser.crud.Documents.get'):
            with patch('app.utils.specification_parser.SessionLocal'):
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1)

                    header = "Позиция  Обозначение  Наименование  Кол-во  Ед.изм."
                    columns = parser._detect_columns(header)

                    assert len(columns) >= 4
                    assert any(col['key'] == 'position' for col in columns)
                    assert any(col['key'] == 'name' for col in columns)
                    assert any(col['key'] == 'quantity' for col in columns)

                    # Проверяем метаданные столбцов
                    for col in columns:
                        assert 'label' in col  # Исходное название
                        assert 'key' in col    # Технический ключ
                        assert 'start' in col  # Позиция начала

    def test_row_by_original_headers(self):
        """Тест преобразования строки для экспорта"""
        with patch('app.utils.specification_parser.crud.Documents.get'):
            with patch('app.utils.specification_parser.SessionLocal'):
                with patch.object(SpecificationParser, '_load_processed_json', return_value={}):
                    parser = SpecificationParser(1)

                    columns = [
                        {'key': 'position', 'label': 'Позиция'},
                        {'key': 'name', 'label': 'Наименование'},
                        {'key': 'quantity', 'label': 'Кол-во'}
                    ]
                    row = {'position': '1', 'name': 'Кабель', 'quantity': '100'}

                    editable = parser._row_by_original_headers(row, columns)

                    assert editable == {
                        'Позиция': '1',
                        'Наименование': 'Кабель',
                        'Кол-во': '100'
                    }


class TestParseDocumentSpecifications:
    """Тесты функции parse_document_specifications"""
    
    def test_parse_to_json(self, mock_document, sample_processed_data, tmp_path):
        """Тест парсинга документа в JSON"""
        with patch('app.utils.specification_parser.SpecificationParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.document = mock_document
            mock_parser_class.return_value.__enter__ = Mock(return_value=mock_parser)
            mock_parser_class.return_value.__exit__ = Mock(return_value=False)
            
            output_path = tmp_path / "output.json"
            mock_parser.export_to_json.return_value = str(output_path)
            
            result = parse_document_specifications(
                document_id=1,
                output_format='json',
                output_dir=str(tmp_path),
                processed_dir='processed'
            )
            
            assert result == str(output_path)
            mock_parser.export_to_json.assert_called_once()
    
    def test_parse_to_excel(self, mock_document, sample_processed_data, tmp_path):
        """Тест парсинга документа в Excel"""
        with patch('app.utils.specification_parser.SpecificationParser') as mock_parser_class:
            mock_parser = Mock()
            mock_parser.document = mock_document
            mock_parser_class.return_value.__enter__ = Mock(return_value=mock_parser)
            mock_parser_class.return_value.__exit__ = Mock(return_value=False)
            
            output_path = tmp_path / "output.xlsx"
            mock_parser.export_to_excel.return_value = str(output_path)
            
            result = parse_document_specifications(
                document_id=1,
                output_format='excel',
                output_dir=str(tmp_path),
                processed_dir='processed'
            )
            
            assert result == str(output_path)
            mock_parser.export_to_excel.assert_called_once()


class TestBatchParseSpecifications:
    """Тесты функции batch_parse_specifications"""
    
    def test_batch_parse(self, tmp_path):
        """Тест пакетного парсинга"""
        mock_docs = [
            Mock(id=1, name="Doc1.pdf"),
            Mock(id=2, name="Doc2.pdf")
        ]
        
        with patch('app.utils.specification_parser.SessionLocal') as mock_db:
            mock_db_instance = Mock()
            mock_db.return_value.__enter__ = Mock(return_value=mock_db_instance)
            mock_db.return_value.__exit__ = Mock(return_value=False)
            mock_db_instance.query.return_value.all.return_value = mock_docs
            
            with patch('app.utils.specification_parser.parse_document_specifications') as mock_parse:
                mock_parse.side_effect = [
                    str(tmp_path / "doc1_spec.json"),
                    str(tmp_path / "doc2_spec.json")
                ]
                
                results = batch_parse_specifications(
                    project_id=1,
                    output_format='json',
                    output_dir=str(tmp_path),
                    processed_dir='processed'
                )
                
                assert len(results) == 2
                assert mock_parse.call_count == 2


if __name__ == '__main__':
    pytest.main([__file__, '-v'])