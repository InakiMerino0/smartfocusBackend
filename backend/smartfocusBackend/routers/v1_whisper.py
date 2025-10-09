from typing import Optional, Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import JSONResponse

from .. import auth
from ..services.whisper_service import transcribe_audio

router = APIRouter(prefix="/api/v1/whisper", tags=["whisper"])

ResponseFormat = Literal["json", "verbose_json", "text", "srt", "vtt"]


@router.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(..., description="Audio a transcribir (m4a/mp3/wav/webm/ogg)"),
    language: Optional[str] = Form(None, description="Idioma forzado, ej. 'es'"),
    responseFormat: ResponseFormat = Form("json", description="Formato de respuesta: json|verbose_json|text|srt|vtt"),
    model: str = Form("whisper-1", description="Modelo de transcripción"),
    current_user=Depends(auth.get_current_user),
):
    """
    Recibe audio por multipart/form-data y devuelve la transcripción normalizada.
    """
    result = await transcribe_audio(
        file=file,
        language=language,
        response_format=responseFormat,
        model=model,
    )
    return JSONResponse(result)
