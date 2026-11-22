"""CU-04, CU-05 y CU-06: compra, consulta, cancelación y validación de reservas."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import reglas
from app.catalog_client import CatalogDep, PrecioCatalogo
from app.clock import NowDep
from app.database import SessionDep
from app.errors import APIError, reserva_no_encontrada
from app.models import Ocupacion, Reserva
from app.reglas import EstadoReserva
from app.schemas import ReservaIn, ReservaOut, ValidacionOut

router = APIRouter(prefix="/api/v1/reservas", tags=["reservas"])

MAX_REINTENTOS = 3


def _ocupacion_bloqueada(session: Session, atraccion_id: int, fecha) -> Ocupacion | None:
    # En SQL Server se traduce a WITH (UPDLOCK, ROWLOCK): serializa compras del mismo día.
    consulta = (
        select(Ocupacion)
        .where(Ocupacion.atraccion_id == atraccion_id, Ocupacion.fecha == fecha)
        .with_for_update()
    )
    return session.scalars(consulta).first()


def _buscar_reserva(session: Session, codigo: str) -> Reserva:
    reserva = session.scalars(select(Reserva).where(Reserva.codigo == codigo)).first()
    if reserva is None:
        raise reserva_no_encontrada(codigo)
    return reserva


def _confirmar_compra(
    session: Session, datos: ReservaIn, precio: PrecioCatalogo, ahora: datetime
) -> Reserva:
    ocupacion = _ocupacion_bloqueada(session, datos.atraccion_id, datos.fecha_visita)
    if ocupacion is None:
        ocupacion = Ocupacion(
            atraccion_id=datos.atraccion_id,
            fecha=datos.fecha_visita,
            vendidas=0,
            aforo_diario=precio.aforo_diario,
        )
        session.add(ocupacion)
        session.flush()  # Si otra compra creó la fila a la vez -> IntegrityError -> reintento
    ocupacion.aforo_diario = precio.aforo_diario

    reglas.comprobar_aforo(
        ocupacion.vendidas, datos.cantidad, ocupacion.aforo_diario, datos.fecha_visita
    )

    ocupacion.vendidas += datos.cantidad
    reserva = Reserva(
        codigo=reglas.generar_codigo(),
        atraccion_id=datos.atraccion_id,
        fecha_visita=datos.fecha_visita,
        cantidad=datos.cantidad,
        precio_unitario=precio.precio_unitario,
        total=precio.total,
        estado=EstadoReserva.CONFIRMADA.value,
        cliente_nombre=datos.cliente.nombre,
        cliente_email=str(datos.cliente.email),
        creada_en=ahora.astimezone(UTC),
    )
    session.add(reserva)
    session.commit()
    return reserva


@router.post("", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
def comprar(datos: ReservaIn, session: SessionDep, catalogo: CatalogDep, ahora: NowDep) -> Reserva:
    reglas.validar_compra(datos.fecha_visita, datos.cantidad, ahora.date())
    precio = catalogo.obtener_precio(datos.atraccion_id, datos.fecha_visita, datos.cantidad)

    for _ in range(MAX_REINTENTOS):
        try:
            return _confirmar_compra(session, datos, precio, ahora)
        except IntegrityError:
            # Carrera al crear la fila de ocupación o colisión de código: se reintenta.
            session.rollback()
        except reglas.ReglaNegocioError:
            session.rollback()
            raise
    raise APIError(409, "CONFLICTO_CONCURRENTE", "No se pudo completar la compra, reinténtelo")


@router.get("/{codigo}", response_model=ReservaOut)
def consultar(codigo: str, session: SessionDep) -> Reserva:
    return _buscar_reserva(session, codigo)


@router.post("/{codigo}/cancelacion", response_model=ReservaOut)
def cancelar(codigo: str, session: SessionDep, ahora: NowDep) -> Reserva:
    reserva = _buscar_reserva(session, codigo)
    # Orden de bloqueo igual que en la compra (ocupación -> reserva) para evitar interbloqueos.
    ocupacion = _ocupacion_bloqueada(session, reserva.atraccion_id, reserva.fecha_visita)
    session.refresh(reserva, with_for_update=True)

    reglas.comprobar_cancelacion(reserva.estado, reserva.fecha_visita, ahora)

    if ocupacion is not None:
        ocupacion.vendidas = max(ocupacion.vendidas - reserva.cantidad, 0)
    reserva.estado = EstadoReserva.CANCELADA.value
    reserva.cancelada_en = ahora.astimezone(UTC)
    session.commit()
    return reserva


@router.post("/{codigo}/validacion", response_model=ValidacionOut)
def validar(codigo: str, session: SessionDep, ahora: NowDep) -> Reserva:
    reserva = _buscar_reserva(session, codigo)
    session.refresh(reserva, with_for_update=True)

    reglas.comprobar_validacion(reserva.estado, reserva.fecha_visita, ahora.date())

    reserva.estado = EstadoReserva.USADA.value
    reserva.validada_en = ahora.astimezone(UTC)
    session.commit()
    return reserva
