"""CU-03: cálculo del precio final para una fecha (RN-01)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import select

from app.database import SessionDep
from app.errors import atraccion_no_encontrada
from app.models import Atraccion, Temporada
from app.pricing import calcular_precio, temporada_vigente
from app.schemas import PrecioOut

router = APIRouter(prefix="/api/v1/precios", tags=["precios"])


@router.get("", response_model=PrecioOut)
def calcular(
    session: SessionDep,
    atraccion_id: Annotated[int, Query(gt=0)],
    fecha: Annotated[date, Query()],
    cantidad: Annotated[int, Query(ge=1, le=10)] = 1,
) -> PrecioOut:
    atraccion = session.get(Atraccion, atraccion_id)
    if atraccion is None or not atraccion.activa:
        raise atraccion_no_encontrada(atraccion_id)

    candidatas = session.scalars(
        select(Temporada)
        .where(Temporada.fecha_inicio <= fecha, Temporada.fecha_fin >= fecha)
        .order_by(Temporada.id)
    )
    temporada = temporada_vigente(candidatas, fecha)
    descuento = temporada.descuento_porcentaje if temporada else 0
    precio = calcular_precio(atraccion.precio_base, descuento, cantidad)

    return PrecioOut(
        atraccion_id=atraccion.id,
        fecha=fecha,
        cantidad=cantidad,
        precio_base=atraccion.precio_base,
        temporada=temporada.nombre if temporada else None,
        descuento_porcentaje=descuento,
        precio_unitario=precio.precio_unitario,
        total=precio.total,
        aforo_diario=atraccion.aforo_diario,
    )
