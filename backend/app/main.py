"""CSVS - 临床试验计算化系统验证管理平台."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.auth import router as auth_router
from app.api.v1.admin import router as admin_router
from app.api.v1.projects import router as projects_router
from app.api.v1.documents import router as documents_router
from app.api.v1.workflows import router as workflows_router
from app.api.v1.signatures import router as signatures_router
from app.api.v1.audit import router as audit_router
from app.api.v1.traceability import router as traceability_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.dictionary import router as dictionary_router
from app.api.v1.systems import router as systems_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理."""
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="临床试验计算化系统验证（CSV）全生命周期管理平台",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)
app.include_router(projects_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(workflows_router, prefix=settings.API_V1_PREFIX)
app.include_router(signatures_router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_router, prefix=settings.API_V1_PREFIX)
app.include_router(traceability_router, prefix=settings.API_V1_PREFIX)
app.include_router(dashboard_router, prefix=settings.API_V1_PREFIX)
app.include_router(dictionary_router, prefix=settings.API_V1_PREFIX)
app.include_router(systems_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查端点."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
