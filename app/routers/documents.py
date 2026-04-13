from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from .. import crud, schemas, db, models
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    document: schemas.DocumentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Создать новый документ

    Требует аутентификации
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, document.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    document_data = document.model_dump()
    if document_data.get("created_at") is None:
        document_data["created_at"] = date.today()
    
    return crud.Documents.create(db, document_data)


@router.get("/", response_model=List[schemas.DocumentRead])
def read_documents(
    project_id: int = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список документов с возможностью фильтрации:
    - project_id - документы конкретного проекта
    - category - категория документа

    Требует аутентификации
    """
    if project_id:
        if category:
            documents = crud.Documents.get_by_category(db, project_id=project_id, category=category, skip=skip, limit=limit)
        else:
            documents = crud.Documents.get_by_project(db, project_id=project_id, skip=skip, limit=limit)
    else:
        documents = crud.Documents.get_multi(db, skip=skip, limit=limit)
    return documents


@router.get("/{document_id}", response_model=schemas.DocumentRead)
def read_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить документ по ID

    Требует аутентификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document


@router.put("/{document_id}", response_model=schemas.DocumentRead)
def update_document(
    document_id: int,
    document: schemas.DocumentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Обновить данные документа

    Требует аутентификации
    """
    db_document = crud.Documents.get(db, document_id)
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    document_data = document.model_dump()
    
    return crud.Documents.update(db, db_document, document_data)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить документ

    Требует аутентификации
    """
    db_document = crud.Documents.get(db, document_id)
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    crud.Documents.remove(db, document_id)
    return None
