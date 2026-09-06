"""Errores de dominio con código estable, análogo a Base Sistema/ErrorService.gs (TSAppError)."""

from fastapi import HTTPException


class AppError(HTTPException):
    def __init__(self, code: str, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail=message)
        self.code = code
