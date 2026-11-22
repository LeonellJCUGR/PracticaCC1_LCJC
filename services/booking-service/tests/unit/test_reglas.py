"""Pruebas unitarias de RN-02 a RN-05 y de las estadísticas (lógica pura)."""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest

from app import reglas
from app.reglas import EstadoReserva, ReglaNegocioError, VentaDia

MADRID = ZoneInfo("Europe/Madrid")
HOY = date(2026, 11, 10)


def _error(funcion, *args) -> ReglaNegocioError:
    with pytest.raises(ReglaNegocioError) as info:
        funcion(*args)
    return info.value


# ---------- RN-03 ----------


@pytest.mark.parametrize("dias", [0, 1, 90])
def test_fechas_validas(dias):
    reglas.validar_compra(HOY + timedelta(days=dias), 1, HOY)


def test_fecha_pasada():
    error = _error(reglas.validar_compra, HOY - timedelta(days=1), 1, HOY)
    assert (error.status_code, error.error) == (422, "FECHA_PASADA")


def test_mas_de_90_dias():
    error = _error(reglas.validar_compra, HOY + timedelta(days=91), 1, HOY)
    assert error.error == "FECHA_DEMASIADO_LEJANA"


@pytest.mark.parametrize("cantidad", [0, 11])
def test_cantidad_fuera_de_rango(cantidad):
    assert _error(reglas.validar_compra, HOY, cantidad, HOY).error == "CANTIDAD_NO_VALIDA"


# ---------- RN-02 ----------


def test_aforo_justo_se_permite():
    reglas.comprobar_aforo(147, 3, 150, HOY)


def test_aforo_superado():
    error = _error(reglas.comprobar_aforo, 148, 3, 150, HOY)
    assert (error.status_code, error.error) == (409, "AFORO_COMPLETO")
    assert error.detalle == "Solo quedan 2 plazas para el 2026-11-10"


def test_aforo_mensaje_singular():
    assert "queda 1 plaza" in _error(reglas.comprobar_aforo, 149, 2, 150, HOY).detalle


def test_plazas_libres_nunca_negativas():
    assert reglas.plazas_libres(10, 5) == 0


# ---------- RN-04 ----------


def test_cancelacion_justo_en_el_limite():
    visita = date(2026, 11, 15)
    limite = datetime(2026, 11, 14, 0, 0, tzinfo=MADRID)
    reglas.comprobar_cancelacion(EstadoReserva.CONFIRMADA, visita, limite)


def test_cancelacion_fuera_de_plazo():
    visita = date(2026, 11, 15)
    tarde = datetime(2026, 11, 14, 0, 1, tzinfo=MADRID)
    error = _error(reglas.comprobar_cancelacion, EstadoReserva.CONFIRMADA, visita, tarde)
    assert error.error == "PLAZO_CANCELACION_VENCIDO"


@pytest.mark.parametrize("estado", [EstadoReserva.CANCELADA, EstadoReserva.USADA])
def test_solo_se_cancelan_confirmadas(estado):
    ahora = datetime(2026, 11, 1, tzinfo=MADRID)
    error = _error(reglas.comprobar_cancelacion, estado, date(2026, 11, 15), ahora)
    assert error.error == "RESERVA_NO_CANCELABLE"


# ---------- RN-05 ----------


def test_validacion_el_dia_de_la_visita():
    reglas.comprobar_validacion(EstadoReserva.CONFIRMADA, HOY, HOY)


@pytest.mark.parametrize(
    ("estado", "fecha", "codigo"),
    [
        (EstadoReserva.USADA, HOY, "ENTRADA_YA_USADA"),
        (EstadoReserva.CANCELADA, HOY, "RESERVA_CANCELADA"),
        (EstadoReserva.CONFIRMADA, HOY + timedelta(days=1), "FECHA_NO_VALIDA"),
        (EstadoReserva.CONFIRMADA, HOY - timedelta(days=1), "FECHA_NO_VALIDA"),
    ],
)
def test_validacion_rechazada(estado, fecha, codigo):
    assert _error(reglas.comprobar_validacion, estado, fecha, HOY).error == codigo


def test_formato_del_codigo():
    codigos = {reglas.generar_codigo() for _ in range(200)}
    assert all(re.fullmatch(r"RT-[A-HJ-NP-Z2-9]{6}", c) for c in codigos)
    assert len(codigos) > 190  # prácticamente sin colisiones


# ---------- CU-07 ----------


def test_agregar_estadisticas():
    ventas = [
        VentaDia(1, date(2026, 11, 1), 100, Decimal("960.00"), 150),
        VentaDia(1, date(2026, 11, 2), 50, Decimal("480.00"), 150),
        VentaDia(2, date(2026, 11, 1), 10, Decimal("95.50"), 40),
    ]
    resultado = reglas.agregar_estadisticas(ventas)
    assert resultado["total_entradas"] == 160
    assert resultado["ingresos_totales"] == Decimal("1535.50")
    assert resultado["por_atraccion"] == [
        {
            "atraccion_id": 1,
            "entradas": 150,
            "ingresos": Decimal("1440.00"),
            "ocupacion_media": 0.5,
        },
        {"atraccion_id": 2, "entradas": 10, "ingresos": Decimal("95.50"), "ocupacion_media": 0.25},
    ]


def test_estadisticas_vacias():
    assert reglas.agregar_estadisticas([]) == {
        "total_entradas": 0,
        "ingresos_totales": Decimal("0.00"),
        "por_atraccion": [],
    }
