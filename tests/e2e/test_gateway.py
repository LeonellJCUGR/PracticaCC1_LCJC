"""Pruebas del API Gateway: enrutado, cabeceras y errores uniformes."""

from __future__ import annotations

import os

import httpx
import pytest

GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8080")


@pytest.fixture(scope="module")
def gateway() -> httpx.Client:
    with httpx.Client(base_url=GATEWAY_URL, timeout=10) as client:
        yield client


def test_salud_del_gateway(gateway):
    respuesta = gateway.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok", "service": "api-gateway"}


def test_enruta_a_cada_microservicio(gateway):
    assert gateway.get("/catalog/health").json()["service"] == "catalog-service"
    assert gateway.get("/booking/health").json()["service"] == "booking-service"
    # Rutas públicas de la API, sin prefijo de servicio
    assert gateway.get("/api/v1/atracciones").status_code == 200
    rango = {"desde": "2026-01-01", "hasta": "2026-01-31"}
    assert gateway.get("/api/v1/estadisticas/ventas", params=rango).status_code == 200


def test_ruta_desconocida_devuelve_json(gateway):
    respuesta = gateway.get("/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "RUTA_NO_ENCONTRADA"


def test_cabeceras_de_trazabilidad_y_seguridad(gateway):
    respuesta = gateway.get("/api/v1/atracciones")
    assert len(respuesta.headers["x-request-id"]) == 32
    assert respuesta.headers["x-content-type-options"] == "nosniff"
    assert "nginx/" not in respuesta.headers.get("server", "")


def test_swagger_publicado_tras_el_gateway(gateway):
    for prefijo in ("/catalog", "/booking"):
        assert gateway.get(f"{prefijo}/docs").status_code == 200
        openapi = gateway.get(f"{prefijo}/openapi.json").json()
        assert openapi["servers"] == [{"url": prefijo}]
