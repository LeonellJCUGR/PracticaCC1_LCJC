"""Pruebas de integración de sistema contra el clúster de docker compose.

Llevan a cabo el flujo de trabajo real: cliente -> api-gateway -> booking-service -> catalog-service
-> SQL Server. Todas las peticiones entran por el API Gateway, igual que un cliente real.
Requieren el entorno levantado (docker compose up -d). URL configurable con GATEWAY_URL.
"""

from __future__ import annotations

import os
import random
import time
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")
HOY = datetime.now(ZoneInfo(os.getenv("APP_TIMEZONE", "Europe/Madrid"))).date()


def _esperar(prefijo: str, segundos: int = 180) -> None:
    """Espera a que el servicio publicado en GATEWAY_URL/<prefijo> esté listo (BD incluida)."""
    url = f"{GATEWAY_URL}{prefijo}"
    limite = time.monotonic() + segundos
    while time.monotonic() < limite:
        try:
            if httpx.get(f"{url}/health/ready", timeout=3).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(3)
    pytest.fail(f"{url} no está listo tras {segundos} s")


@pytest.fixture(scope="session")
def catalog() -> httpx.Client:
    _esperar("/catalog")
    with httpx.Client(base_url=GATEWAY_URL, timeout=10) as client:
        yield client


@pytest.fixture(scope="session")
def booking(catalog) -> httpx.Client:
    _esperar("/booking")
    with httpx.Client(base_url=GATEWAY_URL, timeout=10) as client:
        yield client


@pytest.fixture
def atraccion(catalog) -> dict:
    respuesta = catalog.post(
        "/api/v1/atracciones",
        json={"nombre": f"E2E {random.randint(1, 10**6)}", "precio_base": 10.00, "aforo_diario": 3},
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _comprar(booking: httpx.Client, atraccion_id: int, fecha: date, cantidad: int):
    return booking.post(
        "/api/v1/reservas",
        json={
            "atraccion_id": atraccion_id,
            "fecha_visita": fecha.isoformat(),
            "cantidad": cantidad,
            "cliente": {"nombre": "Prueba E2E", "email": "e2e@example.com"},
        },
    )


def test_precio_con_temporada(catalog, atraccion):
    # Fecha lejana y aleatoria para no interferir con temporadas de otras ejecuciones.
    fecha = date(2090, 1, 1) + timedelta(days=random.randint(0, 3000))
    temporada = catalog.post(
        "/api/v1/temporadas",
        json={
            "nombre": "Campaña E2E",
            "fecha_inicio": fecha.isoformat(),
            "fecha_fin": fecha.isoformat(),
            "descuento_porcentaje": 25,
        },
    ).json()
    try:
        precio = catalog.get(
            "/api/v1/precios",
            params={"atraccion_id": atraccion["id"], "fecha": fecha.isoformat(), "cantidad": 2},
        ).json()
        assert precio["precio_unitario"] == 7.5
        assert precio["total"] == 15.0
    finally:
        catalog.delete(f"/api/v1/temporadas/{temporada['id']}")


def test_compra_aforo_cancelacion_y_validacion(booking, atraccion):
    visita = HOY + timedelta(days=10)

    primera = _comprar(booking, atraccion["id"], visita, 2)
    assert primera.status_code == 201, primera.text
    codigo = primera.json()["codigo"]

    sin_aforo = _comprar(booking, atraccion["id"], visita, 2)
    assert sin_aforo.status_code == 409
    assert sin_aforo.json()["error"] == "AFORO_COMPLETO"

    cancelada = booking.post(f"/api/v1/reservas/{codigo}/cancelacion")
    assert cancelada.status_code == 200
    assert cancelada.json()["estado"] == "CANCELADA"

    disponibilidad = booking.get(
        "/api/v1/disponibilidad",
        params={"atraccion_id": atraccion["id"], "fecha": visita.isoformat()},
    ).json()
    assert disponibilidad["disponibles"] == 3

    # Entrada para hoy: se valida una única vez
    hoy = _comprar(booking, atraccion["id"], HOY, 1).json()["codigo"]
    assert booking.post(f"/api/v1/reservas/{hoy}/validacion").json()["estado"] == "USADA"
    assert booking.post(f"/api/v1/reservas/{hoy}/validacion").status_code == 409


def test_atraccion_inexistente(booking):
    respuesta = _comprar(booking, 999_999_999, HOY + timedelta(days=1), 1)
    assert respuesta.status_code == 404
