"""Acceso a datos con SQLAlchemy 2.0 (SQL Server en local/Azure, SQLite en tests)."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def build_engine(url: str) -> Engine:
    if url.startswith("sqlite"):
        kwargs: dict = {"connect_args": {"check_same_thread": False}}
        if url in ("sqlite://", "sqlite:///:memory:"):
            kwargs["poolclass"] = StaticPool
        return create_engine(url, **kwargs)
    # pool_pre_ping: Azure SQL serverless se pausa y cierra conexiones inactivas.
    return create_engine(url, pool_pre_ping=True, pool_recycle=1800)


class Database:
    def __init__(self, url: str) -> None:
        self.engine = build_engine(url)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def create_schema(self, retries: int = 30, delay: float = 2.0) -> None:
        """Crea las tablas; reintenta mientras la base de datos arranca o se reanuda."""
        for intento in range(1, retries + 1):
            try:
                Base.metadata.create_all(self.engine)
                return
            except DBAPIError as exc:
                if intento == retries:
                    raise
                logger.warning("BD no disponible (intento %s/%s): %s", intento, retries, exc)
                time.sleep(delay)

    def ping(self) -> bool:
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except DBAPIError:
            return False


def get_session(request: Request) -> Iterator[Session]:
    db: Database = request.app.state.db
    with db.session_factory() as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]
