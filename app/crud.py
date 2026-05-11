from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from typing import Type, TypeVar, Generic, List, Optional
from datetime import datetime, date

from . import models
from .services.minio_client import minio_client

ModelType = TypeVar("ModelType", bound=models.Base)

class CRUDBase(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: int) -> Optional[ModelType]:
        return db.get(self.model, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100) -> List[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        return list(db.execute(stmt).scalars())

    def create(self, db: Session, obj_in_data: dict) -> ModelType:
        obj = self.model(**obj_in_data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: ModelType, obj_in_data: dict) -> ModelType:
        for field, value in obj_in_data.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, id: int) -> None:
        obj = self.get(db, id)
        if obj is None:
            return
        db.delete(obj)
        db.commit()


Users = CRUDBase(models.User)
Projects = CRUDBase(models.Project)
Documents = CRUDBase(models.Document)
Drawings = CRUDBase(models.Drawing)
Materials = CRUDBase(models.Material)
MaterialDrawings = CRUDBase(models.MaterialDrawing)
Reports = CRUDBase(models.Report)
ProjectUsers = CRUDBase(models.ProjectUser)
ProjectShares = CRUDBase(models.ProjectShare)
AuthSessions = CRUDBase(models.AuthSession)
DrawingCalculations = CRUDBase(models.DrawingCalculation)
Estimates = CRUDBase(models.Estimate)
EstimateItems = CRUDBase(models.EstimateItem)
DocumentPages = CRUDBase(models.DocumentPage)


class UserCRUD(CRUDBase[models.User]):
    def get_by_username(self, db: Session, username: str) -> Optional[models.User]:
        """Получить пользователя по username"""
        return db.query(models.User).filter(models.User.username == username).first()

    def get_by_id(self, db: Session, user_id: int) -> Optional[models.User]:
        """Получить пользователя по ID"""
        return db.query(models.User).filter(models.User.id == user_id).first()

    def search(self, db: Session, query: str, skip: int = 0, limit: int = 100) -> List[models.User]:
        """Поиск пользователя по username или ФИО"""
        search_term = f"%{query}%"
        return db.query(models.User).filter(
            or_(
                models.User.username.ilike(search_term),
                models.User.first_name.ilike(search_term),
                models.User.last_name.ilike(search_term),
                or_(
                    (models.User.first_name + ' ' + models.User.last_name).ilike(search_term),
                    (models.User.last_name + ' ' + models.User.first_name).ilike(search_term)
                )
            )
        ).offset(skip).limit(limit).all()

    def create_with_password(self, db: Session, obj_in_data: dict, password: str) -> models.User:
        """Создать пользователя с хешированием пароля"""
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        obj_in_data["password_hash"] = password_hash
        return self.create(db, obj_in_data)

    def verify_password(self, user: models.User, password: str) -> bool:
        """Проверить пароль пользователя"""
        import hashlib
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        return user.password_hash == password_hash

    def delete_user(self, db: Session, user_id: int) -> bool:
        """Удалить пользователя и все связанные данные"""
        user = self.get_by_id(db, user_id)
        if not user:
            return False
        db.delete(user)
        db.commit()
        return True


class ProjectCRUD(CRUDBase[models.Project]):
    def get_by_owner(self, db: Session, owner_id: int, skip: int = 0, limit: int = 100) -> List[models.Project]:
        """Получить проекты владельца"""
        return db.query(models.Project).filter(
            models.Project.owner_id == owner_id
        ).offset(skip).limit(limit).all()

    def get_shared_with_user(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Project]:
        """Получить проекты, предоставленные пользователю"""
        return db.query(models.Project).join(
            models.ProjectShare, models.Project.id == models.ProjectShare.project_id
        ).filter(
            models.ProjectShare.shared_with_id == user_id
        ).offset(skip).limit(limit).all()

    def search_by_name(self, db: Session, name: str, user_id: int = None, skip: int = 0, limit: int = 100) -> List[models.Project]:
        """
        Поиск проекта по названию
        
        Если user_id указан - ищет все доступные проекты этого пользователя (мои + общие)
        Если user_id=None - ищет только проекты, где пользователь является владельцем
        """
        if user_id is not None:
            # Поиск среди всех доступных проектов пользователя
            # Проекты, где пользователь является владельцем
            my_projects = db.query(models.Project).filter(
                models.Project.name.ilike(f"%{name}%"),
                models.Project.owner_id == user_id
            ).all()
            
            # Проекты, доступные через шаринг
            shared_projects = db.query(models.Project).join(
                models.ProjectShare, models.Project.id == models.ProjectShare.project_id
            ).filter(
                models.ProjectShare.shared_with_id == user_id,
                models.Project.name.ilike(f"%{name}%")
            ).all()
            
            # Убираем дубликаты по ID
            all_projects = {p.id: p for p in my_projects + shared_projects}
            return list(all_projects.values())[skip:skip+limit]
        else:
            # Поиск только проектов, где пользователь является владельцем (без user_id)
            query = db.query(models.Project).filter(
                models.Project.name.ilike(f"%{name}%")
            )
            return query.offset(skip).limit(limit).all()
        
    def create_with_owner(self, db: Session, obj_in_data: dict, owner_id: int) -> models.Project:
        """Создать проект с указанием владельца и добавлением владельца как участника"""
        obj_in_data["owner_id"] = owner_id
        
        # Создаём проект
        project = self.create(db, obj_in_data)
        
        # Добавляем владельца как участника с правами admin
        project_user = models.ProjectUser(
            user_id=owner_id,
            project_id=project.id,
            access_rights="admin",
            created_at=date.today()
        )
        db.add(project_user)
        db.commit()
        
        return project

    def remove(self, db: Session, id: int) -> None:
        """Удалить проект и все файлы документов из MinIO"""
        project = self.get(db, id)
        if project is None:
            return

        # Получаем все документы проекта до удаления
        documents = db.query(models.Document).filter(
            models.Document.project_id == id
        ).all()

        # Удаляем файлы документов из MinIO
        for doc in documents:
            if doc.file_path:
                try:
                    object_key = doc.file_path.replace("minio://", "")
                    minio_client.delete_file(object_key)
                except Exception as e:
                    print(f"[WARN] Failed to delete file for document {doc.id}: {e}")

        # SQLAlchemy cascade удалит все связанные записи из БД
        db.delete(project)
        db.commit()
        

class DocumentCRUD(CRUDBase[models.Document]):
    def get_by_project(self, db: Session, project_id: int, skip: int = 0, limit: int = 100) -> List[models.Document]:
        """Получить все документы проекта"""
        return db.query(models.Document).filter(
            models.Document.project_id == project_id
        ).offset(skip).limit(limit).all()
        
    def remove(self, db: Session, id: int) -> None:
        """Удалить документ, связанные страницы и файл из MinIO"""
        obj = self.get(db, id)
        if obj is None:
            return

        # Удаляем файл из MinIO если есть
        if obj.file_path:
            try:
                object_key = obj.file_path.replace("minio://", "")
                minio_client.delete_file(object_key)
            except Exception as e:
                # Логируем ошибку, но не прерываем удаление из БД
                print(f"[WARN] Failed to delete file from MinIO: {e}")

        # Удаляем связанные страницы напрямую, чтобы избежать ленивой загрузки
        db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == id
        ).delete(synchronize_session=False)

        # Затем удаляем сам документ
        db.delete(obj)
        db.commit()
        

class EstimateCRUD(CRUDBase[models.Estimate]):
    def create_with_defaults(self, db: Session, obj_in_data: dict) -> models.Estimate:
        """Создать смету с значениями по умолчанию"""
        now = datetime.now()
        obj_in_data["total_cost"] = 0
        obj_in_data["total_quantity"] = 0
        obj_in_data["created_at"] = now
        obj_in_data["updated_at"] = now
        return self.create(db, obj_in_data)

    def update_totals(self, db: Session, estimate_id: int) -> models.Estimate:
        """Обновить итоговые суммы сметы"""
        estimate = self.get(db, estimate_id)
        if not estimate:
            return None
        
        total_cost = 0
        total_quantity = 0
        for item in estimate.items:
            total_cost += item.total_cost
            total_quantity += item.quantity
        
        estimate.total_cost = total_cost
        estimate.total_quantity = total_quantity
        estimate.updated_at = datetime.now()
        db.add(estimate)
        db.commit()
        db.refresh(estimate)
        return estimate

    def merge_estimates(self, db: Session, name: str, description: str, estimate_ids: List[int], user_id: int) -> models.Estimate:
        """Объединить несколько смет в одну"""
        # Создаем новую смету
        new_estimate_data = {
            "project_id": None,  # Will be set from first estimate
            "name": name,
            "description": description,
        }
        
        # Получаем первую смету для определения проекта
        first_estimate = self.get(db, estimate_ids[0])
        if first_estimate:
            new_estimate_data["project_id"] = first_estimate.project_id
        
        new_estimate = self.create_with_defaults(db, new_estimate_data)
        
        # Переносим элементы из всех смет
        total_cost = 0
        total_quantity = 0
        
        for est_id in estimate_ids:
            estimate = self.get(db, est_id)
            if estimate:
                for item in estimate.items:
                    new_item = models.EstimateItem(
                        estimate_id=new_estimate.id,
                        drawing_calculation_id=item.drawing_calculation_id,
                        quantity=item.quantity,
                        unit_cost=item.unit_cost,
                        total_cost=item.total_cost
                    )
                    db.add(new_item)
                    total_cost += item.total_cost
                    total_quantity += item.quantity
        
        new_estimate.total_cost = total_cost
        new_estimate.total_quantity = total_quantity
        new_estimate.updated_at = datetime.now()
        
        db.commit()
        db.refresh(new_estimate)
        return new_estimate


class ProjectUserCRUD(CRUDBase[models.ProjectUser]):
    def check_access(self, db: Session, user_id: int, project_id: int) -> bool:
        """Проверить доступ пользователя к проекту (включая shared проекты)"""
        # Проверка через ProjectUser
        has_user_access = db.query(models.ProjectUser).filter(
            models.ProjectUser.user_id == user_id,
            models.ProjectUser.project_id == project_id
        ).first() is not None
    
        if has_user_access:
            return True
        
        # Проверка через ProjectShare
        has_share_access = db.query(models.ProjectShare).filter(
            models.ProjectShare.shared_with_id == user_id,
            models.ProjectShare.project_id == project_id
        ).first() is not None
        
        return has_share_access
    
    def get_user_projects(self, db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[models.Project]:
        """Получить все проекты пользователя (включая общие)"""
        # Проекты, где пользователь является участником
        user_projects = db.query(models.Project).join(
            models.ProjectUser, models.Project.id == models.ProjectUser.project_id
        ).filter(
            models.ProjectUser.user_id == user_id
        ).offset(skip).limit(limit).all()
        
        # Проекты, доступные через sharing
        shared_projects = db.query(models.Project).join(
            models.ProjectShare, models.Project.id == models.ProjectShare.project_id
        ).filter(
            models.ProjectShare.shared_with_id == user_id
        ).offset(skip).limit(limit).all()
        
        # Объединяем и убираем дубликаты
        all_projects = {p.id: p for p in user_projects + shared_projects}
        return list(all_projects.values())


# Заменяем стандартные классы на расширенные
Users = UserCRUD(models.User)
Projects = ProjectCRUD(models.Project)
Documents = DocumentCRUD(models.Document)
ProjectUsers = ProjectUserCRUD(models.ProjectUser)
Estimates = EstimateCRUD(models.Estimate)
