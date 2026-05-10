from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import hashlib
import io
import json
import mimetypes
from urllib.parse import quote

from ... import crud, schemas, db, models
from ...dependencies import get_current_user
from ...services.minio_client import minio_client
from ...services.document_classifier_v2 import classifier

router = APIRouter()


@router.post("/", response_model=schemas.DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(
    project_id: int = Form(...),
    name: str = Form(...),
    doc_type: Optional[str] = Form(None),
    category: str = Form('other'),
    auto_classify: bool = Form(False),
    file: Optional[UploadFile] = File(None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Создать новый документ с загрузкой файла

    Классификация страниц выполняется автоматически если auto_classify=true и файл PDF
    """
    # Проверка существования проекта
    project = crud.Projects.get(db, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Проверка прав доступа к проекту
    if not crud.ProjectUsers.check_access(db, current_user.id, project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    # Обработка файла
    file_path = None
    file_hash = None
    page_count = None
    file_content = None
    
    if file:
        # Читаем содержимое файла
        file_content = file.file.read()
        
        # Вычисляем хеш
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Загружаем файл в MinIO
        object_key = minio_client.upload_file(
            file_content,
            file.filename,
            project_id
        )
        
        # Формируем полный путь для БД
        file_path = f"minio://{object_key}"
        
        # Получаем количество страниц (для PDF)
        if file.filename.lower().endswith('.pdf'):
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
                page_count = len(doc)
                doc.close()
            except Exception as e:
                print(f"ERROR: Cannot read PDF: {e}")
                pass
    
    # Создаём документ
    document_data = {
        "project_id": project_id,
        "name": name,
        "doc_type": doc_type,
        "category": category,
        "file_path": file_path,
        "file_hash": file_hash,
        "page_count": page_count,
        "created_at": date.today()
    }
    
    document = crud.Documents.create(db, document_data)
    
    # Автоматическая классификация если запрошена и есть PDF
    if auto_classify and file_content and file.filename and file.filename.lower().endswith('.pdf'):
        try:
            classifications = classifier.classify_pdf_pages(file_content)
            for page_data in classifications:
                page_info = {
                    'document_id': document.id,
                    'page_number': page_data.page_number,
                    'category': page_data.category,
                    'confidence': page_data.confidence,
                    'content_type': page_data.content_type,
                    'page_metadata': json.dumps(page_data.metadata)
                }
                crud.DocumentPages.create(db, page_info)
            
            # Обновляем page_count
            if classifications:
                document.page_count = len(classifications)
                db.add(document)
                db.commit()
                db.refresh(document)
            
            print(f"[OK] Auto-classified {len(classifications)} pages for document {document.id}")
        except Exception as e:
            print(f"[WARN] Auto-classification failed: {e}")
            # Не прерываем создание документа если классификация не удалась
    
    return document


@router.get("/", response_model=List[schemas.DocumentRead])
def read_documents(
    project_id: int = None,
    category: str = None,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список документов с возможностью фильтрации:
    - project_id - документы конкретного проекта
    - category - категория документа

    Требует аутентификации
    """
    if project_id:
        # Проверка доступа к проекту
        if not crud.ProjectUsers.check_access(db, current_user.id, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к проекту"
            )
        
        if category:
            documents = db.query(models.Document, models.Project.name.label('project_name')).join(
                models.Project, models.Document.project_id == models.Project.id
            ).filter(
                models.Document.project_id == project_id,
                models.Document.category == category
            ).offset(skip).limit(limit).all()
        else:
            documents = db.query(models.Document, models.Project.name.label('project_name')).join(
                models.Project, models.Document.project_id == models.Project.id
            ).filter(
                models.Document.project_id == project_id
            ).offset(skip).limit(limit).all()
    else:
        # Получаем все документы проектов пользователя
        user_projects = crud.ProjectUsers.get_user_projects(db, current_user.id)
        project_ids = [p.id for p in user_projects]
        
        if not project_ids:
            return []
        
        documents = db.query(models.Document, models.Project.name.label('project_name')).join(
            models.Project, models.Document.project_id == models.Project.id
        ).filter(
            models.Document.project_id.in_(project_ids)
        ).offset(skip).limit(limit).all()
    
    # Преобразуем результат в список словарей
    result = []
    for doc, project_name in documents:
        doc_dict = {
            "id": doc.id,
            "project_id": doc.project_id,
            "project_name": project_name,
            "name": doc.name,
            "doc_type": doc.doc_type,
            "category": doc.category,
            "created_at": doc.created_at,
            "file_path": doc.file_path,
            "file_hash": doc.file_hash,
            "page_count": doc.page_count
        }
        result.append(doc_dict)
    
    return result


@router.get("/{document_id}", response_model=schemas.DocumentRead)
def read_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить документ по ID

    Требует аутентификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    return document


@router.put("/{document_id}", response_model=schemas.DocumentRead)
def update_document(
    document_id: int,
    document: schemas.DocumentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Обновить данные документа

    Требует аутентификации
    """
    db_document = crud.Documents.get(db, document_id)
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    document_data = document.model_dump()
    
    return crud.Documents.update(db, db_document, document_data)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Удалить документ

    Требует аутентификации
    """
    db_document = crud.Documents.get(db, document_id)
    if db_document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    crud.Documents.remove(db, document_id)
    return None


@router.get("/{document_id}/download")
def download_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Скачать документ

    Требует аутентификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Проверка доступа к проекту
    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    # Скачиваем файл из MinIO
    if not document.file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Файл не найден"
        )
    
    # Поддерживаем оба формата: minio://documents/object_key и documents/object_key
    if document.file_path.startswith("minio://"):
        object_key = document.file_path.replace("minio://", "")
    else:
        # Предполагаем, что это прямой object_key
        object_key = document.file_path
    
    print(f"DEBUG: Downloading document {document_id}")
    print(f"DEBUG: file_path = {document.file_path}")
    print(f"DEBUG: object_key = {object_key}")
    
    try:
        # Генерируем presigned URL
        presigned_url = minio_client.get_presigned_url(object_key, expires_in=3600)
        print(f"DEBUG: Presigned URL generated: {presigned_url[:80]}...")
        
        # Перенаправляем на presigned URL
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=presigned_url,
            status_code=status.HTTP_307_TEMPORARY_REDIRECT
        )
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Ошибка при загрузке файла из MinIO: {str(e)}"
        )


@router.get("/{document_id}/stats")
def get_document_stats(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить статистику классификации страниц документа
    
    Возвращает:
    - total_pages: общее количество страниц
    - categories: {category: count} — распределение по категориям
    - avg_confidence: средняя уверенность классификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Проверка доступа к проекту
    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    pages = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == document_id
    ).all()
    
    if not pages:
        return {
            "document_id": document_id,
            "document_name": document.name,
            "total_pages": 0,
            "classified_pages": 0,
            "categories": {},
            "avg_confidence": 0
        }
        
    # Статистика по категориям
    categories = {}
    total_confidence = 0
    
    for page in pages:
        cat = page.category or 'other'
        categories[cat] = categories.get(cat, 0) + 1
        total_confidence += page.confidence or 0
    
    return {
        "document_id": document_id,
        "document_name": document.name,
        "total_pages": document.page_count or len(pages),
        "classified_pages": len(pages),
        "categories": categories,
        "avg_confidence": round(total_confidence / len(pages), 2)
    }


@router.get("/{document_id}/pages")
def get_document_pages(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить классификацию страниц документа

    Требует аутентификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Проверка доступа к проекту
    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    # Получаем страницы документа
    pages = db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == document_id
    ).order_by(models.DocumentPage.page_number).all()
    
    # Форматируем ответ
    pages_data = [
        {
            "id": page.id,
            "document_id": page.document_id,
            "page_number": page.page_number,
            "category": page.category,
            "confidence": page.confidence,
            "content_type": page.content_type,
            "page_metadata": page.page_metadata
        }
        for page in pages
    ]
    
    return {
        "document_id": document_id,
        "document_name": document.name,
        "total_pages": len(pages_data),
        "pages": pages_data
    }


@router.post("/{document_id}/classify")
def classify_document_pages(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Переклассифицировать страницы документа вручную

    Требует аутентификации
    """
    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Проверка доступа к проекту
    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )
    
    # Проверяем есть ли файл
    if not document.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У документа нет файла"
        )
    
    # Скачиваем файл из MinIO
    if document.file_path.startswith("minio://"):
        object_key = document.file_path.replace("minio://", "")
    else:
        object_key = document.file_path
    
    try:
        file_content = minio_client.download_file(object_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка загрузки файла: {str(e)}"
        )
    
    # Проверяем что это PDF
    if not document.file_path.lower().endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Только PDF файлы поддерживают классификацию"
        )
    
    # Удаляем старые классификации
    db.query(models.DocumentPage).filter(
        models.DocumentPage.document_id == document_id
    ).delete()
    db.commit()
    
    # Выполняем классификацию
    try:
        classifications = classifier.classify_pdf_pages(file_content)
        
        # Сохраняем новые классификации
        for page_data in classifications:
            page_info = {
                'document_id': document_id,
                'page_number': page_data.page_number,
                'category': page_data.category,
                'confidence': page_data.confidence,
                'content_type': page_data.content_type,
                'page_metadata': json.dumps(page_data.metadata)
            }
            crud.DocumentPages.create(db, page_info)
        
        # Обновляем page_count документа
        if classifications:
            document.page_count = len(classifications)
            db.add(document)
            db.commit()
            db.refresh(document)
        
        return {
            "document_id": document_id,
            "total_pages": len(classifications),
            "message": f"Успешно классифицировано {len(classifications)} страниц"
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка классификации: {str(e)}"
        )
