import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.api.routes import router
from app.core.config import get_settings
from app.core.errors import AppError

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins,
                   allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
                   allow_headers=["Content-Type"], allow_credentials=False)


@app.middleware("http")
async def correlation(request: Request, call_next):
    request.state.correlation_id = str(uuid4())
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = request.state.correlation_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
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

