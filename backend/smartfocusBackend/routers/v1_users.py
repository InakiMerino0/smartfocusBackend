from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import schemas
from ..services import user_service as svc

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post(
    "/register",
    response_model=schemas.UsuarioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar un nuevo usuario",
    responses={
        201: {"description": "Usuario registrado"},
        409: {"description": "El email ya está registrado"},
    },
)
def register_endpoint(
    payload: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
):
    try:
        return svc.register_user(db, payload)
    except svc.UsuarioDuplicado:
        raise HTTPException(status_code=409, detail="El email ya está registrado")
