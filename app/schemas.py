from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class UserBase(BaseModel):
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    username: str
    phone: Optional[str] = None
    email: Optional[str] = None
    photo_url: Optional[str] = None

class UserBaseUpdate(BaseModel):
    """Схема для обновления данных пользователя (все поля необязательные)"""
    first_name: Optional[str] = None
    middle_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserRead(UserBase):
    id: int
    class Config:
        from_attributes = True


class UserSearch(BaseModel):
    """Схема для поиска пользователя по username или ФИО"""
    query: str


class ProjectBase(BaseModel):
    name: str
    description: Optional[str] = None
    address: Optional[str] = None
    work_scope: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None

class ProjectCreate(ProjectBase):
    pass

class ProjectRead(ProjectBase):
    id: int
    owner_id: Optional[int] = None
    category: Optional[str] = None  # 'my' или 'shared'
    class Config:
        from_attributes = True


class ProjectFilter(BaseModel):
    """Схема для фильтрации проектов"""
    category: Optional[str] = None  # 'my' - личные, 'shared' - иных пользователей
    search: Optional[str] = None  # Поиск по названию


# Категории документов (фиксированный список)
DOCUMENT_CATEGORIES = [
    ("project_documentation", "Проектная документация"),
    ("working_drawings", "Рабочие чертежи"),
    ("specifications", "Спецификации"),
    ("calculations", "Расчёты"),
    ("permits", "Разрешительная документация"),
    ("other", "Другое")
]

class DocumentBase(BaseModel):
    project_id: int
    doc_type: Optional[str] = None
    created_at: Optional[date] = None
    name: str
    file_path: Optional[str] = None
    file_hash: Optional[str] = None
    page_count: Optional[int] = None

class DocumentCreate(DocumentBase):
    pass

class DocumentRead(DocumentBase):
    id: int
    project_name: Optional[str] = None
    class Config:
        from_attributes = True


class DocumentPageBase(BaseModel):
    page_number: int
    category: str  # drawing, specification, scheme, title, other
    confidence: float = 0.0
    content_type: Optional[str] = None

class DocumentPageCreate(DocumentPageBase):
    pass

class DocumentPageRead(DocumentPageBase):
    id: int
    document_id: int

    class Config:
        from_attributes = True


class DocumentWithPagesRead(DocumentRead):
    """Документ с его страницами"""
    pages: List[DocumentPageRead] = []

    class Config:
        from_attributes = True


class DrawingBase(BaseModel):
    document_id: int  # Чертеж привязан к документу
    project_id: int
    number: str
    name: str
    type: str
    scale: str
    area: float
    page_number: Optional[int] = None

class DrawingCreate(DrawingBase):
    pass

class DrawingRead(DrawingBase):
    id: int
    class Config:
        from_attributes = True


class MaterialBase(BaseModel):
    type: str
    name: str
    price: float = 0.0
    mark: str = ""

class MaterialCreate(MaterialBase):
    pass

class MaterialResponse(MaterialBase):
    id: int
    class Config:
        from_attributes = True


class MaterialBatchImport(BaseModel):
    """Схема для пакетного импорта материалов"""
    input_dir: str
    project_id: Optional[int] = None


class MaterialDrawingBase(BaseModel):
    material_id: int
    document_id: int
    drawing_id: int
    project_id: int
    quantity_on_drawing: float
    cost_on_drawing: float

class MaterialDrawingCreate(MaterialDrawingBase):
    pass

class MaterialDrawingRead(MaterialDrawingBase):
    id: int
    class Config:
        from_attributes = True


class ReportBase(BaseModel):
    material_drawing_id: int
    material_id: int
    drawing_id: int
    document_id: int
    project_id: int
    view: str
    total_cost: float
    total_quantity: float

class ReportCreate(ReportBase):
    pass

class ReportRead(ReportBase):
    id: int
    class Config:
        from_attributes = True


class ProjectUserBase(BaseModel):
    user_id: int
    project_id: int
    access_rights: str
    created_at: Optional[date] = None

class ProjectUserCreate(ProjectUserBase):
    pass

class ProjectUserRead(ProjectUserBase):
    id: int
    class Config:
        from_attributes = True


class ProjectShareBase(BaseModel):
    project_id: int
    shared_with_id: int
    access_level: str  # 'read', 'write', 'admin'

class ProjectShareCreate(ProjectShareBase):
    pass

class ProjectShareRead(ProjectShareBase):
    id: int
    owner_id: int
    shared_at: Optional[date] = None

    class Config:
        from_attributes = True


class AuthSessionBase(BaseModel):
    user_id: int
    session_key: str
    created_at: datetime
    expires_at: datetime

class AuthSessionCreate(BaseModel):
    username: str
    password: str

class AuthSessionRead(BaseModel):
    id: int
    user_id: int
    session_key: str
    created_at: datetime
    expires_at: datetime

    class Config:
        from_attributes = True


# ===== Новые схемы для расчетов чертежей и смет =====

class DrawingCalculationBase(BaseModel):
    drawing_id: int
    project_id: int
    element_name: str
    element_type: str
    quantity: float
    unit: Optional[str] = None
    calculation_result: Optional[str] = None

class DrawingCalculationCreate(DrawingCalculationBase):
    pass

class DrawingCalculationRead(DrawingCalculationBase):
    id: int
    created_at: datetime
    class Config:
        from_attributes = True


class EstimateBase(BaseModel):
    project_id: int
    name: str
    description: Optional[str] = None

class EstimateCreate(EstimateBase):
    pass

class EstimateRead(EstimateBase):
    id: int
    total_cost: float
    total_quantity: float
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class EstimateItemBase(BaseModel):
    estimate_id: int
    drawing_calculation_id: int
    quantity: float
    unit_cost: float

class EstimateItemCreate(EstimateItemBase):
    pass

class EstimateItemRead(EstimateItemBase):
    id: int
    total_cost: float
    class Config:
        from_attributes = True


class EstimateWithItemsRead(EstimateRead):
    """Смета с элементами"""
    items: list[EstimateItemRead] = []
    class Config:
        from_attributes = True


class EstimateMerge(BaseModel):
    """Объединение нескольких смет"""
    name: str
    description: Optional[str] = None
    estimate_ids: list[int]  # Список ID смет для объединения
