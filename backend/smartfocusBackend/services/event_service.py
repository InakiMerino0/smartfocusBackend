# services/event_service.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, delete as sa_delete

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


def get_user_events(
    db: Session, 
    usuario_id: int,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[models.Evento]:
    """
    Obtiene todos los eventos de todas las materias del usuario con búsqueda y paginación.
    """
    # Query que une eventos con materias para filtrar por usuario
    stmt = (
        select(models.Evento)
        .join(models.Materia, models.Evento.evento_materia_id == models.Materia.materia_id)
        .where(models.Materia.materia_usuario_id == usuario_id)
    )
    
    # Búsqueda por nombre del evento si se proporciona 'q'
    if q:
        try:
            # Postgres: ILIKE para búsqueda insensible a mayúsculas
            stmt = stmt.where(models.Evento.evento_nombre.ilike(f"%{q}%"))
        except AttributeError:
            # Fallback para dialectos sin ilike
            stmt = stmt.where(models.Evento.evento_nombre.like(f"%{q}%"))
    
    # Ordenar por fecha y aplicar paginación
    stmt = stmt.order_by(models.Evento.evento_fecha.asc()).offset(skip).limit(limit)
    
    return db.execute(stmt).scalars().all()


def delete_event(db: Session, usuario_id: int, evento_id: int) -> None:
    ev = _get_evento_autorizado(db, evento_id, usuario_id)
    db.delete(ev)
    db.commit()


def delete_events_by_materia(db: Session, usuario_id: int, materia_id: int) -> int:
    """
    Elimina todos los eventos de una materia (verifica ownership).
    Retorna la cantidad de eventos eliminados.
    """
    # Asegurar que la materia pertenece al usuario
    _assert_materia_propia(db, materia_id, usuario_id)

    # Borrar en bloque
    stmt = sa_delete(models.Evento).where(models.Evento.evento_materia_id == materia_id)
    res = db.execute(stmt)
    db.commit()

    # rowcount puede ser None dependiendo del driver; manejar ese caso
    try:
        deleted = int(res.rowcount) if getattr(res, 'rowcount', None) is not None else 0
    except Exception:
        deleted = 0

    return deleted
