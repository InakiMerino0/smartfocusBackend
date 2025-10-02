# services/subject_service.py
from __future__ import annotations

from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import models, schemas

# Excepciones de dominio (el router las traduce a HTTP)
class MateriaNoEncontrada(Exception): ...
class AccesoNoAutorizado(Exception): ...
class MateriaDuplicada(Exception): ...


def _get_materia_autorizada(db: Session, materia_id: int, usuario_id: int) -> models.Materia:
    materia = db.get(models.Materia, materia_id)
    if not materia:
        raise MateriaNoEncontrada()
    if materia.materia_usuario_id != usuario_id:
        raise AccesoNoAutorizado()
    return materia


def create_subject(db: Session, usuario_id: int, payload: schemas.MateriaCreate) -> models.Materia:
    # Forzamos que la materia quede asignada al usuario autenticado (ignora lo que venga del cliente)
    nombre = payload.materia_nombre.strip()

    # (Opcional) evitar duplicados por nombre para ese usuario
    dup_stmt = select(models.Materia).where(
        models.Materia.materia_usuario_id == usuario_id,
        models.Materia.materia_nombre == nombre,
    )
    if db.execute(dup_stmt).scalar_one_or_none():
        raise MateriaDuplicada()

    materia = models.Materia(
        materia_usuario_id=usuario_id,
        materia_nombre=nombre,
        materia_descripcion=payload.materia_descripcion,
    )
    db.add(materia)
    db.commit()
    db.refresh(materia)
    return materia


def list_subjects(
    db: Session,
    usuario_id: int,
    q: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[models.Materia]:
    stmt = select(models.Materia).where(models.Materia.materia_usuario_id == usuario_id)
    if q:
        # Búsqueda simple por nombre (case-insensitive si el collation/DB lo permite;
        # en Postgres usar ilike; si usás MySQL y querés insensible, depende del collation)
        try:
            # Postgres: ILIKE
            stmt = stmt.where(models.Materia.materia_nombre.ilike(f"%{q}%"))
        except AttributeError:
            # Fallback (dialect sin ilike): igualamos a like
            stmt = stmt.where(models.Materia.materia_nombre.like(f"%{q}%"))

    stmt = stmt.order_by(models.Materia.materia_nombre.asc()).offset(skip).limit(limit)
    return db.execute(stmt).scalars().all()


def get_subject(db: Session, usuario_id: int, materia_id: int) -> models.Materia:
    return _get_materia_autorizada(db, materia_id, usuario_id)


def update_subject(
    db: Session,
    usuario_id: int,
    materia_id: int,
    payload: schemas.MateriaUpdate,
) -> models.Materia:
    materia = _get_materia_autorizada(db, materia_id, usuario_id)

    data = payload.model_dump(exclude_unset=True)
    if "materia_nombre" in data and data["materia_nombre"]:
        nuevo_nombre = data["materia_nombre"].strip()

        # (Opcional) evitar duplicados al renombrar
        dup_stmt = select(models.Materia).where(
            models.Materia.materia_usuario_id == usuario_id,
            models.Materia.materia_nombre == nuevo_nombre,
            models.Materia.materia_id != materia_id,
        )
        if db.execute(dup_stmt).scalar_one_or_none():
            raise MateriaDuplicada()

        materia.materia_nombre = nuevo_nombre

    if "materia_descripcion" in data:
        materia.materia_descripcion = data["materia_descripcion"]

    db.add(materia)
    db.commit()
    db.refresh(materia)
    return materia


def delete_subject(db: Session, usuario_id: int, materia_id: int) -> None:
    materia = _get_materia_autorizada(db, materia_id, usuario_id)
    db.delete(materia)
    db.commit()
