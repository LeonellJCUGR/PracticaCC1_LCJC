"""CU-02: temporadas de descuento."""

from __future__ import annotations

from fastapi import APIRouter, Response, status
from sqlalchemy import select

from app.database import SessionDep
from app.errors import APIError
from app.models import Temporada
from app.schemas import TemporadaIn, TemporadaOut

router = APIRouter(prefix="/api/v1/temporadas", tags=["temporadas"])


@router.get("", response_model=list[TemporadaOut])
def listar_temporadas(session: SessionDep) -> list[Temporada]:
    consulta = select(Temporada).order_by(Temporada.fecha_inicio, Temporada.id)
    return list(session.scalars(consulta))


@router.post("", response_model=TemporadaOut, status_code=status.HTTP_201_CREATED)
def crear_temporada(datos: TemporadaIn, session: SessionDep) -> Temporada:
    temporada = Temporada(**datos.model_dump())
    session.add(temporada)
    session.commit()
    return temporada


@router.delete("/{temporada_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_temporada(temporada_id: int, session: SessionDep) -> Response:
    temporada = session.get(Temporada, temporada_id)
    if temporada is None:
        raise APIError(404, "TEMPORADA_NO_ENCONTRADA", f"No existe la temporada {temporada_id}")
    session.delete(temporada)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
