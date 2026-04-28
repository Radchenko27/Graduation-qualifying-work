from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ... import crud, schemas, db, models
from ...dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.EstimateRead, status_code=status.HTTP_201_CREATED)
def create_estimate(
    estimate: schemas.EstimateCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Создать новую смету

    Требует аутентификации
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, estimate.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    estimate_data = estimate.model_dump()
    
    return crud.Estimates.create_with_defaults(db, estimate_data)


@router.get("/", response_model=List[schemas.EstimateRead])
def read_estimates(
    project_id: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список смет

    Требует аутентификации
    """
    if project_id:
        estimates = db.query(models.Estimate).filter(
            models.Estimate.project_id == project_id
        ).offset(skip).limit(limit).all()
    else:
        estimates = crud.Estimates.get_multi(db, skip=skip, limit=limit)
    
    return estimates


@router.get("/{estimate_id}", response_model=schemas.EstimateWithItemsRead)
def read_estimate(
    estimate_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить смету по ID с элементами

    Требует аутентификации
    """
    estimate = crud.Estimates.get(db, estimate_id)
    if estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found"
        )
    return estimate


@router.post("/{estimate_id}/items", response_model=schemas.EstimateItemRead, status_code=status.HTTP_201_CREATED)
def add_estimate_item(
    estimate_id: int,
    item: schemas.EstimateItemCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Добавить элемент в смету

    Требует аутентификации
    """
    # Проверка существования сметы
    estimate = crud.Estimates.get(db, estimate_id)
    if estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found"
        )
    
    # Проверка существования расчета чертежа
    calculation = crud.DrawingCalculations.get(db, item.drawing_calculation_id)
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing calculation not found"
        )
    
    # Создаем элемент сметы
    item_data = item.model_dump()
    item_data["total_cost"] = item.quantity * item.unit_cost
    
    new_item = crud.EstimateItems.create(db, item_data)
    
    # Пересчитываем итоги сметы
    crud.Estimates.update_totals(db, estimate_id)
    
    return new_item


@router.delete("/{estimate_id}/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_estimate_item(
    estimate_id: int,
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить элемент из сметы

    Требует аутентификации
    """
    item = crud.EstimateItems.get(db, item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate item not found"
        )
    
    if item.estimate_id != estimate_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item does not belong to this estimate"
        )
    
    crud.EstimateItems.remove(db, item_id)
    
    # Пересчитываем итоги сметы
    crud.Estimates.update_totals(db, estimate_id)
    
    return None


@router.post("/merge", response_model=schemas.EstimateRead, status_code=status.HTTP_201_CREATED)
def merge_estimates(
    merge_data: schemas.EstimateMerge,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Объединить несколько смет в одну

    Требует аутентификации
    """
    if len(merge_data.estimate_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 estimates to merge"
        )
    
    return crud.Estimates.merge_estimates(
        db, 
        name=merge_data.name, 
        description=merge_data.description or "",
        estimate_ids=merge_data.estimate_ids,
        user_id=current_user.id
    )


@router.delete("/{estimate_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_estimate(
    estimate_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить смету

    Требует аутентификации
    """
    db_estimate = crud.Estimates.get(db, estimate_id)
    if db_estimate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Estimate not found"
        )
    crud.Estimates.remove(db, estimate_id)
    return None
