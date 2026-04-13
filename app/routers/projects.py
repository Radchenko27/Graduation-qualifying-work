from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from .. import crud, schemas, db, models
from ..dependencies import get_current_user

router = APIRouter()


@router.post("/", response_model=schemas.ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    project: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Создать новый проект

    Требует аутентификации
    Текущий пользователь становится владельцем проекта
    """
    project_data = project.model_dump()
    return crud.Projects.create_with_owner(db, project_data, owner_id=current_user.id)


@router.get("/", response_model=List[schemas.ProjectRead])
def read_projects(
    skip: int = 0,
    limit: int = 100,
    category: str = None,  # 'my' - личные, 'shared' - иных пользователей
    search: str = None,    # Поиск по названию
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список проектов с возможностью фильтрации:
    - category='my' - только мои проекты
    - category='shared' - проекты, предоставленные мне
    - search - поиск по названию

    Требует аутентификации
    """
    if search:
        # Поиск по названию
        projects = crud.Projects.search_by_name(db, name=search, owner_id=current_user.id, skip=skip, limit=limit)
    elif category == 'my':
        # Только мои проекты
        projects = crud.Projects.get_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)
    elif category == 'shared':
        # Проекты, предоставленные мне
        projects = crud.Projects.get_shared_with_user(db, user_id=current_user.id, skip=skip, limit=limit)
    else:
        # Все проекты (мои + предоставленные)
        my_projects = crud.Projects.get_by_owner(db, owner_id=current_user.id)
        shared_projects = crud.Projects.get_shared_with_user(db, user_id=current_user.id)
        # Объединяем и убираем дубликаты
        all_projects = {p.id: p for p in my_projects + shared_projects}
        projects = list(all_projects.values())[skip:skip+limit]
    
    return projects


@router.get("/{project_id}", response_model=schemas.ProjectRead)
def read_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить проект по ID

    Требует аутентификации
    """
    project = crud.Projects.get(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return project


@router.put("/{project_id}", response_model=schemas.ProjectRead)
def update_project(
    project_id: int,
    project: schemas.ProjectCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Обновить данные проекта

    Требует аутентификации
    """
    db_project = crud.Projects.get(db, project_id)
    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    project_data = project.model_dump()
    
    return crud.Projects.update(db, db_project, project_data)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить проект

    Требует аутентификации
    """
    db_project = crud.Projects.get(db, project_id)
    if db_project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    crud.Projects.remove(db, project_id)
    return None
