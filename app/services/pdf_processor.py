"""
Сервис для обработки PDF файлов строительных чертежей
"""
import fitz  # PyMuPDF
import cv2
import numpy as np
from PIL import Image
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Класс для обработки PDF файлов строительных чертежей"""
    
    def __init__(self, pdf_path: str):
        """
        Инициализация процессора PDF
        
        Args:
            pdf_path: Путь к PDF файлу
        """
        self.pdf_path = Path(pdf_path)
        self.doc = None
        self._load_pdf()
    
    def _load_pdf(self):
        """Загрузка PDF документа"""
        try:
            self.doc = fitz.open(str(self.pdf_path))
            logger.info(f"PDF загружен: {self.pdf_path}, страниц: {self.doc.page_count}")
        except Exception as e:
            logger.error(f"Ошибка загрузки PDF: {e}")
            raise
    
    def get_page_count(self) -> int:
        """Получить количество страниц"""
        return self.doc.page_count if self.doc else 0
    
    def get_metadata(self) -> Dict:
        """
        Извлечь метаданные PDF
        
        Returns:
            Словарь с метаданными
        """
        if not self.doc:
            return {}
        
        metadata = self.doc.metadata
        metadata.update({
            "page_count": self.doc.page_count,
            "file_size": self.pdf_path.stat().st_size,
            "file_name": self.pdf_path.name,
            "created_at": datetime.fromtimestamp(self.pdf_path.stat().st_ctime).isoformat(),
            "modified_at": datetime.fromtimestamp(self.pdf_path.stat().st_mtime).isoformat()
        })
        
        return metadata
    
    def extract_text_from_page(self, page_num: int) -> str:
        """
        Извлечь текст с конкретной страницы
        
        Args:
            page_num: Номер страницы (0-based)
            
        Returns:
            Текст страницы
        """
        if not self.doc or page_num >= self.doc.page_count:
            return ""
        
        page = self.doc[page_num]
        text = page.get_text()
        return text
    
    def extract_all_text(self) -> Dict[int, str]:
        """
        Извлечь текст со всех страниц
        
        Returns:
            Словарь {номер_страницы: текст}
        """
        if not self.doc:
            return {}
        
        text_dict = {}
        for page_num in range(self.doc.page_count):
            text_dict[page_num] = self.extract_text_from_page(page_num)
        
        return text_dict
    
    def extract_images_from_page(self, page_num: int, output_dir: Optional[Path] = None) -> List[Dict]:
        """
        Извлечь изображения с конкретной страницы
        
        Args:
            page_num: Номер страницы (0-based)
            output_dir: Директория для сохранения изображений
            
        Returns:
            Список словарей с информацией об изображениях
        """
        if not self.doc or page_num >= self.doc.page_count:
            return []
        
        page = self.doc[page_num]
        image_list = page.get_images()
        images_info = []
        
        for img_index, img in enumerate(image_list):
            xref = img[0]
            base_image = self.doc.extract_image(xref)
            image_data = base_image["image"]
            
            image_info = {
                "page_num": page_num,
                "image_index": img_index,
                "xref": xref,
                "width": base_image.get("width", 0),
                "height": base_image.get("height", 0),
                "format": base_image.get("ext", "unknown"),
                "size": len(image_data)
            }
            
            if output_dir:
                output_dir = Path(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                
                image_filename = f"page_{page_num}_image_{img_index}.{base_image.get('ext', 'png')}"
                image_path = output_dir / image_filename
                
                with open(image_path, "wb") as img_file:
                    img_file.write(image_data)
                
                image_info["saved_path"] = str(image_path)
            
            images_info.append(image_info)
        
        return images_info
    
    def convert_page_to_image(self, page_num: int, output_dir: Optional[Path] = None, 
                             zoom: float = 2.0) -> Optional[str]:
        """
        Конвертировать страницу PDF в изображение
        
        Args:
            page_num: Номер страницы (0-based)
            output_dir: Директория для сохранения изображений
            zoom: Коэффициент масштабирования
            
        Returns:
            Путь к сохраненному изображению или None
        """
        if not self.doc or page_num >= self.doc.page_count:
            return None
        
        page = self.doc[page_num]
        
        # Создаем матрицу трансформации для масштабирования
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Конвертируем в numpy array
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        img_np = np.array(img)
        
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            image_filename = f"page_{page_num}.png"
            image_path = output_dir / image_filename
            
            # Сохраняем изображение
            cv2.imwrite(str(image_path), cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR))
            
            logger.info(f"Страница {page_num} сохранена как изображение: {image_path}")
            return str(image_path)
        
        return None
    
    def convert_all_pages_to_images(self, output_dir: Path, zoom: float = 2.0) -> List[str]:
        """
        Конвертировать все страницы PDF в изображения
        
        Args:
            output_dir: Директория для сохранения изображений
            zoom: Коэффициент масштабирования
            
        Returns:
            Список путей к сохраненным изображениям
        """
        if not self.doc:
            return []
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        image_paths = []
        for page_num in range(self.doc.page_count):
            image_path = self.convert_page_to_image(page_num, output_dir, zoom)
            if image_path:
                image_paths.append(image_path)
        
        return image_paths
    
    def detect_drawing_elements(self, page_num: int) -> Dict:
        """
        Обнаружить элементы чертежа на странице (линии, прямоугольники, круги и т.д.)
        
        Args:
            page_num: Номер страницы (0-based)
            
        Returns:
            Словарь с обнаруженными элементами
        """
        if not self.doc or page_num >= self.doc.page_count:
            return {}
        
        page = self.doc[page_num]
        drawings = page.get_drawings()
        
        elements = {
            "lines": [],
            "rects": [],
            "circles": [],
            "curves": []
        }
        
        for drawing in drawings:
            for item in drawing["items"]:
                item_type = item[0]
                data = item[1]
                
                if item_type == "l":  # line
                    coords = []
                    if isinstance(data, (tuple, list)):
                        for d in data:
                            if hasattr(d, 'x') and hasattr(d, 'y'):
                                coords.extend([float(d.x), float(d.y)])
                            elif isinstance(d, (int, float)):
                                coords.append(float(d))
                    if len(coords) >= 4:
                        elements["lines"].append({
                            "x1": coords[0], "y1": coords[1],
                            "x2": coords[2], "y2": coords[3]
                        })
                
                elif item_type == "re":  # rect
                    if hasattr(data, 'x0'):
                        elements["rects"].append({
                            "x0": float(data.x0), "y0": float(data.y0),
                            "x1": float(data.x1), "y1": float(data.y1)
                        })
                    elif isinstance(data, (tuple, list)) and len(data) >= 4:
                        elements["rects"].append({
                            "x0": float(data[0]), "y0": float(data[1]),
                            "x1": float(data[2]), "y1": float(data[3])
                        })
                
                elif item_type in ("c", "qu"):  # curve / quad
                    coords = []
                    if isinstance(data, (tuple, list)):
                        for d in data:
                            if hasattr(d, 'x') and hasattr(d, 'y'):
                                coords.extend([float(d.x), float(d.y)])
                            elif isinstance(d, (int, float)):
                                coords.append(float(d))
                    # Group into points
                    points = [{"x": coords[i], "y": coords[i+1]} 
                             for i in range(0, len(coords)-1, 2)]
                    elements["curves"].append(points)
        
        return elements
    
    def analyze_page_structure(self, page_num: int) -> Dict:
        """
        Анализировать структуру страницы (блоки текста, таблицы, изображения)
        
        Args:
            page_num: Номер страницы (0-based)
            
        Returns:
            Словарь с информацией о структуре страницы
        """
        if not self.doc or page_num >= self.doc.page_count:
            return {}
        
        page = self.doc[page_num]
        
        # Получаем блоки текста
        text_blocks = page.get_text("blocks")
        
        # Получаем таблицы (создаём textpage явно для избежания ошибки)
        try:
            textpage = page.get_textpage()
            tables = page.find_tables(textpage=textpage)
            table_count = len(tables.tables)
        except Exception:
            table_count = 0
        
        structure = {
            "page_num": page_num,
            "text_blocks": len(text_blocks),
            "tables": table_count,
            "images": len(page.get_images()),
            "width": page.rect.width,
            "height": page.rect.height,
            "text_blocks_details": [
                {
                    "x0": block[0],
                    "y0": block[1],
                    "x1": block[2],
                    "y1": block[3],
                    "text": block[4][:100] if len(block[4]) > 100 else block[4],  # Первые 100 символов
                    "block_type": block[6]
                }
                for block in text_blocks
            ]
        }
        
        return structure
    
    def process_document(
        self,
        output_dir: Path,
        extract_images: bool = False,
        extract_text: bool = True,
        analyze_structure: bool = True,  # По умолчанию True для text_blocks_details
        zoom: float = 1.0
    ) -> Dict:
        """
        Полная обработка документа с параметрами управления.
        Всегда сохраняет text_blocks_details для геометрического парсинга.

        Args:
            output_dir: Директория для сохранения результатов
            extract_images: Конвертировать страницы в изображения
            extract_text: Извлекать текст из страниц
            analyze_structure: Анализировать структуру страниц (всегда True)
            zoom: Коэффициент масштабирования для изображений
            
        Returns:
            Словарь с результатами обработки
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Всегда анализируем структуру для text_blocks_details
        analyze_structure = True
        
        results = {
            "metadata": self.get_metadata(),
            "text": {},
            "structure": {},
            "images_dir": str(output_dir / "images") if extract_images else None,
            "pages": [],
            "options": {
                "extract_images": extract_images,
                "extract_text": extract_text,
                "analyze_structure": analyze_structure,
                "zoom": zoom
            }
        }
        
        # Извлекаем текст со всех страниц если требуется
        if extract_text:
            results["text"] = self.extract_all_text()

        # Конвертируем все страницы в изображения если требуется
        if extract_images:
            self.convert_all_pages_to_images(output_dir / "images", zoom=zoom)

        # Анализируем структуру КАЖДОЙ страницы (всегда)
        for page_num in range(self.doc.page_count):
            page_info = {
                "page_num": page_num
            }
            
            # Всегда получаем структуру с text_blocks_details
            page_structure = self.analyze_page_structure(page_num)
            drawing_elements = self.detect_drawing_elements(page_num)
            page_info["structure"] = page_structure
            page_info["drawing_elements"] = drawing_elements
            results["structure"][page_num] = page_structure

            if extract_text:
                page_info["text"] = self.extract_text_from_page(page_num)

            results["pages"].append(page_info)

        # Сохраняем результаты в JSON
        # Проверяем имя PDF - если начинается с документа ID, используем его
        stem = self.pdf_path.stem
        if stem.startswith("temp_reprocess"):
            # Временный файл - используем имя из parent директории
            json_output = output_dir / f"{output_dir.name}_processed.json"
        else:
            json_output = output_dir / f"{stem}_processed.json"
        
        with open(json_output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Обработка завершена. Результаты сохранены в: {json_output}")
        
        return results
    
    def close(self):
        """Закрыть PDF документ"""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


import io  # Добавьте этот импорт в начало файла
