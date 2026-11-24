"""Esquemas de entrada/salida de la API (contrato de la sección 6.2 del README)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer

from app.reglas import MAX_ENTRADAS_POR_COMPRA

Money = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


def _iso_utc(valor: datetime) -> str:
    # SQLite pierde la zona horaria: los instantes se guardan siempre en UTC.
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=UTC)
    return valor.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


UtcDateTime = Annotated[datetime, PlainSerializer(_iso_utc, return_type=str, when_used="json")]


class ClienteIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=120)
    email: EmailStr


class ReservaIn(BaseModel):
    atraccion_id: int = Field(gt=0)
    fecha_visita: date
    cantidad: int = Field(ge=1, le=MAX_ENTRADAS_POR_COMPRA)
    cliente: ClienteIn


class ReservaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    atraccion_id: int
    fecha_visita: date
    cantidad: int
    precio_unitario: Money
    total: Money
    estado: str
    creada_en: UtcDateTime


class ValidacionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    codigo: str
    estado: str
    validada_en: UtcDateTime


class DisponibilidadOut(BaseModel):
    atraccion_id: int
    fecha: date
    aforo_diario: int
    vendidas: int
    disponibles: int


class EstadisticaAtraccion(BaseModel):
    atraccion_id: int
    entradas: int
    ingresos: Money
    ocupacion_media: float


class EstadisticasOut(BaseModel):
    desde: date
    hasta: date
    total_entradas: int
    ingresos_totales: Money
    por_atraccion: list[EstadisticaAtraccion]
