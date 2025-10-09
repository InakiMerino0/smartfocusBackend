# services/event_service.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import models, schemas


# Excepciones de dominio (el router las mapea a HTTP)
class MateriaNoEncontrada(Exception): ...
class EventoNoEncontrado(Exception): ...
class AccesoNoAutorizado(Exception): ...


def _assert_materia_propia(db: Session, materia_id: int, usuario_id: int) -> models.Materia:
    materia = db.get(models.Materia, materia_id)
    if not materia:
        raise MateriaNoEncontrada()
    if materia.materia_usuario_id != usuario_id:
        raise AccesoNoAutorizado()
    return materia


def _get_evento_autorizado(db: Session, evento_id: int, usuario_id: int) -> models.Evento:
    ev = db.get(models.Evento, evento_id)
    if not ev:
        raise EventoNoEncontrado()
    mat = db.get(models.Materia, ev.evento_materia_id)
    if not mat or mat.materia_usuario_id != usuario_id:
        raise AccesoNoAutorizado()
    return ev


def create_event(db: Session, usuario_id: int, payload: schemas.EventoCreate) -> models.Evento:
    _assert_materia_propia(db, payload.evento_materia_id, usuario_id)

    ev = models.Evento(
        evento_materia_id=payload.evento_materia_id,
        evento_nombre=payload.evento_nombre,
        evento_descripcion=payload.evento_descripcion,
        evento_fecha=payload.evento_fecha,
        evento_estado=payload.evento_estado,
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def list_events(
    db: Session,
    usuario_id: int,
    materia_id: int,
    estado: Optional[schemas.EventoEstado] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[models.Evento]:
    _assert_materia_propia(db, materia_id, usuario_id)

    stmt = select(models.Evento).where(models.Evento.evento_materia_id == materia_id)
    if estado:
        stmt = stmt.where(models.Evento.evento_estado == estado)
    stmt = stmt.order_by(models.Evento.evento_fecha.asc()).offset(skip).limit(limit)

    return db.execute(stmt).scalars().all()


def get_event(db: Session, usuario_id: int, evento_id: int) -> models.Evento:
    return _get_evento_autorizado(db, evento_id, usuario_id)


def update_event(
    db: Session,
    usuario_id: int,
    evento_id: int,
    payload: schemas.EventoUpdate,
) -> models.Evento:
    ev = _get_evento_autorizado(db, evento_id, usuario_id)

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(ev, k, v)

    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


def get_user_events(db: Session, usuario_id: int) -> List[models.Evento]:
    """
    Obtiene todos los eventos de todas las materias del usuario.
    """
    # Query que une eventos con materias para filtrar por usuario
    stmt = (
        select(models.Evento)
        .join(models.Materia, models.Evento.evento_materia_id == models.Materia.materia_id)
        .where(models.Materia.materia_usuario_id == usuario_id)
        .order_by(models.Evento.evento_fecha.asc())
    )
    
    return db.execute(stmt).scalars().all()


def delete_event(db: Session, usuario_id: int, evento_id: int) -> None:
    ev = _get_evento_autorizado(db, evento_id, usuario_id)
    db.delete(ev)
    db.commit()
