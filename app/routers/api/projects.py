from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ... import crud, schemas, db, models
from ...dependencies import get_current_user

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


@router.post("/{project_id}/share", response_model=schemas.ProjectShareRead, status_code=status.HTTP_201_CREATED)
def share_project(
    project_id: int,
    share_data: schemas.ProjectShareCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Поделиться проектом с пользователем

    Требует аутентификации
    Только владелец проекта может делиться
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Проверка прав доступа (только владелец может делиться)
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец проекта может делиться им"
        )
    
    # Проверка существования пользователя
    user_to_share = crud.Users.get(db, share_data.shared_with_id)
    if user_to_share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Проверка, что не пытаемся поделиться с собой
    if share_data.shared_with_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя поделиться проектом с собой"
        )
    
    # Проверка, что пользователь ещё не имеет доступа
    existing_share = db.query(models.ProjectShare).filter(
        models.ProjectShare.project_id == project_id,
        models.ProjectShare.shared_with_id == share_data.shared_with_id
    ).first()
    
    if existing_share:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У пользователя уже есть доступ к этому проекту"
        )
    
    # Создаём запись о доступе
    share_data_dict = share_data.model_dump()
    share_data_dict['owner_id'] = current_user.id
    
    return crud.ProjectShares.create(db, share_data_dict)


@router.get("/{project_id}/shares", response_model=List[schemas.ProjectShareRead])
def get_project_shares(
    project_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список пользователей с доступом к проекту

    Требует аутентификации
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Проверка прав доступа
    if not crud.ProjectUsers.check_access(db, current_user.id, project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    shares = db.query(models.ProjectShare).filter(
        models.ProjectShare.project_id == project_id
    ).all()
    
    return shares


@router.delete("/{project_id}/shares/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_project_access(
    project_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Отозвать доступ пользователя к проекту

    Требует аутентификации
    Только владелец проекта может отзывать доступ
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Проверка прав доступа (только владелец может отзывать)
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Только владелец проекта может отзывать доступ"
        )
    
    # Поиск записи о доступе
    share = db.query(models.ProjectShare).filter(
        models.ProjectShare.project_id == project_id,
        models.ProjectShare.shared_with_id == user_id
    ).first()
    
    if share is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Доступ пользователя не найден"
        )
    
    # Удаляем доступ
    db.delete(share)
    db.commit()
    return None
