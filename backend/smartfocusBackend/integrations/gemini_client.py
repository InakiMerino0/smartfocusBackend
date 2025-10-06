# backend/smartfocusBackend/integrations/gemini_client.py
from __future__ import annotations

import os
import logging
from typing import Any, Dict, List, Optional

# Hacemos el import "suave" para no romper en dev si la lib no está instalada
try:
    import google.generativeai as genai
except Exception:  # pragma: no cover
    genai = None


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

        # Configurar el nombre del modelo con validación
        model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-1.5-pro-latest")
        if not model_name or model_name == "":
            model_name = "gemini-1.5-pro-latest"
        
        # Validar que el modelo tenga un formato correcto
        valid_models = [
            "gemini-1.5-pro-latest",
            "gemini-1.5-pro",
            "gemini-1.5-flash-latest", 
            "gemini-1.5-flash",
            "gemini-pro"
        ]
        
        if model_name not in valid_models:
            logging.warning(f"GeminiClient: Modelo '{model_name}' no está en la lista de modelos válidos. Usando gemini-1.5-pro-latest por defecto.")
            model_name = "gemini-1.5-pro-latest"
        
        logging.info(f"GeminiClient: Configurando con modelo '{model_name}'")
        
        genai.configure(api_key=api_key)
        logging.info(f"GeminiClient: API configurada exitosamente")

        tools = _tools_definitions()
        logging.info(f"GeminiClient: Configurando {len(tools[0]['function_declarations'])} herramientas")
        
        try:
            self.model = genai.GenerativeModel(
                model_name=model_name,
                tools=tools,
                system_instruction=(
                    "Eres un asistente especializado en gestión académica. Tu tarea es analizar las instrucciones "
                    "del usuario y SIEMPRE usar las funciones (tools) disponibles para realizar las acciones solicitadas. "
                    "\n\nFunciones disponibles:"
                    "\n- create_materia: crear nuevas materias"
                    "\n- update_materia: modificar materias existentes"
                    "\n- delete_materia: eliminar materias"
                    "\n- create_evento: crear eventos (exámenes, parciales, etc.)"
                    "\n- update_evento: modificar eventos existentes"
                    "\n- delete_evento: eliminar eventos"
                    "\n\nREGLAS IMPORTANTES:"
                    "\n1. SIEMPRE usa function calls para responder a las solicitudes del usuario"
                    "\n2. Si el usuario menciona una materia por nombre (sin ID), usa 'materia_ref'"
                    "\n3. Las fechas deben estar en formato ISO 'YYYY-MM-DD'"
                    "\n4. Para eventos, usa estado 'pendiente' si no se especifica otro"
                    "\n5. NO respondas con texto normal, SOLO usa function calls"
                    "\n\nEjemplos:"
                    "\n- 'crear materia matemáticas' → usar create_materia"
                    "\n- 'agregar examen de física para mañana' → usar create_evento"
                    "\n- 'cambiar el nombre de la materia historia' → usar update_materia"
                ),
            )
            logging.info(f"GeminiClient: Modelo '{model_name}' configurado exitosamente con {len(tools[0]['function_declarations'])} herramientas")
        except Exception as e:
            logging.error(f"GeminiClient: Error configurando modelo '{model_name}': {str(e)}")
            raise RuntimeError(f"Error configurando modelo Gemini: {str(e)}")

    def get_tool_calls(self, text: str, *, locale: str = "es-AR") -> List[Dict[str, Any]]:
        """
        Ejecuta una inferencia y devuelve una lista de tool calls normalizados:
        [{ "name": "...", "args": {...} }, ...]
        """
        prompt = f"[locale={locale}] {text}".strip()
        logging.info(f"GeminiClient: Enviando prompt a Gemini API: {text[:100]}...")
        try:
            resp = self.model.generate_content(prompt)
            logging.info(f"GeminiClient: Respuesta recibida de Gemini API")
            
            # Debug: mostrar la respuesta completa
            if hasattr(resp, 'candidates') and resp.candidates:
                for i, candidate in enumerate(resp.candidates):
                    logging.info(f"GeminiClient: Candidato {i}: {candidate}")
                    if hasattr(candidate, 'content') and candidate.content:
                        if hasattr(candidate.content, 'parts'):
                            for j, part in enumerate(candidate.content.parts):
                                logging.info(f"GeminiClient: Parte {j}: {part}")
            
            tool_calls = _parse_tool_calls(resp)
            logging.info(f"GeminiClient: Recibidas {len(tool_calls)} tool calls de Gemini API")
            return tool_calls
        except Exception as e:
            logging.error(f"GeminiClient: Error al generar contenido con Gemini API: {str(e)}")
            return []

    def debug_prompt(self, text: str) -> str:
        """
        Método de debug para ver exactamente qué está respondiendo Gemini
        """
        try:
            resp = self.model.generate_content(text)
            return str(resp)
        except Exception as e:
            return f"Error: {str(e)}"


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
                        "evento_nombre": {"type": "string"},
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
                "description": "Actualiza atributos de un evento existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evento_id": {"type": "integer"},
                        "evento_nombre": {"type": "string"},
                        "evento_fecha": {"type": "string", "description": "Fecha en formato YYYY-MM-DD"},
                        "evento_estado": {
                            "type": "string",
                            "enum": ["pendiente", "aprobado", "desaprobado"],
                        },
                    },
                    "required": ["evento_id"],
                },
            },
            {
                "name": "delete_evento",
                "description": "Elimina un evento existente.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "evento_id": {"type": "integer"},
                    },
                    "required": ["evento_id"],
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
    logging.info(f"_parse_tool_calls: Procesando respuesta de Gemini API")
    
    try:
        candidates = getattr(resp, "candidates", None) or []
        logging.info(f"_parse_tool_calls: Encontrados {len(candidates)} candidatos")
        
        for i, cand in enumerate(candidates):
            logging.info(f"_parse_tool_calls: Procesando candidato {i}")
            content = getattr(cand, "content", None)
            if not content:
                logging.warning(f"_parse_tool_calls: Candidato {i} sin contenido")
                continue
                
            parts = getattr(content, "parts", None) or []
            logging.info(f"_parse_tool_calls: Candidato {i} tiene {len(parts)} partes")
            
            for j, p in enumerate(parts):
                logging.info(f"_parse_tool_calls: Procesando parte {j} del candidato {i}")
                fc = getattr(p, "function_call", None)
                
                if fc:
                    name = getattr(fc, "name", None)
                    if name:
                        args = dict(fc.args) if hasattr(fc.args, "items") else (fc.args or {})
                        logging.info(f"_parse_tool_calls: Encontrada function_call '{name}' con args: {args}")
                        out.append({"name": name, "args": args})
                    else:
                        logging.warning(f"_parse_tool_calls: function_call sin nombre en parte {j}")
                else:
                    # Verificar si hay texto normal en lugar de function_call
                    text = getattr(p, "text", None)
                    if text:
                        logging.info(f"_parse_tool_calls: Parte {j} contiene texto: {text[:100]}...")
                    else:
                        logging.info(f"_parse_tool_calls: Parte {j} sin function_call ni texto")
                        
    except Exception as e:
        logging.error(f"_parse_tool_calls: Error parseando respuesta: {str(e)}")
        return []
    
    logging.info(f"_parse_tool_calls: Retornando {len(out)} tool calls")
    return out
