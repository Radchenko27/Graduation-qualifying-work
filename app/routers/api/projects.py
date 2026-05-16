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
    from datetime import date
    project_data = project.model_dump()
    project_data['created_at'] = date.today()
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
    - search - поиск по названию (во всех доступных проектах)

    Требует аутентификации
    """
    if search:
        # Поиск по названию во всех доступных проектах (мои + общие)
        projects = crud.Projects.search_by_name(db, name=search, user_id=current_user.id, skip=skip, limit=limit)
        # Добавляем категорию для каждого проекта
        for p in projects:
            if p.owner_id == current_user.id:
                p.category = 'my'
            else:
                p.category = 'shared'
    elif category == 'my':
        # Только мои проекты
        projects = crud.Projects.get_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)
        for p in projects:
            p.category = 'my'
    elif category == 'shared':
        # Проекты, предоставленные мне
        projects = crud.Projects.get_shared_with_user(db, user_id=current_user.id, skip=skip, limit=limit)
        for p in projects:
            p.category = 'shared'
    else:
        # Все проекты (мои + предоставленные)
        my_projects = crud.Projects.get_by_owner(db, owner_id=current_user.id)
        shared_projects = crud.Projects.get_shared_with_user(db, user_id=current_user.id)
        
        # Добавляем категорию для каждого проекта
        for p in my_projects:
            p.category = 'my'
        for p in shared_projects:
            p.category = 'shared'
        
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
    try:
        print(f"DEBUG read_project: Fetching project {project_id} for user {current_user.id}")
        project = crud.Projects.get(db, project_id)
        if project is None:
            print(f"DEBUG read_project: Project {project_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        print(f"DEBUG read_project: Project found: {project.id} - {project.name}")
        return project
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"ERROR in read_project: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения проекта: {str(e)}"
        )


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


@router.get("/{project_id}/shares")
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
    
    # Проверка прав доступа (владелец или участник)
    has_access = (project.owner_id == current_user.id) or crud.ProjectUsers.check_access(db, current_user.id, project_id)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    # Получаем shares с информацией о владельце
    shares = db.query(models.ProjectShare).filter(
        models.ProjectShare.project_id == project_id
    ).all()
    
    # Добавляем информацию о владельце и пользователе, которому предоставлен доступ
    result = []
    for share in shares:
        owner = crud.Users.get(db, share.owner_id)
        shared_with = crud.Users.get(db, share.shared_with_id)
        share_dict = {
            "id": share.id,
            "project_id": share.project_id,
            "shared_with_id": share.shared_with_id,
            "access_level": share.access_level,
            "owner_id": share.owner_id,
            "shared_at": share.shared_at,
            "owner_username": owner.username if owner else None,
            "owner_email": owner.email if owner else None,
            "shared_with_username": shared_with.username if shared_with else None,
            "shared_with_email": shared_with.email if shared_with else None,
            "shared_with_first_name": shared_with.first_name if shared_with else None,
            "shared_with_last_name": shared_with.last_name if shared_with else None
        }
        result.append(share_dict)
    
    return result


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
