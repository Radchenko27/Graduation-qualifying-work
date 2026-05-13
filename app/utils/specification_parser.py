"""
Парсер спецификаций из PDF документов.

Использует структуру processed JSON (text постранично) и разбивает
таблицы спецификаций по позициям колонок из заголовка.
"""

import json
import re
import io
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import pandas as pd
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app import models, crud


class SpecificationParser:
    """Класс для парсинга спецификаций из PDF"""
    
    # Стандартные названия колонок (рус → англ)
    COLUMN_MAP = {
        'поз': 'position',
        'поз.': 'position',
        'позиция': 'position',
        '№ п/п': 'position',
        '№п/п': 'position',
        '№': 'position',
        'обозн': 'designation',
        'обозн.': 'designation',
        'обозначение': 'designation',
        'наимен': 'name',
        'наимен.': 'name',
        'наименование': 'name',
        'кол': 'quantity',
        'кол.': 'quantity',
        'кол-во': 'quantity',
        'количество': 'quantity',
        'ед': 'unit',
        'ед.': 'unit',
        'ед.изм': 'unit',
        'ед. изм': 'unit',
        'единица измерения': 'unit',
        'прим': 'note',
        'прим.': 'note',
        'примечание': 'note',
        'масса': 'mass',
        'тип': 'type',
        'марка': 'mark',
    }
    
    def __init__(self, document_id: int, processed_dir: str = "processed"):
        self.document_id = document_id
        self.processed_dir = Path(processed_dir)
        self.db = SessionLocal()
        
        self.document = crud.Documents.get(self.db, document_id)
        if not self.document:
            raise ValueError(f"Документ с ID {document_id} не найден")
        
        self.spec_pages = self._get_specification_pages()
        self.processed_data = self._load_processed_json()
        self._use_pdf_fallback = False
        
        if not self.processed_data or not self.processed_data.get('text'):
            self.processed_data = self._fallback_pdf_parse()
            self._use_pdf_fallback = True
    
    def _get_specification_pages(self) -> List[models.DocumentPage]:
        return self.db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == self.document_id,
            models.DocumentPage.category == 'specification'
        ).order_by(models.DocumentPage.page_number).all()
        
    def _load_processed_json(self) -> Optional[Dict]:
        doc_name = Path(self.document.name).stem if self.document.name else ""
        candidate_files = []
        
        if self.processed_dir.exists():
            for json_file in self.processed_dir.glob("**/*_processed.json"):
                stem = json_file.stem
                parent = json_file.parent.name
                
                if stem.startswith(f"{self.document_id}_"):
                    candidate_files.append((json_file, 4))
                elif str(self.document_id) in stem or str(self.document_id) in parent:
                    candidate_files.append((json_file, 3))
                elif doc_name and any(part in stem or part in parent for part in doc_name.split('-') if len(part) > 3):
                    candidate_files.append((json_file, 2))
                elif not candidate_files:
                    candidate_files.append((json_file, 1))
        
        candidate_files.sort(key=lambda x: x[1], reverse=True)
        
        for json_file, priority in candidate_files:
            data = self._try_load_json_file(json_file)
            if data is not None:
                return data
        
        return None
    
    def _try_load_json_file(self, json_file: Path) -> Optional[Dict]:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return self._recover_json_from_file(json_file)
        except Exception:
            return None
        
    def _recover_json_from_file(self, json_file: Path) -> Optional[Dict]:
        text_data = {}
        current_page = None
        current_text = []
        
        with open(json_file, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                page_match = re.match(r'^"(\d+)":\s*"(.*)', line)
                if page_match:
                    if current_page is not None and current_text:
                        text_data[str(current_page)] = '\n'.join(current_text)
                    current_page = int(page_match.group(1))
                    current_text = [page_match.group(2).rstrip('"').replace('\\n', '\n')]
                    continue
                if current_page is not None:
                    cleaned = line.replace('\\n', '\n').strip('",')
                    if cleaned:
                        current_text.append(cleaned)
                
        if current_page is not None and current_text:
            text_data[str(current_page)] = '\n'.join(current_text)
        
        if text_data:
            return {'text': text_data, 'metadata': {'recovered': True}}
        return None
    
    def _fallback_pdf_parse(self) -> Dict:
        if not self.document.file_path:
            return {'text': {}}
        
        object_key = self.document.file_path.replace("minio://", "")
        if object_key.startswith("documents/"):
            object_key = object_key.replace("documents/", "", 1)
        
        try:
            from app.services.minio_client import minio_client

            pdf_content = minio_client.download_file(object_key)
            import fitz
            doc = fitz.open(stream=io.BytesIO(pdf_content), filetype="pdf")
            text_data = {}
            for page_num in range(len(doc)):
                text_data[str(page_num)] = doc[page_num].get_text()
            doc.close()
            return {'text': text_data, 'metadata': {'source': 'pdf_fallback'}}
        except Exception as e:
            print(f"[ERROR] Fallback PDF parse failed: {e}")
            return {'text': {}}
    
    # ───────────────────────────────────────────────
    #  Основной метод: парсинг по позициям колонок
    # ───────────────────────────────────────────────
    
    def _get_page_blocks(self, page_key: str) -> List[Dict[str, Any]]:
        """
        Получить text_blocks_details для страницы из processed JSON.
        pdf_processor сохраняет structure с ЧИСЛОВЫМИ ключами: structure[0], structure[1]
        """
        page_num_int = int(page_key)

        # Основной формат pdf_processor: structure[page_num]["text_blocks_details"]
        structure = self.processed_data.get('structure', {})
        if isinstance(structure, dict):
            if page_num_int in structure:
                return structure[page_num_int].get('text_blocks_details', [])
            if page_key in structure:
                return structure[page_key].get('text_blocks_details', [])

        # Альтернативный формат: pages[page_num]["structure"]["text_blocks_details"]
        pages = self.processed_data.get('pages', [])
        if isinstance(pages, list) and page_num_int < len(pages):
            page_struct = pages[page_num_int].get('structure', {})
            return page_struct.get('text_blocks_details', [])

        # Legacy форматы
        blocks_data = self.processed_data.get('text_blocks_details', {})
        if isinstance(blocks_data, dict):
            if page_key in blocks_data:
                return blocks_data[page_key]
            if page_num_int in blocks_data:
                return blocks_data[page_num_int]

        pages_data = self.processed_data.get('pages', {})
        if isinstance(pages_data, dict):
            if page_key in pages_data:
                return pages_data[page_key].get('text_blocks_details', [])
            if page_num_int in pages_data:
                return pages_data[page_num_int].get('text_blocks_details', [])

        return []

    def extract_specification_tables(self) -> Dict[str, Any]:
        """
        Извлечь таблицы спецификаций со всех страниц.
        Возвращает словарь {page_N: {...}}.
        """
        result = {}
        text_pages = self.processed_data.get('text', {})

        for spec_page in self.spec_pages:
            page_num = spec_page.page_number
            page_key = str(page_num - 1) if page_num > 0 else "0"

            if page_key not in text_pages:
                continue
            
            page_text = text_pages[page_key]
            page_blocks = self._get_page_blocks(page_key)

            table = self._parse_page_by_columns(
                page_text, page_num, spec_page.confidence,
                text_blocks=page_blocks
            )

            if table and table.get('rows'):
                result[f"page_{page_num}"] = table

        return result

    def _parse_page_by_columns(
        self,
        text: str, 
        page_num: int, 
        confidence: float,
        text_blocks: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Парсинг одной страницы спецификации.

        Если доступны text_blocks с координатами — использует их
        для геометрического определения колонок (гораздо точнее).
        Иначе — fallback на текстовый парсинг.
        """
        lines = text.split('\n')
        
        # Пробуем геометрический парсинг через text_blocks
        if text_blocks:
            geo_result = self._parse_page_geometric(text_blocks, page_num, confidence)
            if geo_result and geo_result.get('rows'):
                return geo_result

        # Fallback: текстовый парсинг
        header_idx, header_line = self._find_header_line(lines)
        if header_idx == -1:
            return None

        columns_meta = self._detect_columns(header_line)
        if len(columns_meta) < 2:
            return None

        rows = []
        current_row = None

        for line in lines[header_idx + 1:]:
            row = self._parse_data_line(line, columns_meta)
            if row:
                rows.append(row)
                current_row = row
                continue
            
            if current_row and self._is_continuation_line(line):
                self._append_continuation(current_row, line)

        if not rows:
            return None

        return {
            'page_number': page_num,
            'confidence': confidence,
            'header': header_line,
            'header_line_index': header_idx,
            'columns': columns_meta,
            'rows': rows,
            'row_count': len(rows),
            'parse_method': 'fixed_width_by_page_header',
            'source': 'pdf_fallback' if self._use_pdf_fallback else 'processed_json'
        }

    def _parse_page_geometric(
        self,
        text_blocks: List[Dict[str, Any]],
        page_num: int,
        confidence: float
    ) -> Optional[Dict[str, Any]]:
        """
        Геометрический парсинг таблицы через text_blocks_details.

        Использует x0/x1 координаты блоков для точного определения
        границ колонок. Блоки группируются по вертикали (y) в строки,
        а по горизонтали (x) — в колонки.
        """
        if not text_blocks:
            return None

        # Сортируем блоки по y (сверху вниз), затем по x (слева направо)
        sorted_blocks = sorted(
            text_blocks,
            key=lambda b: (round(b.get('y0', 0), 1), b.get('x0', 0))
        )

        # Ищем строку заголовка — блоки с ключевыми словами колонок
        header_blocks = []
        header_y = None
        for block in sorted_blocks:
            block_text = block.get('text', '').strip()
            if not block_text:
                continue
            # Проверяем, содержит ли блок заголовок колонки
            if any(re.search(pattern, block_text, re.IGNORECASE)
                   for pattern, _ in self._column_header_patterns()):
                header_blocks.append(block)
                header_y = block.get('y0')

        if len(header_blocks) < 2:
            return None

        # Сортируем заголовочные блоки по x
        header_blocks.sort(key=lambda b: b.get('x0', 0))

        # Формируем метаданные колонок из координат блоков
        columns_meta = []
        for i, block in enumerate(header_blocks):
            label = block.get('text', '').strip().replace('\n', ' ')
            key = self._map_column_name(label)
            start = int(block.get('x0', 0))
            end = int(header_blocks[i + 1].get('x0', 0)) if i + 1 < len(header_blocks) else None

            columns_meta.append({
                'key': key,
                'label': label,
                'start': start,
                'end': end,
                'source': 'geometric_block',
                'x0': block.get('x0'),
                'y0': block.get('y0'),
                'x1': block.get('x1'),
                'y1': block.get('y1'),
            })

        # Собираем строки данных — блоки ниже заголовка, группируем по y
        data_blocks = [b for b in sorted_blocks
                       if b.get('y0', 0) > (header_y or 0) + 5]

        # Группируем блоки по строкам (похожий y)
        rows = []
        current_row_blocks = []
        current_y = None
        y_threshold = 10  # пикселей

        for block in data_blocks:
            y = block.get('y0', 0)
            if current_y is None or abs(y - current_y) < y_threshold:
                current_row_blocks.append(block)
                current_y = y if current_y is None else (current_y + y) / 2
            else:
                # Новая строка
                row = self._build_row_from_blocks(current_row_blocks, columns_meta)
                if row:
                    rows.append(row)
                current_row_blocks = [block]
                current_y = y

        # Последняя строка
        if current_row_blocks:
            row = self._build_row_from_blocks(current_row_blocks, columns_meta)
            if row:
                rows.append(row)

        if not rows:
            return None

        header_line = ' '.join(b.get('text', '').strip() for b in header_blocks)

        return {
            'page_number': page_num,
            'confidence': confidence,
            'header': header_line,
            'columns': columns_meta,
            'rows': rows,
            'row_count': len(rows),
            'parse_method': 'geometric_text_blocks',
            'source': 'processed_json',
            'text_blocks_used': len(text_blocks),
        }

    def _build_row_from_blocks(
        self,
        blocks: List[Dict[str, Any]],
        columns: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Собрать строку таблицы из блоков, распределив по колонкам по x-координатам."""
        row = {col['key']: '' for col in columns}
        row['raw_line'] = ''
        row['cells_by_header'] = {}

        # Сортируем блоки по x
        blocks.sort(key=lambda b: b.get('x0', 0))

        for block in blocks:
            x = block.get('x0', 0)
            text = block.get('text', '').strip().replace('\n', ' ')
            if not text:
                continue

            # Находим колонку, в которую попадает блок
            best_col = None
            best_dist = float('inf')
            for col in columns:
                col_start = col.get('x0', col.get('start', 0))
                col_end = col.get('x1', col.get('end', float('inf')))
                if col_end is None:
                    col_end = float('inf')

                if col_start <= x < col_end:
                    best_col = col
                    break
                else:
                    dist = min(abs(x - col_start), abs(x - col_end))
                    if dist < best_dist:
                        best_dist = dist
                        best_col = col

            if best_col:
                key = best_col['key']
                if row[key]:
                    row[key] += ' ' + text
                else:
                    row[key] = text

        # Проверяем валидность
        values = [v for v in row.values() if v and not isinstance(v, dict)]
        if len(values) < 2:
            return None

        row['raw_line'] = ' '.join(
            b.get('text', '').strip().replace('\n', ' ')
            for b in sorted(blocks, key=lambda b: b.get('x0', 0))
        )
        row['cells_by_header'] = {
            col['label']: row.get(col['key'], '')
            for col in columns
        }

        return row

    def _find_header_line(self, lines: List[str]) -> Tuple[int, str]:
        """
        Найти именно строку заголовков колонок таблицы.
        Возвращает (index, line) или (-1, "").
        """
        for i, line in enumerate(lines):
            if self._is_table_header(line):
                return i, line

            # Некоторые PDF отдают многоуровневый заголовок двумя строками.
            # Проверяем объединение текущей и следующей строки без подмены
            # заголовком страницы/раздела.
            if i + 1 < len(lines):
                combined = f"{line.rstrip()}  {lines[i + 1].lstrip()}"
                if self._is_table_header(combined):
                    return i, combined

        return -1, ""

    def _is_table_header(self, line: str) -> bool:
        line_lower = self._normalize_header_text(line)
        if not line_lower:
            return False

        detected = {col['key'] for col in self._detect_columns(line)}
        has_name = 'name' in detected
        has_quantity = 'quantity' in detected
        has_position_or_designation = bool({'position', 'designation'} & detected)

        return len(detected) >= 2 and (has_name or has_quantity) and (
            has_position_or_designation or len(detected) >= 3
        )

    def _detect_columns(self, header_line: str) -> List[Dict[str, Any]]:
        """
        Определить столбцы по фактическому заголовку текущей страницы.
        Возвращает список метаданных: key, label, start, end.
        """
        matches = []
        used_ranges = []

        for label_pattern, key in self._column_header_patterns():
            for match in re.finditer(label_pattern, header_line, flags=re.IGNORECASE):
                start, end = match.span()
                if any(not (end <= s or start >= e) for s, e in used_ranges):
                    continue
                label = header_line[start:end].strip()
                if not label:
                    continue
                matches.append({
                    'key': key,
                    'label': label,
                    'start': start,
                    'end': end,
                    'source': 'header'
                })
                used_ranges.append((start, end))

        if len(matches) < 2:
            matches = self._detect_columns_by_split(header_line)

        matches.sort(key=lambda col: col['start'])
        matches = self._deduplicate_columns(matches)

        for i, column in enumerate(matches):
            next_start = matches[i + 1]['start'] if i + 1 < len(matches) else None
            column['end'] = next_start

        return matches

    def _column_header_patterns(self) -> List[Tuple[str, str]]:
        return [
            (r'№\s*п/?п', 'position'),
            (r'поз(?:иция)?\.?', 'position'),
            (r'№', 'position'),
            (r'обозн(?:ачение)?\.?', 'designation'),
            (r'марка\.?', 'mark'),
            (r'тип\.?', 'type'),
            (r'наимен(?:ование)?\.?', 'name'),
            (r'кол(?:-?во|ичество)?\.?', 'quantity'),
            (r'ед(?:иница)?\.?\s*(?:изм(?:ерения)?\.?)?', 'unit'),
            (r'масса\.?', 'mass'),
            (r'прим(?:ечание)?\.?', 'note'),
        ]

    def _detect_columns_by_split(self, header_line: str) -> List[Dict[str, Any]]:
        columns = []
        current_pos = 0

        for part in re.split(r'\t+| {2,}', header_line.strip()):
            label = part.strip()
            if not label:
                continue

            start = header_line.find(label, current_pos)
            if start == -1:
                start = current_pos

            key = self._map_column_name(label)
            if key == self._normalize_header_text(label):
                continue

            columns.append({
                'key': key,
                'label': label,
                'start': start,
                'end': start + len(label),
                'source': 'header_split'
            })
            current_pos = start + len(label)

        return columns

    def _deduplicate_columns(self, columns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        result = []
        used_keys = {}

        for column in columns:
            base_key = column['key']
            used_keys[base_key] = used_keys.get(base_key, 0) + 1
            if used_keys[base_key] > 1:
                column = dict(column)
                column['key'] = f"{base_key}_{used_keys[base_key]}"
            result.append(column)

        return result

    def _detect_column_positions(self, header_line: str) -> Tuple[List[str], List[int]]:
        """
        Совместимость со старым API: вернуть ключи колонок и стартовые позиции.
        """
        columns = self._detect_columns(header_line)
        return [col['key'] for col in columns], [col['start'] for col in columns]

    def _parse_header_columns(self, header_line: str) -> List[str]:
        """Совместимость со старыми тестами/скриптами."""
        columns, _ = self._detect_column_positions(header_line)
        return columns

    def _map_column_name(self, text: str) -> str:
        """Сопоставить русское название колонки с английским ключом."""
        text_lower = self._normalize_header_text(text)
        return self.COLUMN_MAP.get(text_lower, text_lower)

    def _normalize_header_text(self, text: str) -> str:
        return re.sub(r'\s+', ' ', text.lower().strip().rstrip('.'))

    def _parse_data_line(
        self,
        line: str,
        columns: List[Dict[str, Any]],
        positions: Optional[List[int]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Разобрать строку данных по позициям колонок текущего листа.
        """
        line = line.rstrip()
        if not line or len(line.strip()) < 2:
            return None

        if self._is_table_header(line):
            return None

        row = self._parse_fixed_width_line(line, columns)
        if not self._is_valid_data_row(row, columns):
            row = self._parse_split_line(line, columns)

        if not self._is_valid_data_row(row, columns):
            return None

        row['raw_line'] = line.strip()
        row['cells_by_header'] = {
            col['label']: row.get(col['key'], '')
            for col in columns
        }

        return row

    def _parse_fixed_width_line(
        self,
        line: str,
        columns: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        row = {}

        for column in columns:
            start_pos = column['start']
            end_pos = column['end'] if column['end'] is not None else len(line)
            row[column['key']] = line[start_pos:end_pos].strip() if start_pos < len(line) else ''

        return self._clean_row_values(row)

    def _parse_split_line(
        self,
        line: str,
        columns: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        parts = [part.strip() for part in re.split(r'\t+| {2,}', line.strip()) if part.strip()]
        row = {column['key']: '' for column in columns}

        for column, value in zip(columns, parts):
            row[column['key']] = value

        # Если частей больше, чем колонок, добавляем остаток в последнюю
        # текстовую колонку, чтобы не терять данные.
        if len(parts) > len(columns) and columns:
            target_key = columns[-1]['key']
            row[target_key] = ' '.join([row.get(target_key, ''), *parts[len(columns):]]).strip()

        return self._clean_row_values(row)

    def _clean_row_values(self, row: Dict[str, str]) -> Dict[str, str]:
        cleaned = {}
        for key, value in row.items():
            value = re.sub(r'\s+', ' ', value).strip()
            if key.startswith('quantity') and value:
                value = value.replace(',', '.') if re.fullmatch(r'\d+[\d\s,.]*', value) else value
            cleaned[key] = value
        return cleaned

    def _is_valid_data_row(self, row: Dict[str, str], columns: List[Dict[str, Any]]) -> bool:
        if not row:
            return False

        values = [value for value in row.values() if value]
        if len(values) < 2:
            return False

        if 'position' in row and row.get('position'):
            return bool(re.match(r'^[\dА-ЯA-Zа-яa-z№\-.]+$', row['position']))

        if 'name' in row and row.get('name'):
            return True

        return bool(values)

    def _is_continuation_line(self, line: str) -> bool:
        line = line.strip()
        if not line or self._is_table_header(line):
            return False
        return not re.match(r'^[\dА-ЯA-Zа-яa-z№\-.]+\s{2,}', line)

    def _append_continuation(self, row: Dict[str, Any], line: str) -> None:
        text = re.sub(r'\s+', ' ', line).strip()
        if not text:
            return

        target_key = 'name' if 'name' in row else next(
            (key for key, value in row.items() if key not in {'raw_line', 'cells_by_header'} and value),
            None
        )
        if not target_key:
            return

        row[target_key] = f"{row.get(target_key, '')} {text}".strip()
        row['raw_line'] = f"{row.get('raw_line', '')}\n{text}".strip()
        if 'cells_by_header' in row:
            for label, value in row['cells_by_header'].items():
                if value == row.get(target_key, ''):
                    row['cells_by_header'][label] = row[target_key]
                    break

    def _parse_spec_row(self, line: str, columns: List[str]) -> Optional[Dict[str, Any]]:
        """Совместимость со старыми тестами/скриптами."""
        header = '  '.join(columns)
        columns_meta = [
            {'key': key, 'label': key, 'start': match.start(), 'end': None, 'source': 'compat'}
            for key, match in ((key, re.search(re.escape(key), header)) for key in columns)
            if match
        ]
        return self._parse_data_line(line, columns_meta)
    
    # ───────────────────────────────────────────────
    #  Экспорт
    # ───────────────────────────────────────────────
    
    def export_to_json(self, output_path: str) -> str:
        specs = self.extract_specification_tables()
        
        # Собираем все строки в плоский список для удобства.
        # Поля берутся из columns каждой конкретной страницы, а не из
        # глобального фиксированного набора.
        all_rows = []
        for page_key, table in specs.items():
            for row in table['rows']:
                row_copy = self._row_by_original_headers(row, table['columns'])
                row_copy['page_number'] = table['page_number']
                row_copy['source_page_key'] = page_key
                all_rows.append(row_copy)
        
        output_data = {
            'document_id': self.document_id,
            'document_name': self.document.name,
            'project_id': self.document.project_id,
            'exported_at': datetime.now().isoformat(),
            'source': 'pdf_fallback' if self._use_pdf_fallback else 'processed_json',
            'specification_pages_count': len(self.spec_pages),
            'tables_found': len(specs),
            'schema_note': 'Для каждой страницы columns содержит реальные заголовки, найденные на этой странице: label — исходное имя столбца, key — технический ключ, start/end — границы в строке.',
            'specifications': specs,
            'all_rows_flat': all_rows,
            'summary': {
                'total_rows': sum(t['row_count'] for t in specs.values()),
                'total_tables': len(specs)
            }
        }
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        return str(output_path)
    
    def export_to_excel(self, output_path: str) -> str:
        specs = self.extract_specification_tables()
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Сводка
            summary_data = {
                'Документ': [self.document.name],
                'ID': [self.document_id],
                'Страниц со спецификациями': [len(self.spec_pages)],
                'Таблиц найдено': [len(specs)],
                'Всего строк': [sum(t['row_count'] for t in specs.values())],
                'Источник': ['PDF fallback' if self._use_pdf_fallback else 'Processed JSON'],
                'Экспорт': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Сводка', index=False)
            
            # Каждая страница — отдельный лист. Заголовки Excel берутся из
            # исходных названий колонок конкретной страницы.
            for page_key, table in specs.items():
                rows = table['rows']
                if rows:
                    df = self._table_to_dataframe(table)
                    sheet_name = f"Стр_{table['page_number']}"[:31]
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Все строки вместе
            all_rows = []
            for page_key, table in specs.items():
                for row in table['rows']:
                    row_copy = self._row_by_original_headers(row, table['columns'])
                    row_copy['Страница'] = table['page_number']
                    row_copy['Источник'] = page_key
                    all_rows.append(row_copy)
            
            if all_rows:
                pd.DataFrame(all_rows).to_excel(writer, sheet_name='Все_строки', index=False)
        
        return str(output_path)
    
    def _table_to_dataframe(self, table: Dict[str, Any]) -> pd.DataFrame:
        rows = [
            self._row_by_original_headers(row, table['columns'])
            for row in table['rows']
        ]
        return pd.DataFrame(rows)

    def _row_by_original_headers(
        self,
        row: Dict[str, Any],
        columns: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        editable_row = {}
        for column in columns:
            editable_row[column['label']] = row.get(column['key'], '')
        return editable_row

    def get_summary(self) -> Dict[str, Any]:
        return {
            'document_id': self.document_id,
            'document_name': self.document.name,
            'project_id': self.document.project_id,
            'specification_pages_count': len(self.spec_pages),
            'source': 'pdf_fallback' if self._use_pdf_fallback else 'processed_json',
            'specification_pages': [
                {
                    'page_number': p.page_number,
                    'confidence': p.confidence,
                    'content_type': p.content_type
                }
                for p in self.spec_pages
            ]
        }
    
    def close(self):
        if self.db:
            self.db.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def parse_document_specifications(
    document_id: int,
    output_format: str = 'json',
    output_dir: str = 'output/specifications',
    processed_dir: str = 'processed'
) -> str:
    with SpecificationParser(document_id, processed_dir) as parser:
        doc_name = Path(parser.document.name).stem
        
        if output_format.lower() == 'excel':
            output_path = Path(output_dir) / f"{doc_name}_specifications.xlsx"
            return parser.export_to_excel(str(output_path))
        else:
            output_path = Path(output_dir) / f"{doc_name}_specifications.json"
            return parser.export_to_json(str(output_path))


def batch_parse_specifications(
    project_id: Optional[int] = None,
    output_format: str = 'json',
    output_dir: str = 'output/specifications',
    processed_dir: str = 'processed'
) -> List[str]:
    db = SessionLocal()
    output_files = []
    
    try:
        query = db.query(models.Document)
        if project_id:
            query = query.filter(models.Document.project_id == project_id)
        
        for doc in query.all():
            try:
                output_path = parse_document_specifications(
                    doc.id, output_format, output_dir, processed_dir
                )
                output_files.append(output_path)
                print(f"OK Документ {doc.id}: {doc.name}")
            except Exception as e:
                print(f"ERROR Документ {doc.id}: {e}")
    finally:
        db.close()
    
    return output_files


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Использование: python specification_parser.py <document_id> [json|excel]")
        sys.exit(1)
    
    doc_id = int(sys.argv[1])
    fmt = sys.argv[2] if len(sys.argv) > 2 else 'json'
    
    output = parse_document_specifications(doc_id, fmt)
    print(f"Сохранено: {output}")
    
    document_id = None
    project_id = None
    output_format = 'json'
    output_dir = 'output/specifications'
    
    i = 1
    while i < len(sys.argv):
        arg = sys.argv[i]
        
        if arg == '--project':
            project_id = int(sys.argv[i + 1])
            i += 2
        elif arg in ['json', 'excel']:
            output_format = arg
            i += 1
        elif not document_id and arg.isdigit():
            document_id = int(arg)
            i += 1
        else:
            output_dir = arg
            i += 1
    
    if project_id:
        print(f"Пакетная обработка проекта {project_id}...")
        output_files = batch_parse_specifications(
            project_id=project_id,
            output_format=output_format,
            output_dir=output_dir
        )
        print(f"\nГотово! Создано файлов: {len(output_files)}")
        for f in output_files:
            print(f"  - {f}")
    elif document_id:
        print(f"Обработка документа {document_id}...")
        output_path = parse_document_specifications(
            document_id=document_id,
            output_format=output_format,
            output_dir=output_dir
        )
        print(f"\nГотово! Файл сохранён: {output_path}")
    else:
        print("Ошибка: укажите document_id или --project <project_id>")
        sys.exit(1)