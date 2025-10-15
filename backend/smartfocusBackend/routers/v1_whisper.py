from typing import Optional, Any, Dict
import logging

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from pydantic import BaseModel

from .. import auth

router = APIRouter(prefix="/api/v1/whisper", tags=["whisper"])


class AudioToNLResponse(BaseModel):
    """Respuesta completa: transcripción + ejecución de acciones NL"""
    transcribed_text: str
    language: str = "es"
    summary: str
    results: list[Dict[str, Any]]


@router.post(
    "/process",
    response_model=AudioToNLResponse,
    summary="Procesar audio con Whisper",
    description="Transcribe audio con Whisper y ejecuta acciones NL automáticamente"
)
async def process_audio_endpoint(
    file: UploadFile = File(..., description="Audio a procesar (mp3/wav/m4a/webm/ogg - máx 3MB)"),
    language: Optional[str] = Form("es", description="Idioma del audio"),
    current_user=Depends(auth.get_current_user),
):
    """
    Endpoint que SOLO recibe y valida el archivo de audio.
    Delega toda la lógica al whisper_service.
    """
    from ..services.whisper_service import process_audio_with_nl
    
    try:
        # Solo validar que hay archivo y delegar al service
        if not file:
            raise HTTPException(status_code=400, detail="Archivo de audio requerido")
        
        # Obtener token JWT de la sesión actual
        token = auth.crear_token(str(current_user.usuario_id))
        
        result = await process_audio_with_nl(
            file=file,
            language=language,
            user_token=token
        )
        
        return AudioToNLResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"process_audio: Error procesando audio: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno al procesar el audio: {str(e)}"
        )
