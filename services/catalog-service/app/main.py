"""Punto de entrada de catalog-service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__, models  # noqa: F401  (registra los modelos en Base.metadata)
from app.config import get_settings
from app.database import Database
from app.errors import APIError, api_error_handler
from app.routers import atracciones, precios, temporadas

SERVICE_NAME = "catalog-service"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    db = Database(settings.database_url)
    db.create_schema()
    app.state.db = db
    yield
    db.engine.dispose()


app = FastAPI(
    title="RutaTicket - catalog-service",
    description="Atractivos, temporadas de descuento y cálculo de precios (RN-01).",
    version=__version__,
    root_path=get_settings().root_path,
    lifespan=lifespan,
)
app.add_exception_handler(APIError, api_error_handler)
app.include_router(atracciones.router)
app.include_router(temporadas.router)
app.include_router(precios.router)


@app.get("/health", tags=["salud"])
def health() -> dict[str, str]:
    """Liveness: el proceso responde (no depende de la BD para no reiniciar en vano)."""
    return {"status": "ok", "service": SERVICE_NAME, "version": __version__}


@app.get("/health/ready", tags=["salud"])
def ready(request: Request) -> JSONResponse:
    """Readiness: comprueba la conexión con la base de datos."""
    ok = request.app.state.db.ping()
    return JSONResponse(
        status_code=200 if ok else 503,
        content={"status": "ok" if ok else "degraded", "database": "up" if ok else "down"},
    )
