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
    
    # 2. CONSUMIR ENDPOINT DE NL (como si fuera el frontend)
    nl_result = await _call_nl_endpoint(transcribed_text, user_token)
    
    # 3. COMBINAR RESULTADOS
    return {
        "transcribed_text": transcribed_text,
        "language": language,
        "summary": nl_result.get("summary", "Procesado correctamente"),
        "results": nl_result.get("results", [])
    }

# Peticion al endpoint NL
async def _call_nl_endpoint(text: str, user_token: str) -> Dict[str, Any]:

    base_url = "http://18.116.90.219/"
    
    # Payload JSON como lo haría el frontend
    payload = {
        "text": text,
        "mode": "execute"
    }
    
    # Headers con autenticación
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/api/v1/nl/command",
                json=payload,
                headers=headers,
                timeout=30.0
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                # Si falla NL, devolver error pero texto transcrito OK
                return {
                    "summary": f"{response.status_code}. Texto transcrito correctamente.",
                    "results": [],
                    "nl_error": response.text
                }
                
    except httpx.RequestError as e:
        return {
            "summary": f"Error conectando con servicio NL: {str(e)}. Texto transcrito correctamente.",
            "results": [],
            "nl_error": str(e)
        }
    except Exception as e:
        return {
            "summary": f"Error inesperado con NL: {str(e)}. Texto transcrito correctamente.",
            "results": [],
            "nl_error": str(e)
        }
