"""Configuración leída de variables de entorno (factor III de 12-factor)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    catalog_service_url: str
    catalog_timeout_seconds: float
    app_timezone: str
    log_level: str
    root_path: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///./booking.db"),
        catalog_service_url=os.getenv("CATALOG_SERVICE_URL", "http://localhost:8001"),
        catalog_timeout_seconds=float(os.getenv("CATALOG_TIMEOUT_SECONDS", "5")),
        # Las fechas de visita son locales al atractivo (RN-04 y RN-05 dependen de "hoy").
        app_timezone=os.getenv("APP_TIMEZONE", "Europe/Madrid"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        # Prefijo con el que el API Gateway publica el servicio (p. ej. "/catalog").
        # Solo afecta a la documentación (Swagger) y a las URLs que genera la app.
        root_path=os.getenv("ROOT_PATH", ""),
    )
