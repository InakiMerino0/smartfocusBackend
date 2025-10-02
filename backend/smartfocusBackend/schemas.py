# schemas.py
from __future__ import annotations

from datetime import datetime, date
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field


# -------------------------------------------------------------------
# Compatibilidad ORM (FastAPI + SQLAlchemy)
# -------------------------------------------------------------------
class ORMModel(BaseModel):
    class Config:
        orm_mode = True              # Pydantic v1
        from_attributes = True       # Pydantic v2


# =========================
# AUTH
# =========================
class LoginRequest(BaseModel):
    """
    Identificador flexible: puede ser el correo (usuario_email) o el nombre de usuario (usuario_nombre).
    """
    identifier: str = Field(..., min_length=1, description="usuario_email o usuario_nombre")
    password: str = Field(..., min_length=1, description="Contraseña en texto plano (se validará contra el hash)")


class TokenResponse(BaseModel):
    token_type: str = "Bearer"
    access_token: str
    # Si más adelante usas refresh tokens, puedes añadir: refresh_token: Optional[str] = None


# =========================
# USUARIO
# Tabla: usuario
# =========================
class UsuarioBase(BaseModel):
    usuario_nombre: str = Field(..., min_length=1, max_length=100)
    usuario_email: EmailStr

class UsuarioCreate(UsuarioBase):
    """
    Para registro/seed. Recibe contraseña en claro; el backend la hashea a usuario_password.
    """
    password: str = Field(..., min_length=6, max_length=128, description="Contraseña en texto plano")

class UsuarioUpdate(BaseModel):
    usuario_nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    usuario_email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=6, max_length=128)

class UsuarioResponse(ORMModel):
    usuario_id: int
    usuario_nombre: str
    usuario_email: EmailStr
    usuario_created_at: datetime


# =========================
# MATERIA
# Tabla: materia
# =========================
class MateriaBase(BaseModel):
    materia_nombre: str = Field(..., min_length=1, max_length=100)
    materia_descripcion: Optional[str] = None

class MateriaCreate(MateriaBase):
    materia_usuario_id: int = Field(..., ge=1)

class MateriaUpdate(BaseModel):
    materia_nombre: Optional[str] = Field(None, min_length=1, max_length=100)
    materia_descripcion: Optional[str] = None

class MateriaResponse(ORMModel):
    materia_id: int
    materia_usuario_id: int
    materia_nombre: str
    materia_descripcion: Optional[str] = None
    materia_created_at: datetime


# =========================
# EVENTO
# Tabla: evento
# =========================
EventoEstado = Literal["pendiente", "aprobado", "desaprobado"]

class EventoBase(BaseModel):
    evento_nombre: str = Field(..., min_length=1, max_length=150)
    evento_fecha: date
    evento_estado: EventoEstado = "pendiente"

class EventoCreate(EventoBase):
    evento_materia_id: int = Field(..., ge=1)

class EventoUpdate(BaseModel):
    evento_nombre: Optional[str] = Field(None, min_length=1, max_length=150)
    evento_fecha: Optional[date] = None
    evento_estado: Optional[EventoEstado] = None

class EventoResponse(ORMModel):
    evento_id: int
    evento_materia_id: int
    evento_nombre: str
    evento_fecha: date
    evento_estado: EventoEstado
    evento_created_at: datetime
