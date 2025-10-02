from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import schemas, auth
from ..database import get_db  # ajusta si tu módulo se llama distinto

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
