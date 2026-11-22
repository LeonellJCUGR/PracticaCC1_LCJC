"""CU-01 / CU-03: gestión y consulta de atractivos."""

from __future__ import annotations

from fastapi import APIRouter, status
from sqlalchemy import select, true

from app.database import SessionDep
from app.errors import atraccion_no_encontrada
from app.models import Atraccion
from app.schemas import AtraccionIn, AtraccionOut, AtraccionUpdate

router = APIRouter(prefix="/api/v1/atracciones", tags=["atracciones"])


@router.get("", response_model=list[AtraccionOut])
def listar_atracciones(session: SessionDep) -> list[Atraccion]:
    consulta = select(Atraccion).where(Atraccion.activa == true()).order_by(Atraccion.id)
    return list(session.scalars(consulta))


@router.get("/{atraccion_id}", response_model=AtraccionOut)
def obtener_atraccion(atraccion_id: int, session: SessionDep) -> Atraccion:
    atraccion = session.get(Atraccion, atraccion_id)
    if atraccion is None:
        raise atraccion_no_encontrada(atraccion_id)
    return atraccion


@router.post("", response_model=AtraccionOut, status_code=status.HTTP_201_CREATED)
def crear_atraccion(datos: AtraccionIn, session: SessionDep) -> Atraccion:
    atraccion = Atraccion(**datos.model_dump(), activa=True)
    session.add(atraccion)
    session.commit()
    return atraccion


@router.put("/{atraccion_id}", response_model=AtraccionOut)
def modificar_atraccion(
    atraccion_id: int, datos: AtraccionUpdate, session: SessionDep
) -> Atraccion:
    atraccion = session.get(Atraccion, atraccion_id)
    if atraccion is None:
        raise atraccion_no_encontrada(atraccion_id)
    for campo, valor in datos.model_dump().items():
        setattr(atraccion, campo, valor)
    session.commit()
    return atraccion
