"""Modelo de datos de booking_db."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, Integer, Numeric, String, Unicode
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Reserva(Base):
    __tablename__ = "reservas"
    __table_args__ = (
        CheckConstraint("cantidad BETWEEN 1 AND 10", name="ck_reservas_cantidad"),
        CheckConstraint(
            "estado IN ('CONFIRMADA', 'CANCELADA', 'USADA')", name="ck_reservas_estado"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    atraccion_id: Mapped[int] = mapped_column(Integer, index=True)
    fecha_visita: Mapped[date] = mapped_column(Date, index=True)
    cantidad: Mapped[int] = mapped_column(Integer)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estado: Mapped[str] = mapped_column(String(12))
    cliente_nombre: Mapped[str] = mapped_column(Unicode(120))
    cliente_email: Mapped[str] = mapped_column(String(254))
    creada_en: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancelada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    validada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Ocupacion(Base):
    """Plazas vendidas por atractivo y día. Su fila se bloquea para serializar compras (RN-02)."""

    __tablename__ = "ocupacion"
    __table_args__ = (CheckConstraint("vendidas >= 0", name="ck_ocupacion_vendidas"),)

    atraccion_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, primary_key=True)
    vendidas: Mapped[int] = mapped_column(Integer, default=0)
    # Copia del aforo del catálogo en el momento de la última compra (para estadísticas).
    aforo_diario: Mapped[int] = mapped_column(Integer)
