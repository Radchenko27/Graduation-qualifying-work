from sqlalchemy import Column, Integer, String, Date, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import Base

# Following the ER diagram with Russian field names translated to snake_case English for code clarity

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(100))
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100))
    username = Column(String(100), unique=True, index=True)
    password_hash = Column(String(255))
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    photo_url = Column(String(1024), nullable=True)

    project_users = relationship("ProjectUser", back_populates="user", cascade="all, delete-orphan")
    owned_shares = relationship("ProjectShare", foreign_keys="[ProjectShare.owner_id]", back_populates="owner", cascade="all, delete-orphan")
    received_shares = relationship("ProjectShare", foreign_keys="[ProjectShare.shared_with_id]", back_populates="shared_with", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Владелец проекта
    name = Column(String(255))
    description = Column(Text, nullable=True)
    address = Column(String(255), nullable=True)
    work_scope = Column(Text, nullable=True)
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")
    drawings = relationship("Drawing", back_populates="project", cascade="all, delete-orphan")
    material_drawings = relationship("MaterialDrawing", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="project", cascade="all, delete-orphan")
    project_users = relationship("ProjectUser", back_populates="project", cascade="all, delete-orphan")
    shares = relationship("ProjectShare", back_populates="project", cascade="all, delete-orphan")
    estimates = relationship("Estimate", back_populates="project", cascade="all, delete-orphan")
    owner = relationship("User", foreign_keys=[owner_id])


class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    doc_type = Column(String(100))
    category = Column(String(100), nullable=True)  # Категория документа (классификация)
    created_at = Column(Date)
    name = Column(String(255))
    file_path = Column(String(1024), nullable=True)
    file_hash = Column(String(255), nullable=True)
    page_count = Column(Integer, nullable=True)  # Количество страниц в документе

    project = relationship("Project", back_populates="documents")
    drawings = relationship("Drawing", back_populates="document", cascade="all, delete-orphan")


class Drawing(Base):
    __tablename__ = "drawings"
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    number = Column(String(100))
    name = Column(String(255))
    type = Column(String(100))
    scale = Column(String(50))
    area = Column(Float)
    page_number = Column(Integer, nullable=True)  # Выбор страницы чертежа

    document = relationship("Document", back_populates="drawings")
    project = relationship("Project", back_populates="drawings")
    material_drawings = relationship("MaterialDrawing", back_populates="drawing", cascade="all, delete-orphan")
    calculations = relationship("DrawingCalculation", back_populates="drawing", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(100))
    name = Column(String(255))
    price = Column(Float)
    mark = Column(String(255))

    material_drawings = relationship("MaterialDrawing", back_populates="material")


class MaterialDrawing(Base):
    __tablename__ = "material_drawings"
    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"))
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    drawing_id = Column(Integer, ForeignKey("drawings.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    quantity_on_drawing = Column(Float)
    cost_on_drawing = Column(Float)

    material = relationship("Material", back_populates="material_drawings")
    drawing = relationship("Drawing", back_populates="material_drawings")
    project = relationship("Project", back_populates="material_drawings")


class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True, index=True)
    material_drawing_id = Column(Integer, ForeignKey("material_drawings.id", ondelete="CASCADE"))
    material_id = Column(Integer, ForeignKey("materials.id", ondelete="CASCADE"))
    drawing_id = Column(Integer, ForeignKey("drawings.id", ondelete="CASCADE"))
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    view = Column(String(100))
    total_cost = Column(Float)
    total_quantity = Column(Float)

    project = relationship("Project", back_populates="reports")


class DrawingCalculation(Base):
    """Модель для расчета элементов чертежа"""
    __tablename__ = "drawing_calculations"
    id = Column(Integer, primary_key=True, index=True)
    drawing_id = Column(Integer, ForeignKey("drawings.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    element_name = Column(String(255))  # Название элемента
    element_type = Column(String(100))  # Тип элемента
    quantity = Column(Float)  # Количество
    unit = Column(String(50), nullable=True)  # Единица измерения
    calculation_result = Column(Text, nullable=True)  # Результат расчета
    created_at = Column(DateTime)

    drawing = relationship("Drawing", back_populates="calculations")
    project = relationship("Project")


class Estimate(Base):
    """Модель для объединенной сметы"""
    __tablename__ = "estimates"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    name = Column(String(255))  # Название сметы
    description = Column(Text, nullable=True)
    total_cost = Column(Float, default=0)
    total_quantity = Column(Float, default=0)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)

    project = relationship("Project", back_populates="estimates")
    items = relationship("EstimateItem", back_populates="estimate", cascade="all, delete-orphan")


class EstimateItem(Base):
    """Элемент сметы - ссылка на расчет чертежа"""
    __tablename__ = "estimate_items"
    id = Column(Integer, primary_key=True, index=True)
    estimate_id = Column(Integer, ForeignKey("estimates.id", ondelete="CASCADE"))
    drawing_calculation_id = Column(Integer, ForeignKey("drawing_calculations.id", ondelete="CASCADE"))
    quantity = Column(Float)
    unit_cost = Column(Float)
    total_cost = Column(Float)

    estimate = relationship("Estimate", back_populates="items")
    drawing_calculation = relationship("DrawingCalculation")


class ProjectUser(Base):
    """Модель для связи многие-ко-многим между пользователями и проектами"""
    __tablename__ = "project_users"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    access_rights = Column(String(255))
    created_at = Column(Date)  # Дата создания связи пользователь-проект

    user = relationship("User", back_populates="project_users")
    project = relationship("Project", back_populates="project_users")


class ProjectShare(Base):
    """Модель для совместного доступа к проектам"""
    __tablename__ = "project_shares"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"))
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    shared_with_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    access_level = Column(String(50))  # 'read', 'write', 'admin'
    shared_at = Column(Date)

    project = relationship("Project", back_populates="shares")
    owner = relationship("User", foreign_keys=[owner_id], back_populates="owned_shares")
    shared_with = relationship("User", foreign_keys=[shared_with_id], back_populates="received_shares")


class AuthSession(Base):
    """Модель для хранения сессий авторизации (ключ-сессии)"""
    __tablename__ = "auth_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    session_key = Column(String(255), unique=True, index=True)  # Уникальный ключ сессии
    created_at = Column(DateTime)  # Дата и время создания сессии
    expires_at = Column(DateTime)  # Дата и время истечения сессии

    user = relationship("User")
