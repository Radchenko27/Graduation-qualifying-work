"""
Универсальный парсер документов.

Обрабатывает ВЕСЬ документ и создаёт полную структурированную JSON-модель.
Каждая страница парсится в зависимости от её категории:
  - specification → таблицы спецификаций
  - drawing       → название, обозначение, размеры
  - scheme        → элементы схемы, обозначения
  - title         → метаданные документа
  - other         → текст страницы
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


class DocumentParser:
    """Универсальный парсер документов — структурирует ВСЕ страницы"""

    def __init__(self, document_id: int, processed_dir: str = "processed"):
        self.document_id = document_id
        self.processed_dir = Path(processed_dir)
        self.db = SessionLocal()

        self.document = crud.Documents.get(self.db, document_id)
        if not self.document:
            raise ValueError(f"Документ с ID {document_id} не найден")

        self.all_pages = self._get_all_pages()
        self.processed_data = self._load_processed_json()
        self._use_pdf_fallback = False

        if not self.processed_data or not self.processed_data.get('text'):
            self.processed_data = self._fallback_pdf_parse()
            self._use_pdf_fallback = True

    def _get_all_pages(self) -> List[models.DocumentPage]:
        """Все страницы документа, отсортированные по номеру"""
        return self.db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == self.document_id
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
    #  Основной метод: обработка ВСЕГО документа
    # ───────────────────────────────────────────────

    def _get_page_blocks(self, page_key: str) -> List[Dict[str, Any]]:
        """Получить text_blocks_details для страницы из processed JSON."""
        # pdf_processor теперь сохраняет structure с 1-based ключами: structure[1], structure[2]...
        # page_key приходит как строка: "1", "2", "3"... (соответствует page_number)
        page_num_int = int(page_key)

        # Формат pdf_processor: structure[page_num]["text_blocks_details"]
        structure = self.processed_data.get('structure', {})
        if isinstance(structure, dict):
            # Пробуем 1-based ключ сначала
            if page_num_int in structure:
                return structure[page_num_int].get('text_blocks_details', [])
            # Пробуем строковый ключ
            if str(page_num_int) in structure:
                return structure[str(page_num_int)].get('text_blocks_details', [])
            # Fallback на 0-based для старых файлов
            if page_num_int - 1 in structure:
                return structure[page_num_int - 1].get('text_blocks_details', [])
            if str(page_num_int - 1) in structure:
                return structure[str(page_num_int - 1)].get('text_blocks_details', [])

        # Альтернативный формат: pages[page_num]["structure"]["text_blocks_details"]
        pages = self.processed_data.get('pages', [])
        if isinstance(pages, list) and page_num_int <= len(pages):
            page_struct = pages[page_num_int - 1].get('structure', {}) if page_num_int > 0 else {}
            return page_struct.get('text_blocks_details', [])

        # Legacy формат
        blocks_data = self.processed_data.get('text_blocks_details', {})
        if isinstance(blocks_data, dict):
            if str(page_num_int) in blocks_data:
                return blocks_data[str(page_num_int)]
            if page_num_int in blocks_data:
                return blocks_data[page_num_int]

        return []

    def parse_document(self) -> Dict[str, Any]:
        """
        Обработать ВЕСЬ документ и вернуть структурированную модель.

        Returns:
            {
              "document_id": 1,
              "document_name": "...",
              "pages": {
                "page_1": {"category": "title", "data": {...}, "text_blocks": [...]},
                ...
              }
            }
        """
        result = {
            "document_id": self.document_id,
            "document_name": self.document.name,
            "project_id": self.document.project_id,
            "parsed_at": datetime.now().isoformat(),
            "source": "pdf_fallback" if self._use_pdf_fallback else "processed_json",
            "total_pages": len(self.all_pages),
            "pages": {}
        }

        text_pages = self.processed_data.get('text', {})

        for page in self.all_pages:
            page_num = page.page_number
            # Используем 1-based ключ для text и structure
            page_key = str(page_num)
            page_text = text_pages.get(page_key, "")
            page_blocks = self._get_page_blocks(page_key)

            parsed_page = self._parse_page(page, page_text, page_blocks)
            result["pages"][f"page_{page_num}"] = parsed_page

        return result

    def _parse_page(
        self,
        page: models.DocumentPage,
        text: str,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг одной страницы в зависимости от категории"""
        base = {
            "page_number": page.page_number,
            "category": page.category,
            "confidence": page.confidence,
            "content_type": page.content_type,
        }

        # Включаем text_blocks_details в выход (как в processed JSON)
        if text_blocks:
            base["text_blocks_details"] = text_blocks
            base["text_blocks_count"] = len(text_blocks)

        if page.category == 'specification':
            base["data"] = self._parse_specification_page(text, page, text_blocks)
        elif page.category == 'drawing':
            base["data"] = self._parse_drawing_page(text, page, text_blocks)
        elif page.category == 'scheme':
            base["data"] = self._parse_scheme_page(text, page, text_blocks)
        elif page.category == 'title':
            base["data"] = self._parse_title_page(text, page, text_blocks)
        else:
            base["data"] = self._parse_other_page(text, page, text_blocks)

        return base

    # ───────────────────────────────────────────────
    #  Парсеры по категориям
    # ───────────────────────────────────────────────

    def _parse_specification_page(
        self,
        text: str,
        page: models.DocumentPage,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг страницы спецификации — использует SpecificationParser"""
        from app.utils.specification_parser import SpecificationParser

        sp = object.__new__(SpecificationParser)
        sp._use_pdf_fallback = self._use_pdf_fallback

        table = sp._parse_page_by_columns(
            text, page.page_number, page.confidence,
            text_blocks=text_blocks
        )

        if table:
            result = {
                "type": "specification_table",
                "has_table": True,
                "header": table.get("header", ""),
                "columns": table.get("columns", []),
                "rows": table.get("rows", []),
                "row_count": table.get("row_count", 0),
                "parse_method": table.get("parse_method", "unknown"),
            }
            if table.get('text_blocks_used'):
                result["text_blocks_used"] = table["text_blocks_used"]
            return result
        else:
            return {
                "type": "specification_text",
                "has_table": False,
                "text_preview": text[:500] if text else "",
                "note": "Страница классифицирована как specification, но таблица не найдена"
            }

    def _parse_drawing_page(
        self,
        text: str,
        page: models.DocumentPage,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг страницы чертежа — извлекает обозначение, название, размеры"""
        lines = text.split('\n') if text else []

        # Если есть text_blocks — используем их для точного определения
        blocks_text = []
        if text_blocks:
            blocks_text = [
                b.get('text', '').strip().replace('\n', ' ')
                for b in sorted(text_blocks, key=lambda b: (b.get('y0', 0), b.get('x0', 0)))
                if b.get('text', '').strip()
            ]
            search_source = blocks_text
        else:
            search_source = lines

        # Ищем обозначение чертежа
        designation = None
        for item in search_source[:15]:
            match = re.search(r'([А-ЯA-Z]{2,4}\.[\d\-]+\.\d+[\-\.\d]*)', item)
            if match:
                designation = match.group(1)
                break

        # Ищем название чертежа
        title = None
        for item in search_source[:20]:
            line_clean = item.strip()
            if len(line_clean) > 10 and not re.match(r'^[\d\s\.\-]+$', line_clean):
                if not designation or designation not in line_clean:
                    title = line_clean
                    break

        # Ищем размеры формата
        format_size = None
        for item in search_source:
            match = re.search(r'\b(А[0-4]|A[0-4])\b', item, re.IGNORECASE)
            if match:
                format_size = match.group(1).upper()
                break

        # Габаритные размеры
        dimensions = []
        for item in search_source:
            matches = re.findall(r'(\d+[\.,]?\d*)\s*[×xXх]\s*(\d+[\.,]?\d*)\s*[×xXх]\s*(\d+[\.,]?\d*)', item)
            for m in matches:
                dimensions.append('×'.join(m))

        # Масштаб
        scale = None
        for item in search_source:
            match = re.search(r'Масштаб[:\s]+([\d:\s]+)', item, re.IGNORECASE)
            if match:
                scale = match.group(1).strip()
                break

        return {
            "type": "drawing",
            "designation": designation,
            "title": title,
            "format_size": format_size,
            "scale": scale,
            "dimensions": dimensions,
            "text_preview": '\n'.join(lines[:10]),
        }

    def _parse_scheme_page(
        self,
        text: str,
        page: models.DocumentPage,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг схемы — извлекает элементы, позиции, обозначения"""
        lines = text.split('\n') if text else []

        # Используем text_blocks если есть
        search_text = []
        if text_blocks:
            search_text = [
                b.get('text', '').strip().replace('\n', ' ')
                for b in text_blocks
                if b.get('text', '').strip()
            ]
        else:
            search_text = lines

        # Ищем позиционные обозначения
        elements = []
        element_pattern = re.compile(r'\b([А-ЯA-Z]{1,3}\d{1,3})\b')

        for item in search_text:
            matches = element_pattern.findall(item)
            for match in matches:
                if match not in [e["designation"] for e in elements]:
                    elements.append({
                        "designation": match,
                        "context": item[:100]
                    })

        # Ищем типы элементов
        element_types = []
        type_keywords = ['двигатель', 'контактор', 'реле', 'выключатель', 'предохранитель',
                         'автомат', 'кнопка', 'лампа', 'резистор', 'трансформатор']
        for item in search_text:
            item_lower = item.lower()
            for keyword in type_keywords:
                if keyword in item_lower:
                    element_types.append({
                        "type": keyword,
                        "context": item[:100]
                    })

        # Ищем ссылки на другие листы
        sheet_refs = []
        for item in search_text:
            matches = re.findall(r'(?:лист|стр\.?|sheet)\s*(\d+)', item, re.IGNORECASE)
            for m in matches:
                sheet_refs.append(int(m))

        return {
            "type": "scheme",
            "elements_count": len(elements),
            "elements": elements[:50],
            "element_types": element_types[:20],
            "sheet_references": list(set(sheet_refs)),
            "text_preview": '\n'.join(lines[:10]),
        }

    def _parse_title_page(
        self,
        text: str,
        page: models.DocumentPage,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг титульного листа — извлекает метаданные документа"""
        lines = text.split('\n') if text else []

        # Используем text_blocks если есть
        search_text = []
        if text_blocks:
            search_text = [
                b.get('text', '').strip().replace('\n', ' ')
                for b in sorted(text_blocks, key=lambda b: (b.get('y0', 0), b.get('x0', 0)))
                if b.get('text', '').strip()
            ]
        else:
            search_text = lines

        # Ищем название проекта/документа
        title_candidates = [l.strip() for l in search_text[:15] if len(l.strip()) > 5]
        document_title = title_candidates[0] if title_candidates else None

        # Ищем шифр/код документа
        doc_code = None
        for item in search_text[:20]:
            match = re.search(r'([А-ЯA-Z]{2,4}[\-\.][\d\-]+[\-\.][\w\-]+)', item)
            if match:
                doc_code = match.group(1)
                break

        # Ищем организацию
        organization = None
        org_keywords = ['ООО', 'АО', 'ПАО', 'ЗАО', 'ИП', 'НИИ', 'университет', 'институт']
        for item in search_text:
            for keyword in org_keywords:
                if keyword in item:
                    organization = item.strip()
                    break
            if organization:
                break

        # Ищем дату
        date = None
        for item in search_text:
            match = re.search(r'(\d{2}[\.\-]\d{2}[\.\-]\d{4})', item)
            if match:
                date = match.group(1)
                break

        # Ищем фамилии (подписи)
        signatures = []
        for item in search_text:
            match = re.search(r'([А-Я][а-я]+\s+[А-Я]\.[А-Я]\.)', item)
            if match:
                signatures.append(match.group(1))

        return {
            "type": "title",
            "document_title": document_title,
            "document_code": doc_code,
            "organization": organization,
            "date": date,
            "signatures": list(set(signatures))[:10],
            "text_preview": '\n'.join(lines[:15]),
        }

    def _parse_other_page(
        self,
        text: str,
        page: models.DocumentPage,
        text_blocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Парсинг прочих страниц — просто текстовый preview"""
        lines = text.split('\n') if text else []
        result = {
            "type": "other",
            "text_preview": '\n'.join(lines[:20]),
            "line_count": len(lines),
            "char_count": len(text) if text else 0,
        }
        if text_blocks:
            result["blocks_count"] = len(text_blocks)
        return result

    # ───────────────────────────────────────────────
    #  Экспорт
    # ───────────────────────────────────────────────

    def export_to_json(self, output_path: str) -> str:
        """Экспорт структурированного документа в JSON"""
        data = self.parse_document()

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(output_path)

    def export_to_excel(self, output_path: str) -> str:
        """Экспорт в Excel — каждая категория на отдельном листе"""
        data = self.parse_document()
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            # Сводка
            summary = self._build_summary(data)
            pd.DataFrame([summary]).to_excel(writer, sheet_name='Сводка', index=False)

            # Спецификации — все строки
            spec_rows = self._extract_all_specification_rows(data)
            if spec_rows:
                pd.DataFrame(spec_rows).to_excel(writer, sheet_name='Спецификации', index=False)

            # Чертежи
            drawings = self._extract_drawings(data)
            if drawings:
                pd.DataFrame(drawings).to_excel(writer, sheet_name='Чертежи', index=False)

            # Схемы — элементы
            scheme_elements = self._extract_scheme_elements(data)
            if scheme_elements:
                pd.DataFrame(scheme_elements).to_excel(writer, sheet_name='Элементы_схем', index=False)

            # Титульные — метаданные
            titles = self._extract_titles(data)
            if titles:
                pd.DataFrame(titles).to_excel(writer, sheet_name='Титулы', index=False)

        return str(output_path)

    def _build_summary(self, data: Dict) -> Dict[str, Any]:
        pages = data.get("pages", {})
        categories = {}
        for p in pages.values():
            cat = p.get("category", "other")
            categories[cat] = categories.get(cat, 0) + 1

        return {
            "document_id": data["document_id"],
            "document_name": data["document_name"],
            "total_pages": data["total_pages"],
            "specification_pages": categories.get("specification", 0),
            "drawing_pages": categories.get("drawing", 0),
            "scheme_pages": categories.get("scheme", 0),
            "title_pages": categories.get("title", 0),
            "other_pages": categories.get("other", 0),
            "parsed_at": data["parsed_at"],
        }

    def _extract_all_specification_rows(self, data: Dict) -> List[Dict]:
        """
        Извлечь все строки спецификаций со всех страниц.
        Использует text_blocks_details для группировки по строкам таблицы.
        """
        rows = []
        
        for page_key, page_data in data.get("pages", {}).items():
            if page_data.get("category") != "specification":
                continue
            
            page_num = page_data.get("page_number")
            page_rows = page_data.get("data", {}).get("rows", [])
            columns = page_data.get("data", {}).get("columns", [])
            text_blocks = page_data.get("text_blocks_details", [])
            
            # Если есть распаршенные строки - используем их
            if page_rows and columns:
                for row in page_rows:
                    flat_row = {"Страница": page_num}
                    for col in columns:
                        flat_row[col["label"]] = row.get(col["key"], "")
                    rows.append(flat_row)
            
            # Если есть text_blocks_details - группируем по Y координате
            elif text_blocks:
                # Группируем блоки по Y с допуском 10px
                y_tolerance = 10
                rows_by_y = {}
                
                for block in text_blocks:
                    y0 = block.get('y0', 0)
                    # Находим ближайшую группу
                    found_group = None
                    for existing_y in rows_by_y.keys():
                        if abs(existing_y - y0) <= y_tolerance:
                            found_group = existing_y
                            break
                    
                    if found_group is not None:
                        rows_by_y[found_group].append(block)
                    else:
                        rows_by_y[y0] = [block]
                
                # Сортируем строки сверху вниз
                sorted_y = sorted(rows_by_y.keys())
                
                # Первая строка - заголовок
                header = None
                if sorted_y:
                    header_blocks = sorted(rows_by_y[sorted_y[0]], key=lambda b: b['x0'])
                    header = [b.get('text', '').strip() for b in header_blocks if b.get('text', '').strip()]
                
                # Остальные строки - данные таблицы
                for y in sorted_y[1:]:
                    row_blocks = sorted(rows_by_y[y], key=lambda b: b['x0'])
                    row_values = [b.get('text', '').strip() for b in row_blocks if b.get('text', '').strip()]
                    
                    if not row_values:
                        continue
                    
                    # Создаём строку с привязкой к заголовку
                    flat_row = {"Страница": page_num}
                    
                    if header:
                        for i, value in enumerate(row_values):
                            if i < len(header):
                                flat_row[header[i]] = value
                            else:
                                flat_row[f"Колонка_{i+1}"] = value
                    else:
                        # Без заголовка - нумеруем колонки
                        for i, value in enumerate(row_values):
                            flat_row[f"Колонка_{i+1}"] = value
                    
                    # Пропускаем строки-заголовки (содержат слова "Позиция", "Обозначение" и т.п.)
                    if any(kw in str(flat_row.values()) for kw in ['Позиция', 'Обозначение', 'Наименование', 'Кол', 'Прим']):
                        # Обновляем заголовок если это он
                        if 'Позиция' in str(row_values) or 'Обозначение' in str(row_values):
                            header = row_values
                            continue
                        continue
                    
                    rows.append(flat_row)
        
        return rows

    def _extract_drawings(self, data: Dict) -> List[Dict]:
        """Извлечь данные чертежей"""
        drawings = []
        for page_data in data.get("pages", {}).values():
            if page_data.get("category") == "drawing":
                d = page_data.get("data", {})
                drawings.append({
                    "Страница": page_data.get("page_number"),
                    "Обозначение": d.get("designation", ""),
                    "Название": d.get("title", ""),
                    "Формат": d.get("format_size", ""),
                    "Масштаб": d.get("scale", ""),
                    "Размеры": ", ".join(d.get("dimensions", [])),
                })
        return drawings

    def _extract_scheme_elements(self, data: Dict) -> List[Dict]:
        """Извлечь элементы схем"""
        elements = []
        for page_data in data.get("pages", {}).values():
            if page_data.get("category") == "scheme":
                page_num = page_data.get("page_number")
                for el in page_data.get("data", {}).get("elements", []):
                    elements.append({
                        "Страница": page_num,
                        "Обозначение": el.get("designation", ""),
                        "Контекст": el.get("context", ""),
                    })
        return elements

    def _extract_titles(self, data: Dict) -> List[Dict]:
        """Извлечь метаданные титульных страниц"""
        titles = []
        for page_data in data.get("pages", {}).values():
            if page_data.get("category") == "title":
                d = page_data.get("data", {})
                titles.append({
                    "Страница": page_data.get("page_number"),
                    "Название": d.get("document_title", ""),
                    "Шифр": d.get("document_code", ""),
                    "Организация": d.get("organization", ""),
                    "Дата": d.get("date", ""),
                    "Подписи": ", ".join(d.get("signatures", [])),
                })
        return titles

    def close(self):
        if self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# ───────────────────────────────────────────────
#  Функции-утилиты
# ───────────────────────────────────────────────

def parse_document_to_json(
    document_id: int,
    output_dir: str = 'output/documents',
    processed_dir: str = 'processed'
) -> str:
    """Обработать документ и сохранить в JSON"""
    with DocumentParser(document_id, processed_dir) as parser:
        doc_name = Path(parser.document.name).stem
        output_path = Path(output_dir) / f"{doc_name}_structured.json"
        return parser.export_to_json(str(output_path))


def parse_document_to_excel(
    document_id: int,
    output_dir: str = 'output/documents',
    processed_dir: str = 'processed'
) -> str:
    """Обработать документ и сохранить в Excel"""
    with DocumentParser(document_id, processed_dir) as parser:
        doc_name = Path(parser.document.name).stem
        output_path = Path(output_dir) / f"{doc_name}_structured.xlsx"
        return parser.export_to_excel(str(output_path))


def batch_parse_documents(
    project_id: Optional[int] = None,
    output_format: str = 'json',
    output_dir: str = 'output/documents',
    processed_dir: str = 'processed'
) -> List[str]:
    """Пакетная обработка всех документов проекта"""
    db = SessionLocal()
    output_files = []

    try:
        query = db.query(models.Document)
        if project_id:
            query = query.filter(models.Document.project_id == project_id)

        for doc in query.all():
            try:
                if output_format.lower() == 'excel':
                    path = parse_document_to_excel(doc.id, output_dir, processed_dir)
                else:
                    path = parse_document_to_json(doc.id, output_dir, processed_dir)
                output_files.append(path)
                print(f"OK Документ {doc.id}: {doc.name}")
            except Exception as e:
                print(f"ERROR Документ {doc.id}: {e}")
    finally:
        db.close()

    return output_files


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Использование: python document_parser.py <document_id> [json|excel]")
        sys.exit(1)

    doc_id = int(sys.argv[1])
    fmt = sys.argv[2] if len(sys.argv) > 2 else 'json'

    if fmt.lower() == 'excel':
        output = parse_document_to_excel(doc_id)
    else:
        output = parse_document_to_json(doc_id)

    print(f"Сохранено: {output}")
