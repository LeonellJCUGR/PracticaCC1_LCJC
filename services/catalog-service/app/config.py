"""Configuración leída de variables de entorno (factor III de 12-factor)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    database_url: str
    log_level: str
    root_path: str


@lru_cache
def get_settings() -> Settings:
    return Settings(
        # En local/CI apunta a SQL Server; sin variable se usa SQLite para desarrollo rápido.
        database_url=os.getenv("DATABASE_URL", "sqlite:///./catalog.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        # Prefijo con el que el API Gateway publica el servicio (p. ej. "/catalog").
        # Solo afecta a la documentación (Swagger) y a las URLs que genera la app.
        root_path=os.getenv("ROOT_PATH", ""),
    )
