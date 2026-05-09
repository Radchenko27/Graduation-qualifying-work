from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ... import crud, schemas, db, models
from ...dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.DrawingCalculationRead, status_code=status.HTTP_201_CREATED)
def create_calculation(
    calculation: schemas.DrawingCalculationCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Создать расчет элемента чертежа

    Требует аутентификации
    """
    # Проверка существования чертежа
    drawing = crud.Drawings.get(db, calculation.drawing_id)
    if drawing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Drawing not found"
        )
    
    calculation_data = calculation.model_dump()
    calculation_data["created_at"] = datetime.now()
    
    return crud.DrawingCalculations.create(db, calculation_data)


@router.get("/", response_model=List[schemas.DrawingCalculationRead])
def read_calculations(
    drawing_id: int = None,
    project_id: int = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список расчетов элементов чертежей

    Требует аутентификации
    """
    if drawing_id:
        calculations = db.query(models.DrawingCalculation).filter(
            models.DrawingCalculation.drawing_id == drawing_id
        ).offset(skip).limit(limit).all()
    elif project_id:
        calculations = db.query(models.DrawingCalculation).filter(
            models.DrawingCalculation.project_id == project_id
        ).offset(skip).limit(limit).all()
    else:
        calculations = crud.DrawingCalculations.get_multi(db, skip=skip, limit=limit)
    
    return calculations


@router.get("/{calculation_id}", response_model=schemas.DrawingCalculationRead)
def read_calculation(
    calculation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить расчет по ID

    Требует аутентификации
    """
    calculation = crud.DrawingCalculations.get(db, calculation_id)
    if calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found"
        )
    return calculation


@router.put("/{calculation_id}", response_model=schemas.DrawingCalculationRead)
def update_calculation(
    calculation_id: int,
    calculation: schemas.DrawingCalculationCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Обновить расчет элемента чертежа

    Требует аутентификации
    """
    db_calculation = crud.DrawingCalculations.get(db, calculation_id)
    if db_calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found"
        )
    
    calculation_data = calculation.model_dump()
    
    return crud.DrawingCalculations.update(db, db_calculation, calculation_data)


@router.delete("/{calculation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_calculation(
    calculation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить расчет элемента чертежа

    Требует аутентификации
    """
    db_calculation = crud.DrawingCalculations.get(db, calculation_id)
    if db_calculation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Calculation not found"
        )
    crud.DrawingCalculations.remove(db, calculation_id)
    return None
