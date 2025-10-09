# schemas.py
from __future__ import annotations

from datetime import datetime, date
from typing import Literal, Optional
from pydantic import BaseModel, EmailStr, Field
import enum


class TipoDaltonismo(str, enum.Enum):
    normal = "normal"
    protanopia = "protanopia"
    deuteranopia = "deuteranopia"
    tritanopia = "tritanopia"
    protanomalia = "protanomalia"
    deuteranomalia = "deuteranomalia"
    tritanomalia = "tritanomalia"


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
    Login usando únicamente el correo electrónico del usuario.
    """
    email: EmailStr = Field(..., description="Correo electrónico del usuario")
    password: str = Field(..., min_length=1, description="Contraseña en texto plano (se validará contra el hash)")
class ORMModel(BaseModel):
    class Config:
        orm_mode = True              # Pydantic v1
        from_attributes = True       # Pydantic v2


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
    password: str = Field(..., min_length=6, max_length=128, description="Contraseña en texto plano")
    usuario_daltonismo: TipoDaltonismo = Field(
        default=TipoDaltonismo.normal, 
        description="Tipo de daltonismo del usuario. Opciones: normal, protanopia, deuteranopia, tritanopia, protanomalia, deuteranomalia, tritanomalia",
        example="normal"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "usuario_nombre": "Juan Pérez",
                "usuario_email": "juan@example.com",
                "password": "mipassword123",
                "usuario_daltonismo": "normal"
            }
        }

class UsuarioProfileUpdate(BaseModel):
    """
    Schema para actualizar solo el perfil del usuario (nombre, email y daltonismo).
    No incluye contraseña para mayor seguridad.
    """
    usuario_nombre: Optional[str] = Field(None, min_length=1, max_length=100, description="Nuevo nombre del usuario")
    usuario_email: Optional[EmailStr] = Field(None, description="Nuevo email del usuario")
    usuario_daltonismo: Optional[TipoDaltonismo] = Field(None, description="Nuevo tipo de daltonismo del usuario")

class UsuarioResponse(ORMModel):
    usuario_id: int
    usuario_nombre: str
    usuario_email: EmailStr
    usuario_daltonismo: TipoDaltonismo = Field(default=TipoDaltonismo.normal, description="Tipo de daltonismo del usuario", example="normal")
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
    evento_descripcion: Optional[str] = Field(None, max_length=255, description="Descripción opcional del evento")
    evento_fecha: date
    evento_estado: EventoEstado = "pendiente"

class EventoCreate(EventoBase):
    evento_materia_id: int = Field(..., ge=1)

class EventoUpdate(BaseModel):
    evento_nombre: Optional[str] = Field(None, min_length=1, max_length=150)
    evento_descripcion: Optional[str] = Field(None, max_length=255, description="Descripción opcional del evento")
    evento_fecha: Optional[date] = None
    evento_estado: Optional[EventoEstado] = None

class EventoResponse(ORMModel):
    evento_id: int
    evento_materia_id: int
    evento_nombre: str
    evento_descripcion: Optional[str] = None
    evento_fecha: date
    evento_estado: EventoEstado
    evento_created_at: datetime
