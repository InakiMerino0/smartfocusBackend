# services/user_service.py
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import models, schemas
from ..utils import hash_clave


class UsuarioDuplicado(Exception):
    """Se intenta registrar un usuario con email existente."""


def _email_existe(db: Session, email: str, exclude_user_id: int = None) -> bool:
    stmt = select(models.Usuario).where(models.Usuario.usuario_email == email)
    if exclude_user_id:
        stmt = stmt.where(models.Usuario.usuario_id != exclude_user_id)
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
        usuario_daltonismo=payload.usuario_daltonismo,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Retornamos el schema usando el campo correcto 'usuario_created_at'.
    return schemas.UsuarioResponse(
        usuario_id=user.usuario_id,
        usuario_nombre=user.usuario_nombre,
        usuario_email=user.usuario_email,
        usuario_daltonismo=user.usuario_daltonismo,
        usuario_created_at=user.usuario_created_at,
    )


def update_user_profile(db: Session, usuario_id: int, payload: schemas.UsuarioProfileUpdate) -> schemas.UsuarioResponse:
    """
    Actualiza el perfil del usuario (nombre y email solamente).
    Solo actualiza campos que realmente cambiaron.
    """
    # Buscar el usuario (ya autenticado, no debería fallar)
    user = db.get(models.Usuario, usuario_id)
    
    cambios_realizados = False
    
    # Verificar y actualizar email si es diferente
    if payload.usuario_email:
        email_norm = payload.usuario_email.strip().lower()
        if email_norm != user.usuario_email:
            # Validar que el nuevo email no esté en uso por otro usuario
            if _email_existe(db, email_norm, exclude_user_id=usuario_id):
                raise UsuarioDuplicado()
            user.usuario_email = email_norm
            cambios_realizados = True
    
    # Verificar y actualizar nombre si es diferente
    if payload.usuario_nombre:
        nombre_norm = payload.usuario_nombre.strip()
        if nombre_norm != user.usuario_nombre:
            user.usuario_nombre = nombre_norm
            cambios_realizados = True
    
    # Verificar y actualizar daltonismo si es diferente
    if payload.usuario_daltonismo:
        if payload.usuario_daltonismo != user.usuario_daltonismo:
            user.usuario_daltonismo = payload.usuario_daltonismo
            cambios_realizados = True
    
    # Solo hacer commit si hubo cambios
    if cambios_realizados:
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return schemas.UsuarioResponse(
        usuario_id=user.usuario_id,
        usuario_nombre=user.usuario_nombre,
        usuario_email=user.usuario_email,
        usuario_daltonismo=user.usuario_daltonismo,
        usuario_created_at=user.usuario_created_at,
    )
    