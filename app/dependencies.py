from fastapi import Depends, HTTPException, status, Header, Cookie
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from . import db, models, crud


def get_auth_session(
    session_key: str = Header(None, alias="X-Session-Key"),  # Для обратной совместимости
    session_key_cookie: str = Cookie(None, alias="session_key"),  # Из cookie
    db_session: Session = Depends(db.get_db)
) -> models.AuthSession:
    """
    Проверка сессии авторизации по ключу
    
    Приоритет: cookie, затем заголовок X-Session-Key

    Args:
        session_key: Ключ сессии из заголовка X-Session-Key (опционально)
        session_key_cookie: Ключ сессии из cookie (опционально)
        db_session: Сессия базы данных
        
    Returns:
        Объект AuthSession если сессия валидна
        
    Raises:
        HTTPException: Если сессия не найдена или истекла
    """
    # Приоритет: cookie, затем заголовок
    key = session_key_cookie or session_key

    if not key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session key not found in cookie or header"
        )
    
    auth_session = db_session.query(models.AuthSession).filter(
        models.AuthSession.session_key == key
    ).first()
    
    if not auth_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session key"
        )

    if datetime.utcnow() > auth_session.expires_at:
        # Удаляем истекшую сессию
        db_session.delete(auth_session)
        db_session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired"
        )

    return auth_session


def get_current_user(
    auth_session: models.AuthSession = Depends(get_auth_session),
    db_session: Session = Depends(db.get_db)
) -> models.User:
    """
    Получить текущего пользователя из сессии
    
    Args:
        auth_session: Объект AuthSession
        db_session: Сессия базы данных
        
    Returns:
        Объект User
        
    Raises:
        HTTPException: Если пользователь не найден
    """
    user = crud.Users.get_by_id(db_session, auth_session.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Получить текущего активного пользователя
    Можно добавить проверку на статус активности пользователя
    
    Args:
        current_user: Объект User
        
    Returns:
        Объект User
    """
    return current_user


def generate_session_key() -> str:
    """
    Сгенерировать уникальный ключ сессии
    
    Returns:
        Уникальный ключ сессии
    """
    import secrets
    return secrets.token_urlsafe(32)


def create_auth_session(
    user_id: int,
    db_session: Session,
    expires_hours: int = 24
) -> models.AuthSession:
    """
    Создать сессию авторизации
    
    Args:
        user_id: ID пользователя
        db_session: Сессия базы данных
        expires_hours: Время жизни сессии в часах
        
    Returns:
        Объект AuthSession
    """
    session_key = generate_session_key()
    now = datetime.utcnow()
    expires_at = now + timedelta(hours=expires_hours)
    
    auth_session = models.AuthSession(
        user_id=user_id,
        session_key=session_key,
        created_at=now,
        expires_at=expires_at
    )
    
    db_session.add(auth_session)
    db_session.commit()
    db_session.refresh(auth_session)
    
    return auth_session


def revoke_auth_session(session_key: str, db_session: Session) -> bool:
    """
    Отозвать сессию авторизации (выход)
    
    Args:
        session_key: Ключ сессии
        db_session: Сессия базы данных
        
    Returns:
        True если сессия была удалена, False если не найдена
    """
    auth_session = db_session.query(models.AuthSession).filter(
        models.AuthSession.session_key == session_key
    ).first()
    
    if auth_session:
        db_session.delete(auth_session)
        db_session.commit()
        return True
    
    return False


def revoke_all_user_sessions(user_id: int, db_session: Session) -> int:
    """
    Отозвать все сессии пользователя
    
    Args:
        user_id: ID пользователя
        db_session: Сессия базы данных
        
    Returns:
        Количество удаленных сессий
    """
    count = db_session.query(models.AuthSession).filter(
        models.AuthSession.user_id == user_id
    ).delete()
    db_session.commit()
    return count


def get_current_user_optional(
    session_key: str = Header(None, alias="X-Session-Key"),
    session_key_cookie: str = Cookie(None, alias="session_key"),
    db_session: Session = Depends(db.get_db)
) -> models.User | None:
    """
    Получить текущего пользователя, если сессия валидна
    Возвращает None если сессии нет или она невалидна (не выбрасывает ошибку)
    
    Args:
        session_key: Ключ сессии из заголовка
        session_key_cookie: Ключ сессии из cookie
        db_session: Сессия базы данных
        
    Returns:
        Объект User или None
    """
    key = session_key_cookie or session_key
    
    if not key:
        return None
    
    auth_session = db_session.query(models.AuthSession).filter(
        models.AuthSession.session_key == key
    ).first()
    
    if not auth_session:
        return None
    
    if datetime.utcnow() > auth_session.expires_at:
        return None
    
    user = crud.Users.get_by_id(db_session, auth_session.user_id)
    return user
