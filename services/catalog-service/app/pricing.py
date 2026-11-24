"""Lógica de negocio pura de precios (RN-01). Sin dependencias de framework ni BD."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

CENTIMO = Decimal("0.01")


class TemporadaLike(Protocol):
    nombre: str
    fecha_inicio: date
    fecha_fin: date
    descuento_porcentaje: int


@dataclass(frozen=True)
class Precio:
    precio_unitario: Decimal
    total: Decimal


def temporada_vigente[T: TemporadaLike](temporadas: Iterable[T], fecha: date) -> T | None:
    """Devuelve la temporada aplicable a `fecha`.

    Si coinciden varias, gana la de mayor descuento; ante empate, la primera recibida.
    """
    vigentes = [t for t in temporadas if t.fecha_inicio <= fecha <= t.fecha_fin]
    return max(vigentes, key=lambda t: t.descuento_porcentaje, default=None)


def calcular_precio(precio_base: Decimal, descuento_porcentaje: int, cantidad: int) -> Precio:
    """precio_unitario = precio_base x (1 - descuento/100), redondeado a céntimos."""
    if cantidad < 1:
        raise ValueError("La cantidad debe ser al menos 1")
    if not 0 <= descuento_porcentaje <= 100:
        raise ValueError("El descuento debe estar entre 0 y 100")
    factor = (Decimal(100) - Decimal(descuento_porcentaje)) / Decimal(100)
    unitario = (Decimal(precio_base) * factor).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    total = (unitario * cantidad).quantize(CENTIMO, rounding=ROUND_HALF_UP)
    return Precio(precio_unitario=unitario, total=total)
