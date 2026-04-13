from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import (
    users, projects, documents,
    drawing_calculations, estimates
)

app = FastAPI(title="Construction Technical Docs Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"status": "ok"}

# include routers
app.include_router(users.router, prefix="/api/users", tags=["users"]) 
app.include_router(projects.router, prefix="/api/projects", tags=["projects"]) 
app.include_router(documents.router, prefix="/api/documents", tags=["documents"]) 
app.include_router(drawing_calculations.router, prefix="/api/drawing-calculations", tags=["drawing_calculations"])
app.include_router(estimates.router, prefix="/api/estimates", tags=["estimates"])

