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
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить список документов с возможностью фильтрации:
    - project_id - документы конкретного проекта

    Требует аутентификации
    """
    if project_id:
        # Проверка доступа к проекту
        if not crud.ProjectUsers.check_access(db, current_user.id, project_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Нет доступа к проекту"
            )
        
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
    
    # Поддерживаем оба формата: minio://project_id/файл.pdf и minio://documents/project_id/файл.pdf
    if document.file_path.startswith("minio://"):
        object_key = document.file_path.replace("minio://", "")
    else:
        # Предполагаем, что это прямой object_key
        object_key = document.file_path
    
    # Если object_key начинается с "documents/", удаляем этот префикс
    # (он добавляется автоматически из bucket имени)
    if object_key.startswith("documents/"):
        object_key = object_key.replace("documents/", "", 1)
    
    print(f"DEBUG: Downloading document {document_id}")
    print(f"DEBUG: file_path = {document.file_path}")
    print(f"DEBUG: object_key (cleaned) = {object_key}")
    
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
    
    # Если object_key начинается с "documents/", удаляем этот префикс
    if object_key.startswith("documents/"):
        object_key = object_key.replace("documents/", "", 1)
    
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


@router.post("/{document_id}/parse-specifications")
def parse_specifications(
    document_id: int,
    format: str = "json",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Парсинг спецификаций документа

    Извлекает спецификации со страниц, классифицированных как 'specification',
    и экспортирует их в JSON или Excel формат.

    Параметры:
    - format: 'json' или 'excel' (по умолчанию 'json')
    """
    from pathlib import Path
    from ...utils.specification_parser import parse_document_specifications, SpecificationParser

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

    # Проверяем формат
    if format not in ['json', 'excel']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат. Используйте 'json' или 'excel'"
        )

    try:
        # Проверяем наличие страниц со спецификациями
        spec_pages = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == document_id,
            models.DocumentPage.category == 'specification'
        ).all()
        
        if not spec_pages:
            print(f"[WARN] Документ {document_id} не имеет страниц со спецификациями")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="В документе нет страниц, классифицированных как спецификации. Переклассифицируйте документ."
            )
        
        print(f"[INFO] Документ {document_id}: найдено {len(spec_pages)} страниц со спецификациями")

        output_dir = Path('output/specifications')
        output_dir.mkdir(parents=True, exist_ok=True)

        output_path = parse_document_specifications(
            document_id=document_id,
            output_format=format,
            output_dir=str(output_dir),
            processed_dir='processed'
        )

        return {
            "status": "success",
            "document_id": document_id,
            "document_name": document.name,
            "format": format,
            "output_path": output_path,
            "message": f"Спецификации успешно экспортированы в {format.upper()}"
        }

    except FileNotFoundError as e:
        print(f"[ERROR] Processed файл не найден для документа {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processed файл не найден. Переобработайте документ через pdf_processor: {str(e)}"
        )
    except ValueError as e:
        error_msg = str(e)
        print(f"[ERROR] ValueError при парсинге документа {document_id}: {error_msg}")
        if "Processed JSON файл не найден" in error_msg:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Processed файл не найден или повреждён. Переобработайте документ через pdf_processor."
            )
        elif "спецификациями не найдено" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="В документе нет страниц со спецификациями. Переклассифицируйте документ."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg
            )
    except Exception as e:
        import traceback
        traceback.print_exc()
        
        # Проверяем на распространённые ошибки
        error_msg = str(e)
        if "openpyxl" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Отсутствует модуль openpyxl. Установите: pip install openpyxl"
            )
        elif "json" in error_msg.lower() and ("decode" in error_msg.lower() or "expecting" in error_msg.lower()):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Processed JSON файл повреждён. Переобработайте документ."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Ошибка парсинга спецификаций: {error_msg}"
            )


@router.get("/{document_id}/specification-summary")
def get_specification_summary(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить сводную информацию о спецификациях документа

    Возвращает:
    - specification_pages_count: количество страниц со спецификациями
    - specification_pages: список страниц с категорией 'specification'
    """
    from ...utils.specification_parser import SpecificationParser

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

    try:
        with SpecificationParser(document_id, processed_dir='processed') as parser:
            summary = parser.get_summary()
            return summary

    except ValueError as e:
        # Если processed файл не найден или нет спецификаций
        # Возвращаем информацию из БД
        spec_pages = db.query(models.DocumentPage).filter(
            models.DocumentPage.document_id == document_id,
            models.DocumentPage.category == 'specification'
        ).order_by(models.DocumentPage.page_number).all()

        return {
            "document_id": document_id,
            "document_name": document.name,
            "project_id": document.project_id,
            "specification_pages_count": len(spec_pages),
            "specification_pages": [
                {
                    "page_number": p.page_number,
                    "confidence": p.confidence,
                    "content_type": p.content_type
                }
                for p in spec_pages
            ],
            "note": "Processed файл не найден. Показана информация из БД."
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения сводки: {str(e)}"
        )


@router.put("/{document_id}/pages/{page_id}/category")
def update_page_category(
    document_id: int,
    page_id: int,
    category_data: dict,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Изменить категорию страницы вручную

    Позволяет пользователю исправить результаты классификации для отдельной страницы.
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
    
    # Получаем страницу
    page = db.query(models.DocumentPage).filter(
        models.DocumentPage.id == page_id,
        models.DocumentPage.document_id == document_id
    ).first()
    
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Страница не найдена"
        )
    
    # Проверяем категорию
    new_category = category_data.get('category')
    valid_categories = ['title', 'drawing', 'scheme', 'specification', 'other']
    
    if not new_category or new_category not in valid_categories:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Неверная категория. Допустимые: {', '.join(valid_categories)}"
        )
    
    # Обновляем категорию
    page.category = new_category
    page.confidence = 1.0  # Уверенность пользователя = 100%
    
    db.add(page)
    db.commit()
    db.refresh(page)
    
    return {
        "page_id": page_id,
        "page_number": page.page_number,
        "category": page.category,
        "message": f"Категория страницы {page.page_number} изменена на '{new_category}'"
    }


@router.get("/{document_id}/pages/{page_number}/image")
def get_page_image(
    document_id: int,
    page_number: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить изображение страницы PDF в формате PNG
    
    Возвращает presigned URL для изображения страницы
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
    
    # Получаем object_key
    if document.file_path.startswith("minio://"):
        object_key = document.file_path.replace("minio://", "")
    else:
        object_key = document.file_path
    
    if object_key.startswith("documents/"):
        object_key = object_key.replace("documents/", "", 1)
    
    # Формируем путь к изображению страницы
    # Предполагаем что страницы сохранены как: project_id/filename/page_1.png
    page_image_key = f"{object_key.rsplit('/', 1)[0]}/pages/page_{page_number}.png"
    
    try:
        # Проверяем существует ли изображение
        if minio_client.file_exists(page_image_key):
            # Генерируем presigned URL
            url = minio_client.get_presigned_url(page_image_key, expires_in=3600)
            return {
                "url": url,
                "page_number": page_number,
                "exists": True
            }
        else:
            # Изображение не найдено - возвращаем ошибку
            return {
                "url": None,
                "page_number": page_number,
                "exists": False,
                "message": "Изображение страницы не найдено. Страницы нужно предварительно извлечь."
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения изображения: {str(e)}"
        )


@router.post("/{document_id}/parse-full")
def parse_full_document(
    document_id: int,
    format: str = "json",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Универсальный парсинг ВСЕГО документа.

    Обрабатывает все страницы документа в зависимости от их категории:
    - specification → таблицы спецификаций
    - drawing       → обозначение, название, размеры
    - scheme        → элементы схемы
    - title         → метаданные
    - other         → текст

    Параметры:
    - format: 'json' или 'excel' (по умолчанию 'json')
    """
    from pathlib import Path
    from ...utils.document_parser import DocumentParser
    from ...services.minio_client import minio_client
    import tempfile
    import os

    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Проверка доступа к проекту
    if document.project_id and not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )

    if format not in ['json', 'excel']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат. Используйте 'json' или 'excel'"
        )

    try:
        with DocumentParser(document_id, processed_dir='processed') as parser:
            doc_name = Path(document.name).stem
            
            # Для JSON — сохраняем в файл и загружаем в MinIO
            if format.lower() == 'json':
                structure = parser.parse_document()
                
                # Сохраняем JSON во временный файл
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
                    import json
                    json.dump(structure, f, ensure_ascii=False, indent=2)
                    temp_json_path = f.name
                
                try:
                    # Загружаем в MinIO
                    with open(temp_json_path, 'rb') as f:
                        json_content = f.read()
                    
                    project_id = document.project_id or 0
                    json_file_name = f"{doc_name}_structured.json"
                    json_object_key = minio_client.upload_file(json_content, json_file_name, project_id)
                    
                    # Сохраняем путь в БД
                    document.json_path = f"minio://{json_object_key}"
                    db.commit()
                    
                    return {
                        "status": "success",
                        "document_id": document_id,
                        "document_name": document.name,
                        "format": "json",
                        "output_path": f"minio://{json_object_key}",
                        "download_url": f"/api/documents/{document_id}/download-processed?format=json",
                        "message": f"Документ успешно обработан и сохранён в JSON в MinIO"
                    }
                finally:
                    # Удаляем временный файл
                    if os.path.exists(temp_json_path):
                        os.unlink(temp_json_path)

            # Для Excel — сохраняем файл и загружаем в MinIO
            output_dir = Path('output/documents')
            output_dir.mkdir(parents=True, exist_ok=True)
            excel_path = parser.export_to_excel(str(output_dir / f"{doc_name}_structured.xlsx"))

            # Загружаем Excel в MinIO
            with open(excel_path, 'rb') as f:
                excel_content = f.read()
            
            project_id = document.project_id or 0
            excel_file_name = f"{doc_name}_structured.xlsx"
            excel_object_key = minio_client.upload_file(excel_content, excel_file_name, project_id)
            
            # Сохраняем путь в БД
            document.excel_path = f"minio://{excel_object_key}"
            db.commit()

            return {
                "status": "success",
                "document_id": document_id,
                "document_name": document.name,
                "format": format,
                "output_path": f"minio://{excel_object_key}",
                "download_url": f"/api/documents/{document_id}/download-processed?format=excel",
                "message": f"Документ успешно обработан и сохранён в {format.upper()} в MinIO"
            }

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processed файл не найден. Переобработайте документ: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка обработки документа: {str(e)}"
        )


@router.get("/{document_id}/download-processed")
def download_processed_document(
    document_id: int,
    format: str = "json",
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Скачать обработанный файл (JSON или Excel) из MinIO.
    """
    from ...services.minio_client import minio_client
    from starlette.responses import StreamingResponse

    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    # Проверка доступа к проекту
    if document.project_id and not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )

    # Определяем путь к файлу в зависимости от формата
    if format.lower() == 'json':
        file_path = document.json_path
        file_name = f"{Path(document.name).stem}_structured.json"
        content_type = 'application/json'
    elif format.lower() == 'excel':
        file_path = document.excel_path
        file_name = f"{Path(document.name).stem}_structured.xlsx"
        content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Неверный формат. Используйте 'json' или 'excel'"
        )

    if not file_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Файл {format.upper()} ещё не сгенерирован. Обработайте документ."
        )

    try:
        # Извлекаем object_key из пути minio://
        object_key = file_path.replace("minio://", "")
        
        # Скачиваем файл из MinIO
        file_content = minio_client.download_file(object_key)
        
        # Возвращаем файл
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename=\"{file_name}\""
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка скачивания файла: {str(e)}"
        )


@router.get("/{document_id}/structure")
def get_document_structure(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Получить структуру документа без сохранения в файл.
    Возвращает JSON с обработанными данными всех страниц.
    """
    from ...utils.document_parser import DocumentParser

    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )

    try:
        with DocumentParser(document_id, processed_dir='processed') as parser:
            structure = parser.parse_document()
            return structure

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Processed файл не найден: {str(e)}"
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка получения структуры: {str(e)}"
        )


@router.post("/{document_id}/reprocess")
def reprocess_document(
    document_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(db.get_db)
):
    """
    Переобработать PDF документ с сохранением text_blocks_details.
    Обновляет processed JSON файл с геометрическими данными.
    """
    from pathlib import Path
    from ...services.pdf_processor import PDFProcessor
    from ...services.minio_client import minio_client

    document = crud.Documents.get(db, document_id)
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    if not crud.ProjectUsers.check_access(db, current_user.id, document.project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Нет доступа к проекту"
        )

    if not document.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="У документа нет файла"
        )

    try:
        # Скачиваем PDF из MinIO
        object_key = document.file_path.replace("minio://", "")
        if object_key.startswith("documents/"):
            object_key = object_key.replace("documents/", "", 1)
        
        pdf_content = minio_client.download_file(object_key)
        
        # Создаём временный файл с документ ID
        temp_pdf = Path('temp_reprocess.pdf')
        with open(temp_pdf, 'wb') as f:
            f.write(pdf_content)
        
        # Определяем директорию для processed
        output_dir = Path('processed') / f"{document_id}_{Path(document.name).stem}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Обрабатываем с analyze_structure=True
        try:
            with PDFProcessor(str(temp_pdf)) as processor:
                result = processor.process_document(
                    output_dir=output_dir,
                    extract_images=False,
                    extract_text=True,
                    analyze_structure=True,
                    zoom=1.0
                )
        finally:
            # Удаляем временный файл после закрытия процессора
            import gc
            gc.collect()
            try:
                if temp_pdf.exists():
                    temp_pdf.unlink()
            except Exception:
                pass
        
        # Переименовываем файл, если он назван неправильно
        json_file = output_dir / f"temp_reprocess_processed.json"
        final_json_name = f"{output_dir.name}_processed.json"
        final_json_path = output_dir / final_json_name
        if json_file.exists():
            json_file.rename(final_json_path)
        
        # Загружаем processed JSON в MinIO
        json_object_key = None
        if final_json_path.exists():
            with open(final_json_path, 'rb') as f:
                json_content = f.read()
            
            project_id = document.project_id or 0
            doc_name = Path(document.name).stem
            json_file_name = f"{doc_name}_structured.json"
            json_object_key = minio_client.upload_file(json_content, json_file_name, project_id)
            
            # Сохраняем путь в БД
            document.json_path = f"minio://{json_object_key}"
            db.commit()
        
        # Проверяем наличие text_blocks_details
        has_blocks = False
        if 'structure' in result and result['structure']:
            first_page = list(result['structure'].values())[0]
            has_blocks = 'text_blocks_details' in first_page
        
        return {
            "status": "success",
            "document_id": document_id,
            "message": f"Документ переобработан. text_blocks_details: {'✓ есть' if has_blocks else '✗ нет'}",
            "output_dir": str(output_dir),
            "pages_processed": len(result.get('text', {})),
            "has_text_blocks": has_blocks,
            "json_path": document.json_path,
            "download_url": f"/api/documents/{document_id}/download-processed?format=json" if document.json_path else None
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ошибка переобработки: {str(e)}"
        )
