"""
API router для управления материалами
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import json
from pathlib import Path

from ... import crud
from ...db import get_db
from ...schemas import MaterialCreate, MaterialResponse, MaterialBatchImport
from ...utils.pdf_parser import PDFDataExtractor, batch_parse_processed_files
from ...dependencies import get_current_user

router = APIRouter()


@router.post("/import-from-json", response_model=List[MaterialResponse])
async def import_materials_from_json(
    json_file_path: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Импортировать материалы из обработанного JSON файла
    
    Args:
        json_file_path: Путь к JSON файлу (относительно корня проекта)
    """
    try:
        # Извлечь материалы из JSON
        extractor = PDFDataExtractor(json_file_path)
        materials_data = extractor.extract_specifications()
        
        if not materials_data:
            raise HTTPException(status_code=404, detail="Материалы не найдены в файле")
        
        # Создать материалы в базе
        created_materials = []
        for mat_data in materials_data:
            # Проверить, существует ли такой материал
            existing = db.query(crud.Material).filter(
                crud.Material.name == mat_data['name'],
                crud.Material.mark == mat_data.get('mark', '')
            ).first()
            
            if existing:
                created_materials.append(MaterialResponse.model_validate(existing))
            else:
                # Создать новый материал
                material = crud.Material.create(db, **mat_data)
                created_materials.append(MaterialResponse.model_validate(material))
        
        return created_materials
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="JSON файл не найден")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка импорта: {str(e)}")


@router.post("/batch-import", response_model=List[MaterialResponse])
async def batch_import_materials(
    input_dir: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Пакетно импортировать материалы из всех JSON файлов в директории
    
    Args:
        input_dir: Директория с JSON файлами (например, "processed")
    """
    try:
        # Пакетный парсинг
        all_materials = batch_parse_processed_files(input_dir)
        
        if not all_materials:
            raise HTTPException(status_code=404, detail="Материалы не найдены в директории")
        
        # Создать материалы в базе
        created_materials = []
        for mat_data in all_materials:
            existing = db.query(crud.Material).filter(
                crud.Material.name == mat_data['name'],
                crud.Material.mark == mat_data.get('mark', '')
            ).first()
            
            if not existing:
                material = crud.Material.create(db, **mat_data)
                created_materials.append(MaterialResponse.model_validate(material))
            else:
                created_materials.append(MaterialResponse.model_validate(existing))
        
        return created_materials
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка пакетного импорта: {str(e)}")


@router.get("/extracted/{doc_id}", response_model=List[dict])
async def get_extracted_materials(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Получить извлечённые материалы для конкретного документа
    
    Args:
        doc_id: ID документа
    """
    # Получить документ
    doc = crud.Documents.get(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    # Проверить наличие обработанного JSON
    json_path = Path(f"processed/{doc.name}_processed.json")
    if not json_path.exists():
        raise HTTPException(
            status_code=404, 
            detail=f"Обработанный JSON файл не найден: {json_path}"
        )
    
    # Извлечь материалы
    extractor = PDFDataExtractor(str(json_path))
    materials = extractor.extract_specifications()
    
    return materials


@router.post("/parse-document/{doc_id}")
async def parse_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Запустить парсинг документа (асинхронно)
    
    Args:
        doc_id: ID документа
    """
    # TODO: Реализовать фоновую задачу парсинга
    # Для этого нужно добавить очередь задач (Celery/RQ)
    
    raise HTTPException(
        status_code=501, 
        detail="Фоновый парсинг пока не реализован. Используйте импорт из JSON напрямую."
    )


@router.get("/types", response_model=List[str])
async def get_material_types():
    """
    Получить список типов материалов
    
    Returns:
        Список типов: ['cable', 'fixture', 'device', 'general']
    """
    return ['cable', 'fixture', 'device', 'general', 'pipe', 'conduit', 'panel']


@router.get("/search", response_model=List[MaterialResponse])
async def search_materials(
    q: str,
    type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Поиск материалов по названию или марке
    
    Args:
        q: Строка поиска
        type: Фильтр по типу (опционально)
    """
    query = db.query(crud.Material)
    
    if q:
        search_pattern = f"%{q}%"
        query = query.filter(
            (crud.Material.name.ilike(search_pattern)) |
            (crud.Material.mark.ilike(search_pattern))
        )
    
    if type:
        query = query.filter(crud.Material.type == type)
    
    materials = query.all()
    return [MaterialResponse.model_validate(m) for m in materials]
