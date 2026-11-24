"""Fixtures comunes: La app se levanta desde SQLite en memoria."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

os.environ["DATABASE_URL"] = "sqlite://"

from fastapi.testclient import TestClient

from app.database import Base
from app.main import app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        engine = app.state.db.engine
        Base.metadata.drop_all(engine)
        Base.metadata.create_all(engine)
        yield test_client


@pytest.fixture
def mirador(client: TestClient) -> dict:
    respuesta = client.post(
        "/api/v1/atracciones",
        json={
            "nombre": "Mirador del Valle",
            "descripcion": "Visita guiada al mirador",
            "precio_base": 12.00,
            "aforo_diario": 150,
        },
    )
    assert respuesta.status_code == 201
    return respuesta.json()
