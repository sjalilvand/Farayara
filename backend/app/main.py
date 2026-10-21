"""نقطه ورود FastAPI — فرایارا"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html

from . import __version__
from .config import settings
from .database import Base, engine
from .routers import admin, assessments, auth, catalog, contracts, dashboards, forms, processes, users

app = FastAPI(
    title="فرایارا — Farayara API",
    description="سامانه یکپارچه مدیریت فرایندها، فرم‌ها، کاتالوگ داده، آزمون‌های مشاوره و قراردادها",
    version=__version__,
    docs_url=None,
    openapi_url="/api/openapi.json",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API = "/api/v1"
app.include_router(auth.router, prefix=API)
app.include_router(users.router, prefix=API)
app.include_router(catalog.router, prefix=API)
app.include_router(forms.router, prefix=API)
app.include_router(processes.router, prefix=API)
app.include_router(assessments.router, prefix=API)
app.include_router(contracts.router, prefix=API)
app.include_router(dashboards.router, prefix=API)
app.include_router(admin.router, prefix=API)


@app.get("/api/docs", include_in_schema=False)
def swagger():
    return get_swagger_ui_html(openapi_url="/api/openapi.json", title="فرایارا — مستندات API")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """ساختار یکسان خطا (بخش ۱۸)"""
    detail = exc.detail
    if isinstance(detail, (list, dict)):
        payload = {"error": True, "message": "درخواست قابل اجرا نیست", "details": detail}
    else:
        payload = {"error": True, "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "app_en": settings.app_name_en,
        "version": __version__,
        "docs": "/api/docs",
        "api_base": API,
    }
