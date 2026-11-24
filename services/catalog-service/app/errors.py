"""Errores de la API con el formato común {"error": ..., "detalle": ...}."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class APIError(Exception):
    def __init__(self, status_code: int, error: str, detalle: str) -> None:
        super().__init__(detalle)
        self.status_code = status_code
        self.error = error
        self.detalle = detalle


async def api_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, APIError)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "detalle": exc.detalle},
    )


def atraccion_no_encontrada(atraccion_id: int) -> APIError:
    return APIError(404, "ATRACCION_NO_ENCONTRADA", f"No existe el atractivo {atraccion_id}")
