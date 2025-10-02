# routers/v1_subjects.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, schemas
from ..services import subject_service as svc

router = APIRouter(prefix="/api/v1/subjects", tags=["subjects"])


@router.post(
    "",
    response_model=schemas.MateriaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear una materia propia",
    responses={
        201: {"description": "Materia creada"},
        403: {"description": "No autorizado"},
        409: {"description": "Materia duplicada"},
    },
)
def create_subject_endpoint(
    payload: schemas.MateriaCreate,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        # Forzamos ownership: ignoramos materia_usuario_id del payload y usamos el del usuario autenticado
        payload_fixed = payload.copy(update={"materia_usuario_id": usuario.usuario_id})
        return svc.create_subject(db, usuario.usuario_id, payload_fixed)
    except svc.MateriaDuplicada:
        raise HTTPException(status_code=409, detail="Ya existe una materia con ese nombre")
    # AccesoNoAutorizado no debería ocurrir acá porque imponemos usuario_id actual


@router.get(
    "",
    response_model=List[schemas.MateriaResponse],
    summary="Listar materias propias (búsqueda/paginado)",
)
def list_subjects_endpoint(
    q: Optional[str] = Query(None, description="Buscar por nombre"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    return svc.list_subjects(db, usuario.usuario_id, q, skip, limit)


@router.get(
    "/{materia_id}",
    response_model=schemas.MateriaResponse,
    summary="Obtener una materia propia por ID",
)
def get_subject_endpoint(
    materia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.get_subject(db, usuario.usuario_id, materia_id)
    except svc.MateriaNoEncontrada:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a esta materia")


@router.put(
    "/{materia_id}",
    response_model=schemas.MateriaResponse,
    summary="Actualizar una materia propia por ID",
    responses={
        200: {"description": "Materia actualizada"},
        403: {"description": "No autorizado"},
        404: {"description": "Materia no encontrada"},
        409: {"description": "Materia duplicada"},
    },
)
def update_subject_endpoint(
    materia_id: int,
    payload: schemas.MateriaUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.update_subject(db, usuario.usuario_id, materia_id, payload)
    except svc.MateriaNoEncontrada:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a esta materia")
    except svc.MateriaDuplicada:
        raise HTTPException(status_code=409, detail="Ya existe una materia con ese nombre")


@router.delete(
    "/{materia_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar una materia propia por ID",
)
def delete_subject_endpoint(
    materia_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        svc.delete_subject(db, usuario.usuario_id, materia_id)
    except svc.MateriaNoEncontrada:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a esta materia")
    return
