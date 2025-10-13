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
    actions: Optional[List[Dict[str, Any]]] = Field(
        None, 
        description="Acciones opcionales (de un plan previo). Para execute directo, dejar vacío.",
        example=None
    )

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
        logging.info(f"nl_command: {payload.mode} - '{payload.text}' (usuario: {usuario.usuario_id})")
        
        if payload.mode == "plan":
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            result = svc.serialize_plan(plan)
            logging.info(f"nl_command: Plan generado con {len(result.get('actions', []))} acciones")
            return result

        # execute
        if payload.actions:
            # Verificar si son acciones de ejemplo de Swagger
            if len(payload.actions) == 1 and "additionalProp1" in payload.actions[0]:
                logging.warning("nl_command: Ignorando acciones de ejemplo de Swagger")
                plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
                actions = plan.actions
            else:
                logging.info(f"nl_command: Usando {len(payload.actions)} acciones predefinidas")
                try:
                    actions = svc.deserialize_actions(payload.actions)
                except Exception as e:
                    logging.error(f"nl_command: Error deserializando acciones: {str(e)}")
                    raise ValueError(f"Formato de acciones inválido: {str(e)}")
        else:
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            actions = plan.actions

        # Filtrar solo acciones permitidas
        allowed_actions = [a for a in actions if getattr(a, 'allow', True)]
        
        if not allowed_actions:
            logging.warning(f"nl_command: 0 de {len(actions)} acciones permitidas")
            return {"summary": "No hay acciones válidas para ejecutar", "results": []}

        results = svc.execute_actions(db, usuario.usuario_id, allowed_actions)
        logging.info(f"nl_command: {len(results)} acciones ejecutadas exitosamente")
        
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