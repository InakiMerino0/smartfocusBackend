import mimetypes
from typing import Any, Dict, Optional, Tuple, Literal

from fastapi import HTTPException, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST, HTTP_502_BAD_GATEWAY

from ..integrations.whisper_client import WhisperClient, WhisperAPIError

# Políticas básicas
ALLOWED_MIME = {
    "audio/mpeg",     # .mp3
    "audio/mp3",
    "audio/mp4",      # .mp4 (a veces contenedor audio)
    "audio/m4a",      # .m4a
    "audio/x-m4a",
    "audio/wav",      # .wav
    "audio/webm",     # .webm
    "audio/ogg",      # .ogg
}
MAX_AUDIO_MB = 25  # límite razonable para STT remoto

ResponseFormat = Literal["json", "verbose_json", "text", "srt", "vtt"]


def _guess_content_type(filename: str, fallback: str = "application/octet-stream") -> str:
    ctype, _ = mimetypes.guess_type(filename)
    return ctype or fallback


async def transcribe_audio(
    *,
    file: UploadFile,
    language: Optional[str] = None,
    response_format: ResponseFormat = "json",
    model: str = "whisper-1",
) -> Dict[str, Any]:
    """
    Orquesta:
    - valida archivo (MIME/tamaño)
    - llama a integrations/WhisperClient
    - normaliza respuesta a shape estable
    """
    # Validar content-type (mejor usar el enviado por el cliente si es fiable; sino, inferir)
    filename = file.filename or "audio"
    content_type = file.content_type or _guess_content_type(filename)

    if content_type not in ALLOWED_MIME:
        # Permitimos wav aunque algunos mimetypes lo devuelven como "audio/x-wav"
        if not (content_type in ("audio/x-wav",) and "audio/wav" in ALLOWED_MIME):
            raise HTTPException(
                status_code=HTTP_400_BAD_REQUEST,
                detail=f"Tipo de archivo no permitido: {content_type}",
            )

    # Cargar en memoria y validar tamaño
    content_bytes = await file.read()
    size_mb = len(content_bytes) / (1024 * 1024)
    if size_mb > MAX_AUDIO_MB:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"El archivo supera el máximo permitido de {MAX_AUDIO_MB} MB",
        )

    client = WhisperClient()
    try:
        payload, request_id = await client.transcribe(
            file_tuple=(filename, content_bytes, content_type),
            model=model,
            language=language,
            response_format=response_format,
        )
    except WhisperAPIError as e:
        # Aquí podrías mapear a tu "error envelope" si ya lo tenés
        raise HTTPException(
            status_code=HTTP_502_BAD_GATEWAY,
            detail={"message": "Falla al transcribir audio", "upstream_status": e.status_code, "upstream": e.details},
        )
    finally:
        await client.close()

    # Normalizar shape de respuesta
    result: Dict[str, Any] = {
        "model": model,
        "request_id": request_id,
    }

    if isinstance(payload, dict):  # json / verbose_json
        # Campos comunes esperables
        result["text"] = payload.get("text", "")
        if "language" in payload:
            result["language"] = payload["language"]
        if "duration" in payload:
            result["duration_sec"] = payload["duration"]
        if "segments" in payload:
            # Mantener la estructura tal cual la retorna Whisper (start, end, text, etc.)
            result["segments"] = payload["segments"]
    else:
        # text / srt / vtt → devolvemos en el campo 'raw'
        # y dejamos 'text' vacío para no inducir a error
        result["text"] = ""
        result["raw"] = payload
        result["format"] = response_format

    return result
