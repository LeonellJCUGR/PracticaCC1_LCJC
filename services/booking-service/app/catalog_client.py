"""Cliente HTTP síncrono de catalog-service (REST + JSON por la red interna)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated

import httpx
from fastapi import Depends, Request


class CatalogoNoDisponible(Exception):
    """catalog-service no responde o devuelve un error inesperado."""


class AtraccionNoEncontrada(Exception):
    def __init__(self, atraccion_id: int) -> None:
        super().__init__(f"No existe el atractivo {atraccion_id}")
        self.atraccion_id = atraccion_id


@dataclass(frozen=True)
class PrecioCatalogo:
    precio_unitario: Decimal
    total: Decimal
    aforo_diario: int
    temporada: str | None


class CatalogClient:
    def __init__(self, http: httpx.Client) -> None:
        self._http = http

    def obtener_precio(self, atraccion_id: int, fecha: date, cantidad: int) -> PrecioCatalogo:
        datos = self._get(
            "/api/v1/precios",
            atraccion_id,
            params={"atraccion_id": atraccion_id, "fecha": fecha.isoformat(), "cantidad": cantidad},
        )
        return PrecioCatalogo(
            precio_unitario=Decimal(str(datos["precio_unitario"])),
            total=Decimal(str(datos["total"])),
            aforo_diario=int(datos["aforo_diario"]),
            temporada=datos.get("temporada"),
        )

    def obtener_aforo(self, atraccion_id: int) -> int:
        datos = self._get(f"/api/v1/atracciones/{atraccion_id}", atraccion_id)
        if not datos.get("activa", True):
            raise AtraccionNoEncontrada(atraccion_id)
        return int(datos["aforo_diario"])

    def _get(self, ruta: str, atraccion_id: int, params: dict | None = None) -> dict:
        try:
            respuesta = self._http.get(ruta, params=params)
        except httpx.HTTPError as exc:
            raise CatalogoNoDisponible(f"Error de red con catalog-service: {exc}") from exc
        if respuesta.status_code == 404:
            raise AtraccionNoEncontrada(atraccion_id)
        if respuesta.status_code >= 400:
            raise CatalogoNoDisponible(f"catalog-service respondió {respuesta.status_code}")
        return respuesta.json()


def get_catalog(request: Request) -> CatalogClient:
    return request.app.state.catalog


CatalogDep = Annotated[CatalogClient, Depends(get_catalog)]
