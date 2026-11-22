"""Esquemas de entrada/salida de la API (contrato de la sección 6.1 del README)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PlainSerializer, model_validator

# Los importes se exponen como número JSON con 2 decimales (no como string).
Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class AtraccionIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    descripcion: str | None = Field(default=None, max_length=500)
    precio_base: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    aforo_diario: int = Field(gt=0, le=100_000)


class AtraccionUpdate(AtraccionIn):
    activa: bool = True


class AtraccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio_base: Money
    aforo_diario: int
    activa: bool


class TemporadaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    fecha_inicio: date
    fecha_fin: date
    descuento_porcentaje: int = Field(gt=0, le=100)

    @model_validator(mode="after")
    def _rango_valido(self) -> TemporadaIn:
        if self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        return self


class TemporadaOut(TemporadaIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PrecioOut(BaseModel):
    atraccion_id: int
    fecha: date
    cantidad: int
    precio_base: Money
    temporada: str | None
    descuento_porcentaje: int
    precio_unitario: Money
    total: Money
    aforo_diario: int
