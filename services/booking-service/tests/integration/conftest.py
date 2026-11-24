"""Fixtures comunes: SQLite en memoria, catálogo simulado y reloj fijo."""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

os.environ["DATABASE_URL"] = "sqlite://"
os.environ["CATALOG_SERVICE_URL"] = "http://catalogo-falso.invalid"

from fastapi.testclient import TestClient

from app.catalog_client import (
    AtraccionNoEncontrada,
    CatalogoNoDisponible,
    PrecioCatalogo,
    get_catalog,
)
from app.clock import get_now
from app.database import Base
from app.main import app

MADRID = ZoneInfo("Europe/Madrid")
AHORA = datetime(2026, 11, 10, 10, 0, tzinfo=MADRID)


class FakeCatalog:
    """Sustituye a catalog-service: atractivo 1 a 12 EUR con 20 % de descuento y aforo 5."""

    def __init__(self) -> None:
        self.atracciones = {1: (Decimal("12.00"), 20, 5)}
        self.caido = False

    def _datos(self, atraccion_id: int) -> tuple[Decimal, int, int]:
        if self.caido:
            raise CatalogoNoDisponible("catalog-service respondió 503")
        if atraccion_id not in self.atracciones:
            raise AtraccionNoEncontrada(atraccion_id)
        return self.atracciones[atraccion_id]

    def obtener_precio(self, atraccion_id: int, fecha: date, cantidad: int) -> PrecioCatalogo:
        base, descuento, aforo = self._datos(atraccion_id)
        unitario = (base * (100 - descuento) / 100).quantize(Decimal("0.01"))
        return PrecioCatalogo(unitario, unitario * cantidad, aforo, "Temporada baja")

    def obtener_aforo(self, atraccion_id: int) -> int:
        return self._datos(atraccion_id)[2]


class Reloj:
    def __init__(self) -> None:
        self.ahora = AHORA

    def __call__(self) -> datetime:
        return self.ahora


@pytest.fixture
def catalogo() -> FakeCatalog:
    return FakeCatalog()


@pytest.fixture
def reloj() -> Reloj:
    return Reloj()


@pytest.fixture
def client(catalogo: FakeCatalog, reloj: Reloj) -> Iterator[TestClient]:
    app.dependency_overrides[get_catalog] = lambda: catalogo
    app.dependency_overrides[get_now] = reloj
    with TestClient(app) as test_client:
        engine = app.state.db.engine
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def comprar(client: TestClient):
    def _comprar(fecha: str = "2026-11-15", cantidad: int = 3, atraccion_id: int = 1):
        return client.post(
            "/api/v1/reservas",
            json={
                "atraccion_id": atraccion_id,
                "fecha_visita": fecha,
                "cantidad": cantidad,
                "cliente": {"nombre": "Ana López", "email": "ana@example.com"},
            },
        )

    return _comprar
