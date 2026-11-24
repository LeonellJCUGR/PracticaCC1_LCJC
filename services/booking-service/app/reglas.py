"""Reglas de negocio puras de reservas (RN-02 a RN-05). Sin dependencias de framework ni BD."""

from __future__ import annotations

import secrets
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum

MAX_ENTRADAS_POR_COMPRA = 10
MAX_DIAS_ANTELACION = 90
HORAS_MINIMAS_CANCELACION = 24
ALFABETO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # sin 0/O ni 1/I para evitar confusiones
LONGITUD_CODIGO = 6


class EstadoReserva(StrEnum):
    CONFIRMADA = "CONFIRMADA"
    CANCELADA = "CANCELADA"
    USADA = "USADA"


class ReglaNegocioError(Exception):
    """Violación de una regla de negocio. `status_code` es el código HTTP sugerido."""

    def __init__(self, status_code: int, error: str, detalle: str) -> None:
        super().__init__(detalle)
        self.status_code = status_code
        self.error = error
        self.detalle = detalle


# RN-03: fechas y cantidad válidas


def validar_compra(fecha_visita: date, cantidad: int, hoy: date) -> None:
    if not 1 <= cantidad <= MAX_ENTRADAS_POR_COMPRA:
        raise ReglaNegocioError(
            422,
            "CANTIDAD_NO_VALIDA",
            f"Se pueden comprar entre 1 y {MAX_ENTRADAS_POR_COMPRA} entradas por compra",
        )
    if fecha_visita < hoy:
        raise ReglaNegocioError(
            422, "FECHA_PASADA", f"No se pueden comprar entradas para {fecha_visita.isoformat()}"
        )
    if fecha_visita > hoy + timedelta(days=MAX_DIAS_ANTELACION):
        raise ReglaNegocioError(
            422,
            "FECHA_DEMASIADO_LEJANA",
            f"Solo se venden entradas con un máximo de {MAX_DIAS_ANTELACION} días de antelación",
        )


# RN-02: control de aforo


def plazas_libres(vendidas: int, aforo_diario: int) -> int:
    return max(aforo_diario - vendidas, 0)


def comprobar_aforo(vendidas: int, cantidad: int, aforo_diario: int, fecha: date) -> None:
    if vendidas + cantidad > aforo_diario:
        libres = plazas_libres(vendidas, aforo_diario)
        texto = "queda 1 plaza" if libres == 1 else f"quedan {libres} plazas"
        raise ReglaNegocioError(409, "AFORO_COMPLETO", f"Solo {texto} para el {fecha.isoformat()}")


# RN-04: cancelación


def limite_cancelacion(fecha_visita: date, tz) -> datetime:
    inicio_visita = datetime.combine(fecha_visita, time.min, tzinfo=tz)
    return inicio_visita - timedelta(hours=HORAS_MINIMAS_CANCELACION)


def comprobar_cancelacion(estado: str, fecha_visita: date, ahora: datetime) -> None:
    if estado != EstadoReserva.CONFIRMADA:
        raise ReglaNegocioError(
            409, "RESERVA_NO_CANCELABLE", f"La reserva está {estado} y no puede cancelarse"
        )
    if ahora > limite_cancelacion(fecha_visita, ahora.tzinfo):
        raise ReglaNegocioError(
            409,
            "PLAZO_CANCELACION_VENCIDO",
            f"Solo se puede cancelar hasta {HORAS_MINIMAS_CANCELACION} h antes de la visita",
        )


#  RN-05: validación de acceso


def comprobar_validacion(estado: str, fecha_visita: date, hoy: date) -> None:
    if estado == EstadoReserva.USADA:
        raise ReglaNegocioError(409, "ENTRADA_YA_USADA", "La entrada ya fue validada")
    if estado == EstadoReserva.CANCELADA:
        raise ReglaNegocioError(409, "RESERVA_CANCELADA", "La reserva está cancelada")
    if fecha_visita != hoy:
        raise ReglaNegocioError(
            409,
            "FECHA_NO_VALIDA",
            f"La entrada es para el {fecha_visita.isoformat()} y solo puede validarse ese día",
        )


def generar_codigo() -> str:
    return "RT-" + "".join(secrets.choice(ALFABETO_CODIGO) for _ in range(LONGITUD_CODIGO))


# CU-07: estadísticas


@dataclass(frozen=True)
class VentaDia:
    atraccion_id: int
    fecha: date
    entradas: int
    ingresos: Decimal
    aforo_diario: int


def agregar_estadisticas(ventas: Iterable[VentaDia]) -> dict:
    """Agrega ventas diarias por atractivo.

    ocupacion_media = media, sobre los días con ventas, de entradas_del_dia / aforo_diario.
    """
    por_atraccion: dict[int, list[VentaDia]] = defaultdict(list)
    for venta in ventas:
        por_atraccion[venta.atraccion_id].append(venta)

    resumen = []
    for atraccion_id in sorted(por_atraccion):
        dias = por_atraccion[atraccion_id]
        ocupaciones = [d.entradas / d.aforo_diario for d in dias if d.aforo_diario > 0]
        resumen.append(
            {
                "atraccion_id": atraccion_id,
                "entradas": sum(d.entradas for d in dias),
                "ingresos": sum((d.ingresos for d in dias), Decimal("0.00")),
                "ocupacion_media": round(sum(ocupaciones) / len(ocupaciones), 2)
                if ocupaciones
                else 0.0,
            }
        )
    return {
        "total_entradas": sum(r["entradas"] for r in resumen),
        "ingresos_totales": sum((r["ingresos"] for r in resumen), Decimal("0.00")),
        "por_atraccion": resumen,
    }
