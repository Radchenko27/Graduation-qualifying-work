from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .routers.api import users, projects, documents, drawing_calculations, estimates
from .routers import frontend

app = FastAPI(title="Construction Technical Docs Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# include API routers
app.include_router(users.router, prefix="/api/users", tags=["users"]) 
app.include_router(projects.router, prefix="/api/projects", tags=["projects"]) 
app.include_router(documents.router, prefix="/api/documents", tags=["documents"]) 
app.include_router(drawing_calculations.router, prefix="/api/drawing-calculations", tags=["drawing_calculations"])
app.include_router(estimates.router, prefix="/api/estimates", tags=["estimates"])

# include frontend routers
app.include_router(frontend.router, tags=["frontend"])

