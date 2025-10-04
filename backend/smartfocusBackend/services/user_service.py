# services/user_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils import hash_clave


class UsuarioDuplicado(Exception):
    """Se intenta registrar un usuario con email existente."""
    


def _email_existe(db: Session, email: str) -> bool:
    stmt = select(models.Usuario).where(models.Usuario.usuario_email == email)
    return db.execute(stmt).scalar_one_or_none() is not None


def register_user(db: Session, payload: schemas.UsuarioCreate) -> schemas.UsuarioResponse:
    email_norm = payload.usuario_email.strip().lower()
    nombre_norm = payload.usuario_nombre.strip()

    # Unicidad por email (ajusta si también querés por nombre)
    if _email_existe(db, email_norm):
        raise UsuarioDuplicado()

    user = models.Usuario(
        usuario_nombre=nombre_norm,
        usuario_email=email_norm,               
        usuario_password=hash_clave(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Retornamos el schema usando el campo correcto 'usuario_created_at'.
    return schemas.UsuarioResponse(
        usuario_id=user.usuario_id,
        usuario_nombre=user.usuario_nombre,
        usuario_email=user.usuario_email,
        usuario_created_at=user.usuario_created_at,
    )
    