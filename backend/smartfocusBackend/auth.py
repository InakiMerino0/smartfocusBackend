# auth.py
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import select
from jose import jwt, JWTError

from . import models, utils, database, schemas

class InvalidCredentialsError(Exception):
    """Excepción para credenciales inválidas"""
    pass

# =========================
# Config (desde entorno)
# =========================
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_ACCESS")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

_http_bearer = HTTPBearer(auto_error=False)

# =========================
# Helpers JWT
# =========================
def _now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)

def crear_token(subject: str, minutos_expira: int = ACCESS_TOKEN_EXPIRE_MINUTES, extra: Dict[str, Any] | None = None) -> str:
    now = _now_utc()
    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=minutos_expira)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decodificar_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

# =========================
# Core de autenticación
# =========================
def _buscar_usuario_por_identificador(db: Session, identificador: str) -> Optional[models.Usuario]:
    # Buscar por email o por nombre
    stmt = select(models.Usuario).where(
        (models.Usuario.usuario_email == identificador) | 
        (models.Usuario.usuario_nombre == identificador)
    )
    return db.execute(stmt).scalar_one_or_none()

def _buscar_usuario_por_id(db: Session, usuario_id: int) -> Optional[models.Usuario]:
    return db.get(models.Usuario, usuario_id)

def login_user(request: schemas.LoginRequest, db: Session):
    usuario = _buscar_usuario_por_identificador(db, request.identifier)
    if not usuario or not utils.verificar_clave(request.password, usuario.usuario_password):
        # Mensaje genérico para no filtrar existencia
        raise InvalidCredentialsError("Credenciales inválidas")

    # sub = id (recomendado); puedes agregar claims no sensibles si querés
    token = crear_token(subject=str(usuario.usuario_id), extra={
        "username": usuario.usuario_nombre
    })

    # Respuesta consistente con tu schema TokenResponse
    return {
        "access_token": token,
        "token_type": "Bearer",
    }

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(_http_bearer),
    db: Session = Depends(database.get_db),
):
    """
    Lee Authorization: Bearer <token>, valida y retorna el usuario.
    """
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")

    token = creds.credentials
    try:
        claims = decodificar_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")

    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido (sin sub)")

    usuario = _buscar_usuario_por_id(db, int(sub))
    if not usuario:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")

    # (Opcional) si tienes un flag de activo:
    # if not usuario.activo: raise HTTPException(status_code=403, detail="Usuario inactivo")

    return usuario
