from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import httpx

from ..models import User
from ..dependencies import get_current_user_optional

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def get_session_key(request: Request) -> Optional[str]:
    """Получить ключ сессии из заголовка или куки"""
    return request.headers.get("X-Session-Key") or request.cookies.get("session_key")


async def get_api_client():
    """Создать HTTP клиент для внутренних запросов к API"""
    return httpx.AsyncClient(base_url="http://localhost:8000/api")


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("home.html", {"request": request})


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Страница входа"""
    session_key = get_session_key(request)
    if session_key:
        return RedirectResponse(url="/projects", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Страница регистрации"""
    session_key = get_session_key(request)
    if session_key:
        return RedirectResponse(url="/projects", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request})


@router.get("/logout")
async def logout(request: Request):
    """Выход из системы"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("session_key")
    return response


@router.get("/projects", response_class=HTMLResponse)
async def projects_page(request: Request):
    """Страница проектов"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("/projects/", headers={"X-Session-Key": session_key})
            projects = response.json() if response.ok else []
        except:
            projects = []
    
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "projects": projects,
        "current_user": True
    })


@router.get("/projects/{project_id}", response_class=HTMLResponse)
async def project_detail_page(request: Request, project_id: int):
    """Детальная страница проекта"""
    session_key = get_session_key(request)
    if not session_key:
        print(f"ERROR: No session key for project {project_id}")
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            url = f"http://127.0.0.1:8000/api/projects/{project_id}"
            response = await client.get(url, headers={"X-Session-Key": session_key})
            print(f"DEBUG: API request to {url}, status={response.status_code}")
            if response.status_code >= 400:
                print(f"DEBUG: API response body={response.text[:200]}")
                raise HTTPException(status_code=404, detail="Проект не найден")
            project = response.json()
            print(f"DEBUG project detail: project = {project}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"ERROR: {e}")
            raise HTTPException(status_code=404, detail="Проект не найден")
    
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
        "project_id": project_id,
        "current_user": True
    })


@router.get("/documents", response_class=HTMLResponse)
async def documents_page(request: Request):
    """Страница документов"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            docs_response = await client.get("/documents/", headers={"X-Session-Key": session_key})
            documents = docs_response.json() if docs_response.ok else []
            
            projects_response = await client.get("/projects/", headers={"X-Session-Key": session_key})
            projects = projects_response.json() if projects_response.ok else []
        except:
            documents = []
            projects = []
    
    return templates.TemplateResponse("documents.html", {
        "request": request,
        "documents": documents,
        "projects": projects,
        "current_user": True
    })


@router.get("/documents/{document_id}/download")
async def download_document(request: Request, document_id: int):
    """Скачивание документа"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    return RedirectResponse(url=f"/api/documents/{document_id}/download")


@router.get("/documents/{document_id}", response_class=HTMLResponse)
async def document_detail_page(request: Request, document_id: int):
    """Страница просмотра документа с классификацией страниц"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    try:
        async with httpx.AsyncClient(base_url="http://localhost:8000/api") as client:
            # Получаем информацию о документе
            doc_response = await client.get(
                f"/documents/{document_id}",
                headers={"X-Session-Key": session_key}
            )
            document = doc_response.json() if doc_response.status_code == 200 else {}
            
            # Получаем проект
            if document.get('project_id'):
                proj_response = await client.get(
                    f"/projects/{document['project_id']}",
                    headers={"X-Session-Key": session_key}
                )
                project = proj_response.json() if proj_response.status_code == 200 else {}
            else:
                project = {}
        
    except Exception as e:
        print(f"ERROR document_detail_page: {e}")
        import traceback
        traceback.print_exc()
        return RedirectResponse(url="/documents", status_code=302)
    
    return templates.TemplateResponse("document_detail.html", {
        "request": request,
        "document": {
            "id": document_id,
            "name": document.get('name', ''),
            "project_name": project.get('name', '') if project else '',
            "created_at": document.get('created_at', ''),
            "page_count": document.get('page_count', 0),
            "json_path": document.get('json_path'),
            "excel_path": document.get('excel_path')
        }
    })


@router.get("/drawing-calculations", response_class=HTMLResponse)
async def drawing_calculations_page(request: Request):
    """Страница расчётов чертежей"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            calc_response = await client.get("/drawing-calculations/", headers={"X-Session-Key": session_key})
            calculations = calc_response.json() if calc_response.ok else []
            
            drawings_response = await client.get("/drawings/", headers={"X-Session-Key": session_key})
            drawings = drawings_response.json() if drawings_response.ok else []
        except:
            calculations = []
            drawings = []
    
    return templates.TemplateResponse("drawing_calculations.html", {
        "request": request,
        "calculations": calculations,
        "drawings": drawings,
        "current_user": True
    })


@router.get("/estimates", response_class=HTMLResponse)
async def estimates_page(request: Request):
    """Страница смет"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            est_response = await client.get("/estimates/", headers={"X-Session-Key": session_key})
            estimates = est_response.json() if est_response.ok else []
            
            projects_response = await client.get("/projects/", headers={"X-Session-Key": session_key})
            projects = projects_response.json() if projects_response.ok else []
        except:
            estimates = []
            projects = []
    
    return templates.TemplateResponse("estimates.html", {
        "request": request,
        "estimates": estimates,
        "projects": projects,
        "current_user": True
    })


@router.get("/users", response_class=HTMLResponse)
async def users_page(request: Request):
    """Страница пользователей"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    # Получить текущую информацию о пользователе
    current_user_info = None
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("/users/me", headers={"X-Session-Key": session_key})
            if response.ok:
                current_user_info = response.json()
    except:
        pass
    
    return templates.TemplateResponse("users.html", {
        "request": request,
        "current_user": current_user_info,
        "current_user_id": current_user_info.get("id") if current_user_info else None
    })


@router.get("/profile", response_class=HTMLResponse)
async def profile_page(request: Request):
    """Страница профиля"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get("http://127.0.0.1:8000/api/users/me", headers={"X-Session-Key": session_key})
            print(f"DEBUG profile: API response status = {response.status_code}")
            if response.status_code == 200:
                user = response.json()
                print(f"DEBUG profile: User data = {user}")
            else:
                print(f"DEBUG profile: API error = {response.text}")
                user = {}
        except Exception as e:
            print(f"DEBUG profile: Exception = {e}")
            user = {}
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "current_user": True
    })


@router.post("/profile", response_class=HTMLResponse)
async def profile_update(request: Request):
    """Обновление данных профиля"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    # Получаем данные формы
    form_data = await request.form()
    user_data = {
        "first_name": form_data.get("first_name", ""),
        "middle_name": form_data.get("middle_name", ""),
        "last_name": form_data.get("last_name", ""),
        "email": form_data.get("email", ""),
        "phone": form_data.get("phone", "")
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(
                "http://127.0.0.1:8000/api/users/me",
                headers={"X-Session-Key": session_key},
                json=user_data
            )
            if response.status_code == 200:
                # Обновляем данные пользователя
                updated_user = response.json()
                print(f"DEBUG profile update: Success = {updated_user}")
                # Возвращаем на страницу профиля с обновлёнными данными
                return RedirectResponse(url="/profile?updated=true", status_code=302)
            else:
                print(f"DEBUG profile update: Error = {response.text}")
                # Возвращаем с ошибкой
                return RedirectResponse(url="/profile?error=update_failed", status_code=302)
        except Exception as e:
            print(f"DEBUG profile update: Exception = {e}")
            return RedirectResponse(url="/profile?error=exception", status_code=302)


@router.get("/projects/{project_id}/share", response_class=HTMLResponse)
async def project_share_page(request: Request, project_id: int):
    """Страница управления доступом к проекту"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            # Получаем информацию о проекте
            project_response = await client.get(
                "http://127.0.0.1:8000/api/projects/" + str(project_id),
                headers={"X-Session-Key": session_key}
            )
            project = project_response.json() if project_response.ok else {}
            
            # Получаем список пользователей с доступом
            shares_response = await client.get(
                "http://127.0.0.1:8000/api/projects/" + str(project_id) + "/shares",
                headers={"X-Session-Key": session_key}
            )
            shares = shares_response.json() if shares_response.ok else []
            
            if not project or not project.get('id'):
                print(f"ERROR: Project not found or empty: {project}")
                return RedirectResponse(url="/projects", status_code=302)
        except Exception as e:
            print(f"ERROR: {e}")
            return RedirectResponse(url="/projects", status_code=302)
    
    return templates.TemplateResponse("project_share.html", {
        "request": request,
        "project": project,
        "project_id": project_id,
        "shares": shares,
        "current_user": True
    })


@router.post("/projects/{project_id}/share", response_class=HTMLResponse)
async def project_share_create(request: Request, project_id: int):
    """Добавить доступ к проекту"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    # Получаем данные формы
    form_data = await request.form()
    share_data = {
        "project_id": project_id,
        "shared_with_id": int(form_data.get("shared_with_id")),
        "access_level": form_data.get("access_level", "read")
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "http://127.0.0.1:8000/api/projects/" + str(project_id) + "/share",
                headers={"X-Session-Key": session_key},
                json=share_data
            )
            if response.status_code in [200, 201]:
                return RedirectResponse(url=f"/projects/{project_id}/share?success=true", status_code=302)
            else:
                error_detail = response.json().get("detail", "Ошибка")
                print(f"Share error: {error_detail}")
                return RedirectResponse(url=f"/projects/{project_id}/share?error={error_detail}", status_code=302)
        except Exception as e:
            print(f"ERROR: {e}")
            return RedirectResponse(url=f"/projects/{project_id}/share?error=exception", status_code=302)


@router.post("/projects/{project_id}/shares/{user_id}/revoke", response_class=HTMLResponse)
async def project_share_revoke(request: Request, project_id: int, user_id: int):
    """Отозвать доступ к проекту"""
    session_key = get_session_key(request)
    if not session_key:
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(
                "http://127.0.0.1:8000/api/projects/" + str(project_id) + "/shares/" + str(user_id),
                headers={"X-Session-Key": session_key}
            )
            if response.status_code == 204:
                return RedirectResponse(url=f"/projects/{project_id}/share?success=true", status_code=302)
            else:
                return RedirectResponse(url=f"/projects/{project_id}/share?error=revocation_failed", status_code=302)
        except Exception as e:
            print(f"ERROR: {e}")
            return RedirectResponse(url=f"/projects/{project_id}/share?error=exception", status_code=302)
