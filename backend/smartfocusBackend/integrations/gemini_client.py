# backend/smartfocusBackend/integrations/gemini_client.py
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional
import google.generativeai as genai


class GeminiClient:
    """
    Adaptador mínimo para Gemini con Function Calling.
    Expone: get_tool_calls(text, locale="es-AR") -> List[{name, args}]
    No contiene lógica de negocio (eso vive en nl_service).
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        if genai is None:
            raise RuntimeError(
                "Falta el paquete 'google-generativeai' en el entorno. "
                "Instálalo en producción para usar el endpoint NL."
            )

        api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY no configurada.")
            logging.info("GeminiClient: GEMINI_API_KEY no configurada en el entorno")

        model_name = "gemini-2.5-flash"
        
        genai.configure(api_key=api_key)

        tools = _tools_definitions()
        
        try:
            self.model = genai.GenerativeModel(
                model_name=model_name,
                tools=tools,
                system_instruction=(
                    "Eres un asistente especializado en gestión académica. Tu tarea es analizar las instrucciones "
                    "del usuario y usar las funciones que el usuario indique (tools) disponibles para realizar las acciones solicitadas. "
                    "\n\nFunciones disponibles:"
                    "\n- create_materia: crear nuevas materias (con descripción opcional)"
                    "\n- update_materia: modificar materias existentes"
                    "\n- delete_materia: eliminar materias"
                    "\n- create_evento: crear eventos (exámenes, parciales, etc.) con descripción opcional"
                    "\n- update_evento: modificar eventos existentes"
                    "\n- delete_evento: eliminar eventos"
                    "\n\nREGLAS IMPORTANTES:"
                    "\n1. SIEMPRE QUE SE ESPECIFIQUEN (no deben ser necesariamente especificadas textualmente iguales a como se encuentran en la base de datos) usa function calls para responder a las solicitudes del usuario"
                    "\n2. Si el usuario menciona una materia por nombre, usa 'materia_ref'"
                    "\n3. Las fechas deben estar en formato ISO 'YYYY-MM-DD'"
                    "\n4. Para eventos, usa estado 'pendiente' si no se especifica otro"
                    "\n5. Incluye descripciones cuando el usuario proporcione detalles adicionales sobre eventos o materias"
                    "\n6. Para modificar/eliminar eventos puedes usar:"
                    "\n   - 'evento_id' si se conoce el ID específico"
                    "\n   - 'evento_ref' con el nombre del evento"
                    "\n   - 'materia_ref' con el nombre de la materia (si tiene un solo evento)"
                    "\n   - Combinación de 'evento_ref' y 'materia_ref' para mayor precisión"
                    "\n7. NO respondas con texto normal, SOLO usa function calls"
                    "\n\nEjemplos:"
                    "\n- 'crear materia matemáticas' → usar create_materia"
                    "\n- 'agregar examen de física para mañana' → usar create_evento"
                    "\n- 'crear parcial de álgebra con calculadora permitida para el viernes' → usar create_evento con descripción"
                    "\n- 'cambiar el nombre de la materia historia' → usar update_materia"
                    "\n- 'borrar el parcial de química' → usar delete_evento con evento_ref='parcial' y materia_ref='química'"
                    "\n- 'eliminar el evento de matemáticas' → usar delete_evento con materia_ref='matemáticas'"
                    "\n- 'cambiar fecha del examen de física' → usar update_evento con evento_ref='examen' y materia_ref='física'"
                    ),
            )
            logging.info(f"GeminiClient: Modelo '{model_name}' configurado exitosamente")
        except Exception as e:
            logging.error(f"GeminiClient: Error configurando modelo '{model_name}': {str(e)}")
            raise RuntimeError(f"Error configurando modelo Gemini: {str(e)}")

    def get_tool_calls(self, text: str, *, locale: str = "es-AR") -> List[Dict[str, Any]]:
        """
        Ejecuta una inferencia y devuelve una lista de tool calls normalizados:
        [{ "name": "...", "args": {...} }, ...]
        """
        prompt = f"[locale={locale}] {text}".strip()
        try:
            resp = self.model.generate_content(prompt)
            
            tool_calls = _parse_tool_calls(resp)
            logging.info(f"GeminiClient: Recibidas {len(tool_calls)} tool calls")
            return tool_calls
        except Exception as e:
            logging.error(f"GeminiClient: Error al generar contenido con Gemini API: {str(e)}")
            return []


def _tools_definitions() -> List[Dict[str, Any]]:
    """
    Declaración de tools alineada al contrato que espera nl_service._normalize_tool_call.
    """
    return [{
        "function_declarations": [
            {
                "name": "create_materia",
                "description": "Crea una materia del usuario.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "materia_nombre": {"type": "string", "description": "Nombre de la materia"},
                        "materia_descripcion": {"type": "string", "description": "Descripción opcional"},
                    },
                    "required": ["materia_nombre"],
                },
            },
            {
                "name": "update_materia",
                "description": "Actualiza nombre y/o descripción de una materia existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "materia_id": {"type": "integer", "description": "ID de la materia (preferido)"},
                        "materia_ref": {"type": "string", "description": "Nombre actual si no hay ID"},
                        "materia_nombre": {"type": "string"},
                        "materia_descripcion": {"type": "string"},
                    },
                    "required": [],
                },
            },
            {
                "name": "delete_materia",
                "description": "Elimina una materia existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "materia_id": {"type": "integer"},
                        "materia_ref": {"type": "string"},
                    },
                    "required": [],
                },
            },
            {
                "name": "create_evento",
                "description": "Crea un evento asociado a una materia.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evento_materia_id": {"type": "integer", "description": "ID de la materia"},
                        "materia_ref": {"type": "string", "description": "Nombre de la materia si no hay ID"},
                        "evento_nombre": {"type": "string", "description": "Nombre del evento"},
                        "evento_descripcion": {"type": "string", "description": "Descripción opcional del evento"},
                        "evento_fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                        "evento_estado": {
                            "type": "string",
                            "enum": ["pendiente", "aprobado", "desaprobado"],
                            "description": "Estado del evento (por defecto: pendiente)",
                        },
                    },
                    "required": ["evento_nombre", "evento_fecha"],
                },
            },
            {
                "name": "update_evento",
                "description": "Actualiza atributos de un evento existente. Puede identificar el evento por ID, nombre del evento, o nombre de la materia (si tiene un solo evento).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evento_id": {"type": "integer", "description": "ID del evento (preferido si se conoce)"},
                        "evento_ref": {"type": "string", "description": "Nombre del evento a buscar"},
                        "materia_ref": {"type": "string", "description": "Nombre de la materia para buscar el evento"},
                        "evento_nombre": {"type": "string", "description": "Nuevo nombre del evento"},
                        "evento_descripcion": {"type": "string", "description": "Nueva descripción del evento"},
                        "evento_fecha": {"type": "string", "description": "Nueva fecha en formato YYYY-MM-DD"},
                        "evento_estado": {
                            "type": "string",
                            "enum": ["pendiente", "aprobado", "desaprobado"],
                            "description": "Nuevo estado del evento",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "delete_evento",
                "description": "Elimina un evento existente. Puede identificar el evento por ID, nombre del evento, o nombre de la materia (si tiene un solo evento).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evento_id": {"type": "integer", "description": "ID del evento (preferido si se conoce)"},
                        "evento_ref": {"type": "string", "description": "Nombre del evento a eliminar"},
                        "materia_ref": {"type": "string", "description": "Nombre de la materia para buscar el evento a eliminar"},
                    },
                    "required": [],
                },
            },
        ]
    }]


def _parse_tool_calls(resp) -> List[Dict[str, Any]]:
    """
    Extrae [{name, args}] desde la respuesta del SDK.
    Ignora candidatos sin function_call.
    """
    out: List[Dict[str, Any]] = []
    
    try:
        candidates = getattr(resp, "candidates", None) or []
        
        for i, cand in enumerate(candidates):
            content = getattr(cand, "content", None)
            if not content:
                continue
                
            parts = getattr(content, "parts", None) or []
            
            for j, p in enumerate(parts):
                fc = getattr(p, "function_call", None)
                
                if fc:
                    name = getattr(fc, "name", None)
                    if name:
                        args = dict(fc.args) if hasattr(fc.args, "items") else (fc.args or {})
                        out.append({"name": name, "args": args})
                        
    except Exception as e:
        logging.error(f"_parse_tool_calls: Error parseando respuesta: {str(e)}")
        return []
    
    return out
