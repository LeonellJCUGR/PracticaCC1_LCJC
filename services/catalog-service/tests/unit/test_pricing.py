"""Pruebas unitarias de RN-01 (lógica pura, sin BD ni HTTP)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import pytest

from app.pricing import calcular_precio, temporada_vigente


@dataclass
class T:
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    descuento_porcentaje: int


INVIERNO = T("Temporada baja invierno", date(2026, 11, 1), date(2027, 2, 28), 20)
CAMPANA = T("Campaña Black Friday", date(2026, 11, 27), date(2026, 11, 30), 35)


def test_ejemplo_del_readme():
    precio = calcular_precio(Decimal("12.00"), 20, 3)
    assert precio.precio_unitario == Decimal("9.60")
    assert precio.total == Decimal("28.80")


def test_sin_descuento_se_cobra_precio_base():
    precio = calcular_precio(Decimal("12.00"), 0, 2)
    assert precio.precio_unitario == Decimal("12.00")
    assert precio.total == Decimal("24.00")


def test_redondeo_a_centimos_half_up():
    # 9.99 * 0.85 = 8.4915 -> 8.49 ; 10.05 * 0.5 = 5.025 -> 5.03
    assert calcular_precio(Decimal("9.99"), 15, 1).precio_unitario == Decimal("8.49")
    assert calcular_precio(Decimal("10.05"), 50, 1).precio_unitario == Decimal("5.03")


def test_descuento_total():
    assert calcular_precio(Decimal("12.00"), 100, 4).total == Decimal("0.00")


@pytest.mark.parametrize(("descuento", "cantidad"), [(-1, 1), (101, 1), (10, 0)])
def test_parametros_invalidos(descuento, cantidad):
    with pytest.raises(ValueError):
        calcular_precio(Decimal("12.00"), descuento, cantidad)


def test_sin_temporada_vigente():
    assert temporada_vigente([INVIERNO], date(2026, 6, 1)) is None


def test_limites_del_rango_son_inclusivos():
    assert temporada_vigente([INVIERNO], date(2026, 11, 1)) is INVIERNO
    assert temporada_vigente([INVIERNO], date(2027, 2, 28)) is INVIERNO


def test_solapamiento_aplica_mayor_descuento():
    assert temporada_vigente([INVIERNO, CAMPANA], date(2026, 11, 28)) is CAMPANA
    assert temporada_vigente([CAMPANA, INVIERNO], date(2026, 11, 28)) is CAMPANA


def test_empate_se_queda_con_la_primera():
    otra = T("Otra", date(2026, 11, 1), date(2026, 12, 31), 20)
    assert temporada_vigente([INVIERNO, otra], date(2026, 11, 15)) is INVIERNO
