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
        return RedirectResponse(url="/login", status_code=302)
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"/projects/{project_id}", headers={"X-Session-Key": session_key})
            project = response.json() if response.ok else {}
        except:
            project = {}
    
    return templates.TemplateResponse("project_detail.html", {
        "request": request,
        "project": project,
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
            response = await client.get("/users/me", headers={"X-Session-Key": session_key})
            user = response.json() if response.ok else {}
        except:
            user = {}
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "current_user": True
    })
