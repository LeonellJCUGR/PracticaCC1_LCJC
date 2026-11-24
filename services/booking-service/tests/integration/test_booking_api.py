"""Pruebas de integración: API HTTP + persistencia (SQLite) con catálogo simulado."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/health/ready").status_code == 200


# CU-04: compra


def test_compra_confirmada(comprar):
    respuesta = comprar()
    assert respuesta.status_code == 201
    cuerpo = respuesta.json()
    assert cuerpo["codigo"].startswith("RT-")
    assert cuerpo["estado"] == "CONFIRMADA"
    assert cuerpo["precio_unitario"] == 9.6
    assert cuerpo["total"] == 28.8
    assert cuerpo["creada_en"] == "2026-11-10T09:00:00Z"  # 10:00 Madrid = 09:00 UTC


def test_compra_actualiza_disponibilidad(client, comprar):
    comprar(cantidad=2)
    cuerpo = client.get(
        "/api/v1/disponibilidad", params={"atraccion_id": 1, "fecha": "2026-11-15"}
    ).json()
    assert cuerpo == {
        "atraccion_id": 1,
        "fecha": "2026-11-15",
        "aforo_diario": 5,
        "vendidas": 2,
        "disponibles": 3,
    }


def test_aforo_completo_409(comprar):
    assert comprar(cantidad=4).status_code == 201
    respuesta = comprar(cantidad=2)
    assert respuesta.status_code == 409
    assert respuesta.json() == {
        "error": "AFORO_COMPLETO",
        "detalle": "Solo queda 1 plaza para el 2026-11-15",
    }
    # El aforo es por día: otra fecha sigue libre
    assert comprar(fecha="2026-11-16", cantidad=5).status_code == 201


def test_compra_fecha_pasada_422(comprar):
    respuesta = comprar(fecha="2026-11-09")
    assert respuesta.status_code == 422
    assert respuesta.json()["error"] == "FECHA_PASADA"


def test_compra_mas_de_90_dias_422(comprar):
    assert comprar(fecha="2027-02-09").status_code == 422


def test_compra_mas_de_10_entradas_422(comprar):
    assert comprar(cantidad=11).status_code == 422


def test_compra_email_invalido_422(client):
    cuerpo = {
        "atraccion_id": 1,
        "fecha_visita": "2026-11-15",
        "cantidad": 1,
        "cliente": {"nombre": "Ana", "email": "no-es-un-email"},
    }
    assert client.post("/api/v1/reservas", json=cuerpo).status_code == 422


def test_compra_atraccion_inexistente_404(comprar):
    respuesta = comprar(atraccion_id=99)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "ATRACCION_NO_ENCONTRADA"


def test_catalogo_caido_503(comprar, catalogo):
    catalogo.caido = True
    respuesta = comprar()
    assert respuesta.status_code == 503
    assert respuesta.json()["error"] == "CATALOGO_NO_DISPONIBLE"


# CU-05: consulta y cancelación


def test_consultar_reserva(client, comprar):
    reserva = comprar().json()
    assert client.get(f"/api/v1/reservas/{reserva['codigo']}").json() == reserva
    assert client.get("/api/v1/reservas/RT-NOEXIS").status_code == 404


def test_cancelar_libera_aforo(client, comprar):
    codigo = comprar(cantidad=5).json()["codigo"]
    respuesta = client.post(f"/api/v1/reservas/{codigo}/cancelacion")
    assert respuesta.status_code == 200
    assert respuesta.json()["estado"] == "CANCELADA"
    disponibilidad = client.get(
        "/api/v1/disponibilidad", params={"atraccion_id": 1, "fecha": "2026-11-15"}
    ).json()
    assert disponibilidad["disponibles"] == 5
    # Cancelar de nuevo no está permitido
    segunda = client.post(f"/api/v1/reservas/{codigo}/cancelacion")
    assert segunda.status_code == 409
    assert segunda.json()["error"] == "RESERVA_NO_CANCELABLE"


def test_cancelar_con_menos_de_24h_409(client, comprar, reloj):
    codigo = comprar(fecha="2026-11-11").json()["codigo"]
    reloj.ahora = datetime(2026, 11, 10, 12, 0, tzinfo=MADRID)
    respuesta = client.post(f"/api/v1/reservas/{codigo}/cancelacion")
    assert respuesta.status_code == 409
    assert respuesta.json()["error"] == "PLAZO_CANCELACION_VENCIDO"


def test_cancelar_inexistente_404(client):
    assert client.post("/api/v1/reservas/RT-XXXXXX/cancelacion").status_code == 404


# CU-06: validación


def test_validar_el_dia_de_la_visita(client, comprar, reloj):
    codigo = comprar(fecha="2026-11-15").json()["codigo"]

    otro_dia = client.post(f"/api/v1/reservas/{codigo}/validacion")
    assert otro_dia.status_code == 409
    assert otro_dia.json()["error"] == "FECHA_NO_VALIDA"

    reloj.ahora = datetime(2026, 11, 15, 10, 12, tzinfo=MADRID)
    respuesta = client.post(f"/api/v1/reservas/{codigo}/validacion")
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "codigo": codigo,
        "estado": "USADA",
        "validada_en": "2026-11-15T09:12:00Z",
    }

    repetida = client.post(f"/api/v1/reservas/{codigo}/validacion")
    assert repetida.status_code == 409
    assert repetida.json()["error"] == "ENTRADA_YA_USADA"


def test_no_se_valida_una_cancelada(client, comprar, reloj):
    codigo = comprar(fecha="2026-11-15").json()["codigo"]
    client.post(f"/api/v1/reservas/{codigo}/cancelacion")
    reloj.ahora = datetime(2026, 11, 15, 9, 0, tzinfo=MADRID)
    respuesta = client.post(f"/api/v1/reservas/{codigo}/validacion")
    assert respuesta.json()["error"] == "RESERVA_CANCELADA"


# CU-07: estadísticas


def test_estadisticas_excluyen_canceladas(client, comprar):
    comprar(fecha="2026-11-15", cantidad=3)
    comprar(fecha="2026-11-16", cantidad=2)
    cancelada = comprar(fecha="2026-11-16", cantidad=1).json()["codigo"]
    client.post(f"/api/v1/reservas/{cancelada}/cancelacion")

    cuerpo = client.get(
        "/api/v1/estadisticas/ventas", params={"desde": "2026-11-01", "hasta": "2026-11-30"}
    ).json()
    assert cuerpo == {
        "desde": "2026-11-01",
        "hasta": "2026-11-30",
        "total_entradas": 5,
        "ingresos_totales": 48.0,
        "por_atraccion": [
            # días: 3/5 = 0.6 y 2/5 = 0.4 -> media 0.5
            {"atraccion_id": 1, "entradas": 5, "ingresos": 48.0, "ocupacion_media": 0.5}
        ],
    }


def test_estadisticas_rango_invertido_422(client):
    respuesta = client.get(
        "/api/v1/estadisticas/ventas", params={"desde": "2026-11-30", "hasta": "2026-11-01"}
    )
    assert respuesta.status_code == 422
