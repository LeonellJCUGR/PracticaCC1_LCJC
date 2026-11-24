"""Traducción de errores de dominio al formato común {"error": ..., "detalle": ...}."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.catalog_client import AtraccionNoEncontrada, CatalogoNoDisponible
from app.reglas import ReglaNegocioError


class APIError(ReglaNegocioError):
    """Error HTTP genérico con el mismo formato que las reglas de negocio."""


def _json(status_code: int, error: str, detalle: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "detalle": detalle})


async def _regla(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ReglaNegocioError)
    return _json(exc.status_code, exc.error, exc.detalle)


async def _no_encontrada(_: Request, exc: Exception) -> JSONResponse:
    return _json(404, "ATRACCION_NO_ENCONTRADA", str(exc))


async def _catalogo_caido(_: Request, exc: Exception) -> JSONResponse:
    return _json(503, "CATALOGO_NO_DISPONIBLE", str(exc))


def registrar_manejadores(app: FastAPI) -> None:
    app.add_exception_handler(ReglaNegocioError, _regla)
    app.add_exception_handler(AtraccionNoEncontrada, _no_encontrada)
    app.add_exception_handler(CatalogoNoDisponible, _catalogo_caido)


def reserva_no_encontrada(codigo: str) -> APIError:
    return APIError(404, "RESERVA_NO_ENCONTRADA", f"No existe la reserva {codigo}")
