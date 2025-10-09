from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, auth
from ..database import get_db  # ajusta si tu módulo se llama distinto
from ..services import user_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post(
    "/login",
    response_model=schemas.TokenResponse,
    summary="Iniciar sesión",
    status_code=status.HTTP_200_OK,
)
def login_endpoint(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    try:
        return auth.login_user(payload, db)
    except auth.InvalidCredentialsError:
        # mensaje genérico para no filtrar si el usuario existe
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    except Exception as e:
        # evita filtrar detalles internos
        raise HTTPException(status_code=500, detail="Error de autenticación")


@router.get(
    "/me",
    response_model=schemas.UsuarioResponse,
    summary="Ver perfil del usuario autenticado",
)
def me_endpoint(usuario=Depends(auth.get_current_user)):
    """
    Devuelve el usuario actual a partir del access token (Bearer).
    """
    return usuario


@router.put(
    "/profile",
    response_model=schemas.UsuarioResponse,
    summary="Actualizar perfil del usuario autenticado",
    description="Permite actualizar el nombre y email del usuario. Solo actualiza campos que realmente cambiaron."
)
def update_profile_endpoint(
    payload: schemas.UsuarioProfileUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user)
):
    """
    Actualiza el perfil del usuario autenticado (nombre y email).
    Solo procesa cambios reales para optimizar el rendimiento.
    """
    try:
        return user_service.update_user_profile(db, usuario.usuario_id, payload)
    except user_service.UsuarioDuplicado:
        raise HTTPException(status_code=400, detail="El email ya está en uso por otro usuario")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error actualizando perfil: {str(e)}")
