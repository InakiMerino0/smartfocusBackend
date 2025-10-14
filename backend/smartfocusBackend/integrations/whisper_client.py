import os
import tempfile

from openai import AsyncOpenAI
from fastapi import UploadFile


class WhisperClient:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY no está configurada en el entorno.")
        
        self.client = AsyncOpenAI(api_key=self.api_key)

    # Conexion y transcripcion
    async def transcribe(self, file: UploadFile, language: str = "es") -> str:

        # Leer contenido del archivo
        content = await file.read()
        
        # Obtener extensión del archivo
        file_extension = "m4a"  # default
        
        # Crear archivo temporal para OpenAI SDK
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        try:
            # Transcribir usando OpenAI SDK (como en la documentación)
            with open(temp_file_path, "rb") as audio_file:
                transcription = await self.client.audio.transcriptions.create(
                    model="whisper-1", 
                    file=audio_file, 
                    response_format="text",
                    language=language,
                    prompt="Transcribe el audio de forma fiel y clara en el mismo idioma del hablante (español por defecto), con puntuación y mayúsculas correctas, sin resumir ni interpretar ni añadir comentarios; conserva tal cual los nombres propios, tecnicismos y referencias académicas (materias, eventos, parciales, exámenes) y, cuando el usuario dicte instrucciones operativas para crear, actualizar o eliminar recursos, asegúrate de que queden explícitos el verbo de acción, el recurso afectado y sus parámetros (nombre, fecha, hora, estado, identificadores), manteniendo números y fechas tal como se pronuncian o normalizándolos a AAAA-MM-DD y HH:MM solo si son inequívocos; no traduzcas ni corrijas el sentido; entrega únicamente el texto transcrito final, ya que será consumido por otro servicio para ejecutar las acciones indicadas."
                )
            
            # Devuelve directamente el texto transcrito
            return transcription.strip()
            
        finally:
            # Limpiar archivo temporal
            os.unlink(temp_file_path)
