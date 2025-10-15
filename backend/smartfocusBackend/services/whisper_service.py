import os
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException, UploadFile
from starlette.status import HTTP_400_BAD_REQUEST

from ..integrations.whisper_client import WhisperClient

MAX_AUDIO_MB = 3  # límite para chat


async def process_audio_with_nl(
    *,
    file: UploadFile,
    language: Optional[str] = "es",
    user_token: str,  # JWT token para autenticación con NL endpoint
) -> Dict[str, Any]:
    """
    Flujo completo:
    1. Valida archivo
    2. Transcribe con WhisperClient
    3. Consume ENDPOINT de v1_nl.py vía HTTP
    4. Devuelve resultado combinado
    """
    # Validar content-type
    content_type = file.content_type or "application/octet-stream"

    # Validar tamaño
    content_bytes = await file.read()
    size_mb = len(content_bytes) / (1024 * 1024)
    
    if size_mb > MAX_AUDIO_MB:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"El archivo supera el máximo permitido de {MAX_AUDIO_MB} MB"
        )
    
    # Resetear el archivo para WhisperClient
    file.file.seek(0)
    
    # 1. TRANSCRIBIR AUDIO
    client = WhisperClient()
    transcribed_text = await client.transcribe(file=file, language=language)
    
    if not transcribed_text:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail="No se pudo transcribir texto del audio proporcionado"
        )
    
    # 2. LLAMAR DIRECTAMENTE A NL (como lo haría el frontend, pero interno)
    from ..routers.v1_nl import nl_command, NLCommandRequest, get_llm_client
    from .. import auth, database
    from fastapi import Depends
    from sqlalchemy.orm import Session
    import contextlib

    # Decodificar usuario desde el token
    db = next(database.get_db())
    try:
        claims = auth.decodificar_token(user_token)
        usuario_id = int(claims.get("sub"))
        usuario = db.get(__import__("..models", fromlist=["Usuario"]).Usuario, usuario_id)
        if not usuario:
            raise HTTPException(status_code=401, detail="Usuario no encontrado para el token")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token inválido: {str(e)}")

    # Instanciar el cliente LLM
    llm = get_llm_client()

    # Construir el payload como lo haría el frontend
    payload = NLCommandRequest(text=transcribed_text, mode="execute")

    # Llamar a la función nl_command directamente
    try:
        result = nl_command.__wrapped__(
            payload=payload,
            db=db,
            usuario=usuario,
            llm=llm
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error ejecutando NL: {str(e)}")

    return {
        "transcribed_text": transcribed_text,
        "language": language,
        "summary": result.get("summary", "Procesado correctamente"),
        "results": result.get("results", [])
    }
