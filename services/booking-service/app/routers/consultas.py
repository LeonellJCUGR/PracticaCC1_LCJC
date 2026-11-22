"""Disponibilidad de plazas y estadísticas de ventas (CU-04, CU-07)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Query
from sqlalchemy import and_, func, select

from app import reglas
from app.catalog_client import CatalogDep
from app.database import SessionDep
from app.errors import APIError
from app.models import Ocupacion, Reserva
from app.reglas import EstadoReserva, VentaDia
from app.schemas import DisponibilidadOut, EstadisticasOut

router = APIRouter(prefix="/api/v1", tags=["consultas"])


@router.get("/disponibilidad", response_model=DisponibilidadOut)
def disponibilidad(
    session: SessionDep,
    catalogo: CatalogDep,
    atraccion_id: Annotated[int, Query(gt=0)],
    fecha: Annotated[date, Query()],
) -> DisponibilidadOut:
    aforo = catalogo.obtener_aforo(atraccion_id)
    vendidas = (
        session.scalar(
            select(Ocupacion.vendidas).where(
                Ocupacion.atraccion_id == atraccion_id, Ocupacion.fecha == fecha
            )
        )
        or 0
    )
    return DisponibilidadOut(
        atraccion_id=atraccion_id,
        fecha=fecha,
        aforo_diario=aforo,
        vendidas=vendidas,
        disponibles=reglas.plazas_libres(vendidas, aforo),
    )


@router.get("/estadisticas/ventas", response_model=EstadisticasOut)
def estadisticas_ventas(
    session: SessionDep,
    desde: Annotated[date, Query()],
    hasta: Annotated[date, Query()],
) -> EstadisticasOut:
    if hasta < desde:
        raise APIError(422, "RANGO_NO_VALIDO", "'hasta' no puede ser anterior a 'desde'")
    filas = session.execute(
        select(
            Reserva.atraccion_id,
            Reserva.fecha_visita,
            func.sum(Reserva.cantidad),
            func.sum(Reserva.total),
            Ocupacion.aforo_diario,
        )
        .join(
            Ocupacion,
            and_(
                Ocupacion.atraccion_id == Reserva.atraccion_id,
                Ocupacion.fecha == Reserva.fecha_visita,
            ),
        )
        .where(
            Reserva.fecha_visita.between(desde, hasta),
            Reserva.estado.in_([EstadoReserva.CONFIRMADA.value, EstadoReserva.USADA.value]),
        )
        .group_by(Reserva.atraccion_id, Reserva.fecha_visita, Ocupacion.aforo_diario)
    ).all()

    ventas = [
        VentaDia(
            atraccion_id=atraccion_id,
            fecha=fecha,
            entradas=int(entradas),
            ingresos=Decimal(str(ingresos)).quantize(Decimal("0.01")),
            aforo_diario=int(aforo),
        )
        for atraccion_id, fecha, entradas, ingresos, aforo in filas
    ]
    return EstadisticasOut(desde=desde, hasta=hasta, **reglas.agregar_estadisticas(ventas))
