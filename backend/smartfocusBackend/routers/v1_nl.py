from __future__ import annotations

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
        if payload.mode == "plan":
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            return svc.serialize_plan(plan)

        # execute
        if payload.actions:
            actions = svc.deserialize_actions(payload.actions)
        else:
            plan = svc.plan_actions(db, usuario.usuario_id, payload.text, llm)
            actions = plan.actions

        results = svc.execute_actions(db, usuario.usuario_id, actions)
        summary = "Acciones ejecutadas:\n" + "\n".join(f"- {r.get('kind')}" for r in results) if results else "Sin cambios."

        return {"summary": summary, "results": results}

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error procesando la orden")
