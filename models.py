# models.py
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (Integer, String, Text, DateTime, ForeignKey, Index, Enum, func)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .database import Base

class Usuario(Base):
    __tablename__ = "usuario"

    usuario_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    usuario_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    usuario_mail: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    usuario_password: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relación 1..N con Materia
    materias: Mapped[List["Materia"]] = relationship(
        "Materia",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_usuario_mail", "usuario_mail"),
    )

    # Metodo representation, utilizable en depuracion (logs, debugging)
    def __repr__(self) -> str:
        return f"<Usuario id={self.usuario_id} mail={self.usuario_mail!r}>"


class Materia(Base):
    __tablename__ = "materia"

    materia_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    materia_usuario_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("usuario.usuario_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    materia_nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    materia_descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    usuario: Mapped["Usuario"] = relationship("Usuario", back_populates="materias")
    eventos: Mapped[List["Evento"]] = relationship(
        "Evento",
        back_populates="materia",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        Index("idx_materia_usuario", "materia_usuario_id"),
    )

    # Metodo representation, utilizable en depuracion (logs, debugging)
    def __repr__(self) -> str:
        return f"<Materia id={self.materia_id} nombre={self.materia_nombre!r}>"


EventoEstadoEnum = Enum(
    "pendiente",
    "hecho",
    "cancelado",
    name="evento_estado",          # tipo ENUM en PostgreSQL
)

class Evento(Base):
    __tablename__ = "evento"

    evento_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, index=True)
    evento_materia_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("materia.materia_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    evento_fecha_limite: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    evento_descripcion: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evento_estado: Mapped[str] = mapped_column(EventoEstadoEnum, nullable=False, server_default="pendiente")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relaciones
    materia: Mapped["Materia"] = relationship("Materia", back_populates="eventos")

    __table_args__ = (
        Index("idx_evento_materia", "evento_materia_id"),
        Index("idx_evento_fecha", "evento_fecha_limite"),
    )
    
    # Metodo representation, utilizable en depuracion (logs, debugging)
    def __repr__(self) -> str:
        return f"<Evento id={self.evento_id} estado={self.evento_estado} fecha={self.evento_fecha_limite}>"
