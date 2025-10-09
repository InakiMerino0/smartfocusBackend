import os
import uuid
from typing import Any, Dict, Optional, Tuple

import httpx


class WhisperAPIError(Exception):
    def __init__(self, status_code: int, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


class WhisperClient:
    """
    Cliente mínimo para OpenAI Whisper /v1/audio/transcriptions
    - Usa httpx.AsyncClient
    - Envía multipart con el audio y parámetros (model, language, response_format)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        timeout_seconds: float = 60.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY no está configurada en el entorno.")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=httpx.Timeout(self.timeout_seconds),
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def transcribe(
        self,
        *,
        file_tuple: Tuple[str, bytes, str],  # (filename, content_bytes, content_type)
        model: str = "whisper-1",
        language: Optional[str] = None,
        response_format: str = "json",  # "json" | "verbose_json" | "text" | "srt" | "vtt"
    ) -> Tuple[Dict[str, Any] | str, str]:
        """
        Envía el audio a OpenAI y devuelve (payload, request_id)
        - payload: dict (json/verbose_json) o str (text/srt/vtt)
        - request_id: UUID interno de tracking en nuestro backend
        """
        filename, content, content_type = file_tuple
        request_id = str(uuid.uuid4())

        # Construimos multipart form
        # Nota: httpx arma el boundary automáticamente
        files = {
            "file": (filename, content, content_type),
        }
        data = {
            "model": model,
            "response_format": response_format,
        }
        if language:
            data["language"] = language

        try:
            resp = await self._client.post("/audio/transcriptions", files=files, data=data)
        except httpx.RequestError as e:
            raise WhisperAPIError(503, "No se pudo contactar con el servicio de transcripción", {"error": str(e)})

        # Manejo de errores HTTP
        if resp.status_code >= 400:
            # Intentar parsear JSON de error; si no, texto
            try:
                err = resp.json()
            except Exception:
                err = {"error": resp.text}
            raise WhisperAPIError(resp.status_code, "Error en Whisper API", err)

        # Formatos: json/verbose_json devuelven JSON; text/srt/vtt devuelven texto
        content_type_header = resp.headers.get("content-type", "")
        if "application/json" in content_type_header:
            return resp.json(), request_id
        else:
            return resp.text, request_id
