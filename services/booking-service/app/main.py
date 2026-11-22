"""Punto de entrada de booking-service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app import __version__, models
from app.catalog_client import CatalogClient
from app.config import get_settings
from app.database import Database
from app.errors import registrar_manejadores
from app.routers import consultas, reservas

SERVICE_NAME = "booking-service"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    db = Database(settings.database_url)
    db.create_schema()
    http = httpx.Client(
        base_url=settings.catalog_service_url, timeout=settings.catalog_timeout_seconds
    )
    app.state.db = db
    app.state.catalog = CatalogClient(http)
    yield
    http.close()
    db.engine.dispose()


app = FastAPI(
    title="RutaTicket - booking-service",
    description="Compra, cancelación y validación de entradas; control de aforo (RN-02 a RN-05).",
    version=__version__,
    root_path=get_settings().root_path,
    lifespan=lifespan,
)
registrar_manejadores(app)
app.include_router(reservas.router)
app.include_router(consultas.router)


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
