from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth, schemas
from ..services import event_service as svc

router = APIRouter(prefix="/api/v1/events", tags=["events"])


@router.post(
    "",
    response_model=schemas.EventoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear evento para una materia propia",
)
def create_event_endpoint(
    payload: schemas.EventoCreate,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.create_event(db, usuario.usuario_id, payload)
    except svc.MateriaNoEncontrada:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a esta materia")


@router.get(
    "",
    response_model=List[schemas.EventoResponse],
    summary="Listar eventos de una materia propia (filtro por estado, paginado)",
)
def list_events_endpoint(
    materia_id: int = Query(..., ge=1, description="ID de la materia"),
    estado: Optional[schemas.EventoEstado] = Query(None, description="Filtrar por estado"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.list_events(db, usuario.usuario_id, materia_id, estado, skip, limit)
    except svc.MateriaNoEncontrada:
        raise HTTPException(status_code=404, detail="Materia no encontrada")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a esta materia")


@router.get(
    "/{evento_id}",
    response_model=schemas.EventoResponse,
    summary="Obtener un evento propio por ID",
)
def get_event_endpoint(
    evento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.get_event(db, usuario.usuario_id, evento_id)
    except svc.EventoNoEncontrado:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a este evento")


@router.put(
    "/{evento_id}",
    response_model=schemas.EventoResponse,
    summary="Actualizar un evento propio por ID",
)
def update_event_endpoint(
    evento_id: int,
    payload: schemas.EventoUpdate,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        return svc.update_event(db, usuario.usuario_id, evento_id, payload)
    except svc.EventoNoEncontrado:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a este evento")


@router.delete(
    "/{evento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un evento propio por ID",
)
def delete_event_endpoint(
    evento_id: int,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
):
    try:
        svc.delete_event(db, usuario.usuario_id, evento_id)
    except svc.EventoNoEncontrado:
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    except svc.AccesoNoAutorizado:
        raise HTTPException(status_code=403, detail="No autorizado para acceder a este evento")
    return
