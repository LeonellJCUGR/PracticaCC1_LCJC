"""Pruebas de integración: API HTTP + capa de persistencia (SQLAlchemy sobre SQLite)."""

from __future__ import annotations


def test_health(client):
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json()["status"] == "ok"
    assert client.get("/health/ready").status_code == 200


# ---------- Atracciones (CU-01, CU-03) ----------


def test_crear_atraccion_devuelve_201(mirador):
    assert mirador == {
        "id": 1,
        "nombre": "Mirador del Valle",
        "descripcion": "Visita guiada al mirador",
        "precio_base": 12.0,
        "aforo_diario": 150,
        "activa": True,
    }


def test_listar_y_obtener(client, mirador):
    assert client.get("/api/v1/atracciones").json() == [mirador]
    assert client.get(f"/api/v1/atracciones/{mirador['id']}").json() == mirador


def test_obtener_inexistente_404(client):
    respuesta = client.get("/api/v1/atracciones/999")
    assert respuesta.status_code == 404
    assert respuesta.json()["error"] == "ATRACCION_NO_ENCONTRADA"


def test_crear_atraccion_invalida_422(client):
    for cuerpo in (
        {"nombre": "", "precio_base": 10, "aforo_diario": 10},
        {"nombre": "X", "precio_base": -1, "aforo_diario": 10},
        {"nombre": "X", "precio_base": 10, "aforo_diario": 0},
        {"nombre": "X", "precio_base": 10.123, "aforo_diario": 10},
    ):
        assert client.post("/api/v1/atracciones", json=cuerpo).status_code == 422


def test_modificar_y_desactivar(client, mirador):
    cambios = {"nombre": "Mirador Norte", "precio_base": 15.5, "aforo_diario": 80, "activa": False}
    respuesta = client.put(f"/api/v1/atracciones/{mirador['id']}", json=cambios)
    assert respuesta.status_code == 200
    assert respuesta.json()["precio_base"] == 15.5
    assert respuesta.json()["activa"] is False
    # Las inactivas no aparecen en el catálogo
    assert client.get("/api/v1/atracciones").json() == []


def test_modificar_inexistente_404(client):
    cuerpo = {"nombre": "X", "precio_base": 10, "aforo_diario": 10}
    assert client.put("/api/v1/atracciones/42", json=cuerpo).status_code == 404


# ---------- Temporadas (CU-02) ----------

INVIERNO = {
    "nombre": "Temporada baja invierno",
    "fecha_inicio": "2026-11-01",
    "fecha_fin": "2027-02-28",
    "descuento_porcentaje": 20,
}


def test_crud_temporadas(client):
    creada = client.post("/api/v1/temporadas", json=INVIERNO)
    assert creada.status_code == 201
    temporada_id = creada.json()["id"]
    assert client.get("/api/v1/temporadas").json() == [{**INVIERNO, "id": temporada_id}]
    assert client.delete(f"/api/v1/temporadas/{temporada_id}").status_code == 204
    assert client.delete(f"/api/v1/temporadas/{temporada_id}").status_code == 404


def test_temporada_con_rango_invertido_422(client):
    cuerpo = {**INVIERNO, "fecha_inicio": "2027-03-01"}
    assert client.post("/api/v1/temporadas", json=cuerpo).status_code == 422


def test_temporada_con_descuento_invalido_422(client):
    for descuento in (0, 101):
        cuerpo = {**INVIERNO, "descuento_porcentaje": descuento}
        assert client.post("/api/v1/temporadas", json=cuerpo).status_code == 422


# ---------- Precios (RN-01) ----------


def test_precio_ejemplo_readme(client, mirador):
    client.post("/api/v1/temporadas", json=INVIERNO)
    respuesta = client.get(
        "/api/v1/precios",
        params={"atraccion_id": mirador["id"], "fecha": "2026-11-15", "cantidad": 3},
    )
    assert respuesta.status_code == 200
    assert respuesta.json() == {
        "atraccion_id": mirador["id"],
        "fecha": "2026-11-15",
        "cantidad": 3,
        "precio_base": 12.0,
        "temporada": "Temporada baja invierno",
        "descuento_porcentaje": 20,
        "precio_unitario": 9.6,
        "total": 28.8,
        "aforo_diario": 150,
    }


def test_precio_aplica_mayor_descuento(client, mirador):
    client.post("/api/v1/temporadas", json=INVIERNO)
    client.post(
        "/api/v1/temporadas",
        json={
            **INVIERNO,
            "nombre": "Campaña",
            "fecha_inicio": "2026-11-27",
            "fecha_fin": "2026-11-30",
            "descuento_porcentaje": 50,
        },
    )
    cuerpo = client.get(
        "/api/v1/precios", params={"atraccion_id": mirador["id"], "fecha": "2026-11-28"}
    ).json()
    assert cuerpo["temporada"] == "Campaña"
    assert cuerpo["precio_unitario"] == 6.0


def test_precio_sin_temporada(client, mirador):
    cuerpo = client.get(
        "/api/v1/precios",
        params={"atraccion_id": mirador["id"], "fecha": "2026-07-01", "cantidad": 2},
    ).json()
    assert cuerpo["temporada"] is None
    assert cuerpo["descuento_porcentaje"] == 0
    assert cuerpo["total"] == 24.0


def test_precio_atraccion_inexistente_404(client):
    respuesta = client.get("/api/v1/precios", params={"atraccion_id": 7, "fecha": "2026-07-01"})
    assert respuesta.status_code == 404


def test_precio_parametros_invalidos_422(client, mirador):
    base = {"atraccion_id": mirador["id"], "fecha": "2026-07-01"}
    assert client.get("/api/v1/precios", params={**base, "cantidad": 0}).status_code == 422
    assert client.get("/api/v1/precios", params={**base, "cantidad": 11}).status_code == 422
    assert client.get("/api/v1/precios", params={**base, "fecha": "no-fecha"}).status_code == 422
