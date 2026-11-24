"""Modelo de datos de catalog_db."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, Integer, Numeric, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Atraccion(Base):
    __tablename__ = "atracciones"
    __table_args__ = (
        CheckConstraint("precio_base > 0", name="ck_atracciones_precio_base"),
        CheckConstraint("aforo_diario > 0", name="ck_atracciones_aforo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Unicode(120))
    descripcion: Mapped[str | None] = mapped_column(Unicode(500), nullable=True)
    precio_base: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    aforo_diario: Mapped[int] = mapped_column(Integer)
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class Temporada(Base):
    __tablename__ = "temporadas"
    __table_args__ = (
        CheckConstraint("fecha_fin >= fecha_inicio", name="ck_temporadas_rango"),
        CheckConstraint(
            "descuento_porcentaje > 0 AND descuento_porcentaje <= 100",
            name="ck_temporadas_descuento",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(Unicode(120))
    fecha_inicio: Mapped[date] = mapped_column(Date, index=True)
    fecha_fin: Mapped[date] = mapped_column(Date, index=True)
    descuento_porcentaje: Mapped[int] = mapped_column(Integer)
