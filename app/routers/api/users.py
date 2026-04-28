from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from ... import crud, schemas, db, models
from ...dependencies import (
    create_auth_session,
    revoke_auth_session,
    revoke_all_user_sessions,
    get_current_user
)

router = APIRouter()


@router.post("/register", response_model=schemas.UserRead, status_code=status.HTTP_201_CREATED)
def register(
    user: schemas.UserCreate,
    response: Response,
    db: Session = Depends(db.get_db)
):
    """
    Регистрация нового пользователя

    Не требует аутентификации

    Устанавливает cookie с session_key
    """
    # Проверка существования username
    existing_user = crud.Users.get_by_username(db, user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Создаем пользователя с хешированным паролем
    user_data = user.model_dump()
    user_data.pop("password")  # Пароль будет хеширован в методе create_with_password
    new_user = crud.Users.create_with_password(db, user_data, user.password)

    # Создаем сессию авторизации
    auth_session = create_auth_session(new_user.id, db)

    # Устанавливаем cookie с session_key
    response.set_cookie(
        key="session_key",
        value=auth_session.session_key,
        httponly=True,  # Защита от XSS (недоступен через JavaScript)
        secure=False,    # Для разработки. В production: True
        samesite="lax",  # Защита от CSRF
        max_age=86400    # 24 часа в секундах
    )

    return new_user


@router.post("/login", response_model=schemas.AuthSessionRead)
def login(
    credentials: schemas.AuthSessionCreate,
    response: Response,
    db: Session = Depends(db.get_db)
):
    """
    Авторизация пользователя

    Не требует аутентификации

    Returns:
        Сессию авторизации с ключом
    Устанавливает cookie с session_key
    """
    # Проверяем существование пользователя
    user = crud.Users.get_by_username(db, credentials.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Проверяем пароль
    if not crud.Users.verify_password(user, credentials.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )

    # Создаем сессию авторизации
    auth_session = create_auth_session(user.id, db)

    # Устанавливаем cookie с session_key
    response.set_cookie(
        key="session_key",
        value=auth_session.session_key,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=86400
    )

    return auth_session


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Выход из системы (удаление текущей сессии)

    Требует аутентификации
    Удаляет cookie с session_key
    """
    # Удаляем все сессии пользователя (или можно только текущую)
    revoke_all_user_sessions(current_user.id, db)

    # Удаляем cookie
    response.delete_cookie(
        key="session_key",
        httponly=True,
        secure=False,
        samesite="lax"
    )

    return None


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удаление аккаунта текущего пользователя

    Требует аутентификации
    Удаляет пользователя и все связанные данные
    """
    # Удаляем все сессии пользователя
    revoke_all_user_sessions(current_user.id, db)

    # Удаляем пользователя
    success = crud.Users.delete_user(db, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return None


@router.get("/me", response_model=schemas.UserRead)
def get_current_user_info(
    current_user: models.User = Depends(get_current_user)
):
    """
    Получить информацию о текущем пользователе

    Требует аутентификации
    """
    return current_user


@router.put("/me", response_model=schemas.UserRead)
def update_current_user(
    user_update: schemas.UserBase,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Обновить данные текущего пользователя

    Требует аутентификации
    """
    user_data = user_update.model_dump()
    updated_user = crud.Users.update(db, current_user, user_data)
    return updated_user


# Остальные эндпоинты для работы с пользователями (требуют аутентификации)

@router.get("/", response_model=List[schemas.UserRead])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список пользователей

    Требует аутентификации
    """
    users = crud.Users.get_multi(db, skip=skip, limit=limit)
    return users


@router.get("/search", response_model=List[schemas.UserRead])
def search_users(
    q: str,
    skip: int = 0,
    limit: int = 20,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Поиск пользователя по username или ФИО

    Требует аутентификации
    """
    users = crud.Users.search(db, query=q, skip=skip, limit=limit)
    return users


@router.get("/{user_id}", response_model=schemas.UserRead)
def read_user(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить пользователя по ID

    Требует аутентификации
    """
    user = crud.Users.get(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
