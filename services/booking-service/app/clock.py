"""Reloj inyectable: permite fijar "ahora" en las pruebas (RN-03, RN-04 y RN-05 dependen de él)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.config import get_settings


def get_now() -> datetime:
    return datetime.now(ZoneInfo(get_settings().app_timezone))


NowDep = Annotated[datetime, Depends(get_now)]
