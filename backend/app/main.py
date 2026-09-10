import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.api.admin import router as admin_router
from app.api.atenciones import router as atenciones_router
from app.api.auth import router as auth_router
from app.api.bootstrap import router as bootstrap_router
from app.api.busqueda import router as busqueda_router
from app.api.casos import router as casos_router
from app.api.dashboard import router as dashboard_router
from app.api.documentos import router as documentos_router
from app.api.formularios import router as formularios_router
from app.api.routers_simples import (
    hallazgos_recorrido_router, novedades_router, personas_router, recorridos_router,
)
from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url=None if settings.environment == "production" else "/docs",
    redoc_url=None if settings.environment == "production" else "/redoc",
    openapi_url=None if settings.environment == "production" else "/openapi.json",
)
# allow_credentials=True: la sesión viaja en una cookie (app/services/sessions.py).
# cors_origins es una lista explícita, nunca "*" — obligatorio junto con credentials.
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                   allow_headers=["Content-Type"], allow_credentials=True)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)


@app.middleware("http")
async def csrf_origin_check(request: Request, call_next):
    """Las mutaciones con cookie solo se aceptan desde un origen configurado."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and settings.environment == "production":
        origin = request.headers.get("origin")
        if origin not in settings.cors_origins:
            return error_response(request, 403, "ORIGIN_FORBIDDEN", "Origen de la solicitud no permitido.")
    return await call_next(request)


@app.middleware("http")
async def correlation(request: Request, call_next):
    request.state.correlation_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Cache-Control"] = "no-store"
    if settings.environment == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def error_response(request: Request, status: int, code: str, message: str):
    correlation_id = getattr(request.state, "correlation_id", str(uuid4()))
    return JSONResponse(status_code=status, content={"ok": False, "code": code, "message": message,
                        "correlationId": correlation_id},
                        headers={"X-Correlation-ID": correlation_id, "Cache-Control": "no-store"})


@app.exception_handler(AppError)
async def app_error(request: Request, error: AppError):
    return error_response(request, error.status_code, error.code, str(error.detail))


@app.exception_handler(HTTPException)
async def http_error(request: Request, error: HTTPException):
    return error_response(request, error.status_code, f"HTTP_{error.status_code}", str(error.detail))


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, _: RequestValidationError):
    return error_response(request, 422, "INVALID_INPUT", "Revise los datos enviados.")


@app.exception_handler(Exception)
async def internal_error(request: Request, error: Exception):
    logging.getLogger(__name__).exception("Error interno: %s", request.state.correlation_id)
    return error_response(request, 500, "INTERNAL_ERROR", "No fue posible completar la solicitud.")


app.include_router(router)
app.include_router(auth_router)
app.include_router(bootstrap_router)
app.include_router(casos_router)
app.include_router(atenciones_router)
app.include_router(novedades_router)
app.include_router(recorridos_router)
app.include_router(hallazgos_recorrido_router)
app.include_router(personas_router)
app.include_router(formularios_router)
app.include_router(busqueda_router)
app.include_router(admin_router)
app.include_router(documentos_router)
app.include_router(dashboard_router)

