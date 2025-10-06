from __future__ import annotations

import logging
from typing import Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from .. import auth
from ..services import nl_service as svc
from ..integrations.gemini_client import GeminiClient  # ← nuevo adaptador

router = APIRouter(prefix="/api/v1/nl", tags=["nl"])


class NLCommandRequest(BaseModel):
    """
    mode="plan": genera acciones (no ejecuta)
    mode="execute": ejecuta acciones. Si no se pasan explícitamente, planea y ejecuta.
    """
    text: str = Field(..., min_length=1, description="Instrucción del usuario en lenguaje natural")
    mode: Literal["plan", "execute"] = "plan"
    actions: Optional[List[Dict[str, Any]]] = None  # acciones opcionales (de un plan previo)

class NLPlanResponse(BaseModel):
    summary: str
    actions: List[Dict[str, Any]]

class NLExecuteResponse(BaseModel):
    summary: str
    results: List[Dict[str, Any]]


def get_llm_client() -> GeminiClient:
    """
    Factory muy simple para inyectar el cliente Gemini.
    Lee GEMINI_API_KEY / GEMINI_MODEL del entorno.
    """
    return GeminiClient()


@router.post(
    "/debug",
    summary="Endpoint para debuggear respuestas de Gemini",
)
def debug_gemini(
    text: str,
    llm: GeminiClient = Depends(get_llm_client),
):
    """
    Endpoint temporal para debuggear qué está respondiendo Gemini
    """
    try:
        # Probar directamente la respuesta de Gemini
        raw_response = llm.debug_prompt(text)
        tool_calls = llm.get_tool_calls(text)
        
        return {
            "input_text": text,
            "raw_response": raw_response,
            "tool_calls": tool_calls,
            "tool_calls_count": len(tool_calls)
        }
    except Exception as e:
        return {"error": str(e)}


@router.post(
    "/command",
    response_model=Dict[str, Any],
    summary="Procesa una orden en lenguaje natural (plan / execute)",
    responses={
        200: {"description": "Resultado del plan o ejecución"},
        400: {"description": "Entrada inválida o acciones inconsistentes"},
        403: {"description": "Acceso no autorizado a recursos"},
        500: {"description": "Error interno"},
    },
)
def nl_command(
    payload: NLCommandRequest,
    db: Session = Depends(get_db),
    usuario=Depends(auth.get_current_user),
    llm: GeminiClient = Depends(get_llm_client),  # ← inyección del cliente
):
    """
    Flujo:
      - mode='plan'  -> devuelve summary + actions (sin tocar DB).
      - mode='execute':
          * si vienen actions (del plan), ejecuta esas;
          * si no, planifica y ejecuta en el mismo request.
    """
    try:
        logging.info(f"nl_command: Procesando request - mode: {payload.mode}, text: '{payload.text}', usuario_id: {usuario.usuario_id}")
        
        if payload.mode == "plan":
            logging.info("nl_command: Ejecutando modo plan")
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            result = svc.serialize_plan(plan)
            logging.info(f"nl_command: Plan generado exitosamente con {len(result.get('actions', []))} acciones")
            return result

        # execute
        logging.info("nl_command: Ejecutando modo execute")
        
        if payload.actions:
            logging.info(f"nl_command: Usando acciones predefinidas ({len(payload.actions)} acciones)")
            actions = svc.deserialize_actions(payload.actions)
        else:
            logging.info("nl_command: Generando plan para ejecutar")
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            actions = plan.actions
            logging.info(f"nl_command: Plan generado con {len(actions)} acciones para ejecutar")

        # Filtrar solo acciones permitidas
        allowed_actions = [a for a in actions if getattr(a, 'allow', True)]
        logging.info(f"nl_command: {len(allowed_actions)} de {len(actions)} acciones permitidas para ejecución")
        
        if not allowed_actions:
            logging.warning("nl_command: No hay acciones permitidas para ejecutar")
            return {"summary": "No hay acciones válidas para ejecutar", "results": []}

        logging.info(f"nl_command: Ejecutando {len(allowed_actions)} acciones")
        results = svc.execute_actions(db, usuario.usuario_id, allowed_actions)
        logging.info(f"nl_command: Ejecución completada, {len(results)} resultados")
        
        summary = "Acciones ejecutadas:\n" + "\n".join(f"- {r.get('kind')}" for r in results) if results else "Sin cambios."

        return {"summary": summary, "results": results}

    except PermissionError as e:
        logging.error(f"nl_command: Error de permisos: {str(e)}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        logging.error(f"nl_command: Error de validación: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logging.error(f"nl_command: Error interno: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error procesando la orden: {str(e)}")
