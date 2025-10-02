# services/nl_service.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional
from datetime import date

from sqlalchemy.orm import Session
from sqlalchemy import select

from .. import models, schemas
from . import subject_service, event_service

ActionKind = Literal[
    "create_materia",
    "update_materia",
    "delete_materia",
    "create_evento",
    "update_evento",
    "delete_evento",
]

@dataclass
class PlannedAction:
    kind: ActionKind
    args: Dict[str, Any]   # argumentos listos para servicio (validados/saneados)
    description: str       # para mostrar al usuario

@dataclass
class PlanResult:
    actions: List[PlannedAction]
    summary: str


# =========
# Utilidades de acceso/ownership
# =========
def _get_materia_by_name(db: Session, usuario_id: int, nombre: str) -> Optional[models.Materia]:
    stmt = select(models.Materia).where(
        models.Materia.materia_usuario_id == usuario_id,
        models.Materia.materia_nombre == nombre.strip(),
    )
    return db.execute(stmt).scalar_one_or_none()

def _ensure_ownership_materia(db: Session, usuario_id: int, materia_id: int) -> models.Materia:
    mat = db.get(models.Materia, materia_id)
    if not mat:
        raise ValueError("Materia no encontrada")
    if mat.materia_usuario_id != usuario_id:
        raise PermissionError("No autorizado para acceder a esta materia")
    return mat

def _ensure_ownership_evento(db: Session, usuario_id: int, evento_id: int) -> models.Evento:
    ev = db.get(models.Evento, evento_id)
    if not ev:
        raise ValueError("Evento no encontrado")
    _ensure_ownership_materia(db, usuario_id, ev.evento_materia_id)
    return ev


# =========
# Normalización del output del LLM → acciones ejecutables
# (recibe tool calls ya parseados por el adaptador Gemini)
# =========
def _normalize_tool_call(
    raw: Dict[str, Any],
    db: Session,
    usuario_id: int,
) -> List[PlannedAction]:
    """
    Normaliza un solo tool_call (puede expandirse a varias acciones).
    Soporta referencias por nombre de materia: arg 'materia_ref' (nombre) → materia_id.
    """
    name = raw.get("name")
    args = raw.get("args") or {}
    out: List[PlannedAction] = []

    # helpers para mapear referencia de materia
    def materia_ref_to_id(mref: Optional[str]) -> Optional[int]:
        if mref is None:
            return None
        found = _get_materia_by_name(db, usuario_id, mref)
        return found.materia_id if found else None

    if name == "create_materia":
        materia_nombre = args.get("materia_nombre")
        materia_descripcion = args.get("materia_descripcion")
        if not materia_nombre:
            raise ValueError("Falta materia_nombre en create_materia")
        out.append(
            PlannedAction(
                kind="create_materia",
                args={
                    "materia_usuario_id": usuario_id,
                    "materia_nombre": materia_nombre.strip(),
                    "materia_descripcion": materia_descripcion,
                },
                description=f"Crear materia '{materia_nombre}'",
            )
        )

    elif name == "update_materia":
        materia_id = args.get("materia_id")
        materia_nombre = args.get("materia_nombre")
        materia_descripcion = args.get("materia_descripcion")
        if materia_id is None:
            # permitir referenciar por nombre actual
            materia_ref = args.get("materia_ref")
            materia_id = materia_ref_to_id(materia_ref)
        if not materia_id:
            raise ValueError("Falta materia_id/materia_ref en update_materia")
        _ensure_ownership_materia(db, usuario_id, materia_id)
        update_args = {}
        if materia_nombre is not None:
            update_args["materia_nombre"] = materia_nombre.strip()
        if materia_descripcion is not None:
            update_args["materia_descripcion"] = materia_descripcion
        out.append(
            PlannedAction(
                kind="update_materia",
                args={"materia_id": materia_id, **update_args},
                description=f"Actualizar materia #{materia_id}",
            )
        )

    elif name == "delete_materia":
        materia_id = args.get("materia_id")
        if materia_id is None:
            materia_ref = args.get("materia_ref")
            materia_id = materia_ref_to_id(materia_ref)
        if not materia_id:
            raise ValueError("Falta materia_id/materia_ref en delete_materia")
        _ensure_ownership_materia(db, usuario_id, materia_id)
        out.append(
            PlannedAction(
                kind="delete_materia",
                args={"materia_id": materia_id},
                description=f"Eliminar materia #{materia_id}",
            )
        )

    elif name == "create_evento":
        # Permite materia_id o materia_ref
        materia_id = args.get("evento_materia_id")
        if materia_id is None:
            materia_ref = args.get("materia_ref")
            materia_id = materia_ref_to_id(materia_ref)
        if not materia_id:
            raise ValueError("Falta evento_materia_id/materia_ref en create_evento")

        _ensure_ownership_materia(db, usuario_id, materia_id)

        evento_nombre = args.get("evento_nombre")
        evento_fecha = args.get("evento_fecha")   # se espera 'YYYY-MM-DD'
        evento_estado = args.get("evento_estado", "pendiente")
        if not evento_nombre or not evento_fecha:
            raise ValueError("Falta evento_nombre o evento_fecha en create_evento")
        out.append(
            PlannedAction(
                kind="create_evento",
                args={
                    "evento_materia_id": materia_id,
                    "evento_nombre": evento_nombre.strip(),
                    "evento_fecha": evento_fecha,  # string ISO; FastAPI lo parsea a date
                    "evento_estado": evento_estado,
                },
                description=f"Crear evento '{evento_nombre}' ({evento_fecha}) en materia #{materia_id}",
            )
        )

    elif name == "update_evento":
        evento_id = args.get("evento_id")
        if not evento_id:
            raise ValueError("Falta evento_id en update_evento")
        _ensure_ownership_evento(db, usuario_id, int(evento_id))

        update_args = {}
        for k in ("evento_nombre", "evento_fecha", "evento_estado"):
            if k in args and args[k] is not None:
                update_args[k] = args[k]
        out.append(
            PlannedAction(
                kind="update_evento",
                args={"evento_id": int(evento_id), **update_args},
                description=f"Actualizar evento #{evento_id}",
            )
        )

    elif name == "delete_evento":
        evento_id = args.get("evento_id")
        if not evento_id:
            raise ValueError("Falta evento_id en delete_evento")
        _ensure_ownership_evento(db, usuario_id, int(evento_id))
        out.append(
            PlannedAction(
                kind="delete_evento",
                args={"evento_id": int(evento_id)},
                description=f"Eliminar evento #{evento_id}",
            )
        )

    # herramientas desconocidas: se ignoran
    return out


# =========
# API del servicio
# =========
def plan_actions(db: Session, usuario_id: int, user_text: str, llm) -> PlanResult:
    """
    Obtiene tool_calls desde el cliente LLM, normaliza a acciones y
    verifica existencias para aplicar la regla de idempotencia:
      - Si existe -> solo UPDATE/DELETE (CREATE prohibido)
      - Si NO existe -> solo CREATE (UPDATE/DELETE prohibido)
    Anota cada acción con: a.allow (bool), a.resolved (dict), a.conflict (str|None)
    y construye un summary legible.
    """
    # 1) tool calls -> acciones normalizadas
    tool_calls = llm.get_tool_calls(user_text, locale="es-AR")
    actions: List[PlannedAction] = []
    for call in tool_calls:
        actions.extend(_normalize_tool_call(call, db, usuario_id))

    # 2) verificación de existencias + regla de negocio (allow/conflict/resolved)
    def _find_materia_by_name(uid: int, nombre: str) -> Optional[models.Materia]:
        q = select(models.Materia).where(
            models.Materia.materia_usuario_id == uid,
            models.Materia.materia_nombre == nombre.strip()
        )
        return db.execute(q).scalar_one_or_none()

    def _find_evento_by_natural_key(mid: int, nombre: str, fecha_val) -> Optional[models.Evento]:
        if isinstance(fecha_val, str):
            try:
                fecha_val = date.fromisoformat(fecha_val)
            except ValueError:
                return None
        q = select(models.Evento).where(
            models.Evento.evento_materia_id == mid,
            models.Evento.evento_nombre == nombre.strip(),
            models.Evento.evento_fecha == fecha_val,
        )
        return db.execute(q).scalar_one_or_none()

    summary_lines: List[str] = []
    if not actions:
        return PlanResult(actions=[], summary="No se detectaron acciones. Podés reformular o ser más específico.")

    for a in actions:
        a.allow = True
        a.resolved = {}
        a.conflict = None

        kind = a.kind
        args = a.args

        if kind == "create_materia":
            nombre = args.get("materia_nombre", "")
            m = _find_materia_by_name(usuario_id, nombre) if nombre else None
            a.resolved["materia_id"] = m.materia_id if m else None
            if m:
                a.allow = False
                a.conflict = "Materia ya existe; solo se permite update/delete."
                summary_lines.append(f"✖ Crear materia '{nombre}': ya existe (id={m.materia_id}).")
            else:
                summary_lines.append(f"✔ Crear materia '{nombre}': permitido (no existe).")

        elif kind in ("update_materia", "delete_materia"):
            mid = args.get("materia_id")
            if not mid and "materia_nombre" in args:
                m2 = _find_materia_by_name(usuario_id, args["materia_nombre"])
                mid = m2.materia_id if m2 else None
            a.resolved["materia_id"] = mid
            if not mid or not db.get(models.Materia, mid):
                a.allow = False
                a.conflict = "Materia no existe; no se permite update/delete."
                summary_lines.append(f"✖ {kind.replace('_', ' ').title()} materia: no existe.")
            else:
                summary_lines.append(f"✔ {kind.replace('_', ' ').title()} materia #{mid}: permitido.")

        elif kind == "create_evento":
            mid = args.get("evento_materia_id")
            nombre = args.get("evento_nombre", "")
            fecha_val = args.get("evento_fecha")
            a.resolved["materia_id"] = mid

            m_ok = bool(mid and db.get(models.Materia, mid))
            if not m_ok:
                a.allow = False
                a.conflict = "Materia no existe; no se puede crear el evento."
                summary_lines.append(f"✖ Crear evento '{nombre}': materia #{mid} no existe.")
            else:
                ev = _find_evento_by_natural_key(mid, nombre, fecha_val)
                a.resolved["evento_id"] = ev.evento_id if ev else None
                if ev:
                    a.allow = False
                    a.conflict = "Evento ya existe; solo se permite update/delete."
                    summary_lines.append(
                        f"✖ Crear evento '{nombre}' ({fecha_val}) en materia #{mid}: ya existe (id={ev.evento_id})."
                    )
                else:
                    summary_lines.append(
                        f"✔ Crear evento '{nombre}' ({fecha_val}) en materia #{mid}: permitido (no existe)."
                    )

        elif kind in ("update_evento", "delete_evento"):
            evid = args.get("evento_id")
            a.resolved["evento_id"] = evid  # ← corregido el typo
            ev = db.get(models.Evento, evid) if evid else None
            if not ev:
                a.allow = False
                a.conflict = "Evento no existe; no se permite update/delete."
                summary_lines.append(f"✖ {kind.replace('_', ' ').title()} evento: no existe.")
            else:
                a.resolved["materia_id"] = ev.evento_materia_id
                summary_lines.append(f"✔ {kind.replace('_', ' ').title()} evento #{evid}: permitido.")

        else:
            a.allow = False
            a.conflict = "Acción desconocida."
            summary_lines.append(f"✖ Acción desconocida: {kind}.")

    summary_header = "Resultado del plan (verificación de existencias):"
    summary = summary_header + "\n" + "\n".join(summary_lines)
    return PlanResult(actions=actions, summary=summary)


def execute_actions(
    db: Session,
    usuario_id: int,
    actions: List[PlannedAction],
) -> List[Dict[str, Any]]:
    """
    Ejecuta las acciones usando los servicios de dominio.
    Retorna una lista de resultados serializables.
    """
    results: List[Dict[str, Any]] = []

    for a in actions:
        if a.kind == "create_materia":
            payload = schemas.MateriaCreate(**a.args)
            m = subject_service.create_subject(db, usuario_id, payload)
            results.append({"kind": a.kind, "materia": m})

        elif a.kind == "update_materia":
            mid = a.args.pop("materia_id")
            payload = schemas.MateriaUpdate(**a.args)
            m = subject_service.update_subject(db, usuario_id, mid, payload)
            results.append({"kind": a.kind, "materia": m})

        elif a.kind == "delete_materia":
            mid = a.args["materia_id"]
            subject_service.delete_subject(db, usuario_id, mid)
            results.append({"kind": a.kind, "deleted": {"materia_id": mid}})

        elif a.kind == "create_evento":
            payload = schemas.EventoCreate(**a.args)
            e = event_service.create_event(db, usuario_id, payload)
            results.append({"kind": a.kind, "evento": e})

        elif a.kind == "update_evento":
            evid = a.args.pop("evento_id")
            payload = schemas.EventoUpdate(**a.args)
            e = event_service.update_event(db, usuario_id, evid, payload)
            results.append({"kind": a.kind, "evento": e})

        elif a.kind == "delete_evento":
            evid = a.args["evento_id"]
            event_service.delete_event(db, usuario_id, evid)
            results.append({"kind": a.kind, "deleted": {"evento_id": evid}})

    return results


# Helpers para (de)serializar acciones para la API
def serialize_plan(plan: PlanResult) -> Dict[str, Any]:
    return {
        "summary": plan.summary,
        "actions": [
            {
                "kind": a.kind,
                "args": a.args,
                "description": a.description,
                "allow": getattr(a, "allow", True),
                "resolved": getattr(a, "resolved", {}),
                "conflict": getattr(a, "conflict", None),
            }
            for a in plan.actions
        ],
    }

def deserialize_actions(items: List[Dict[str, Any]]) -> List[PlannedAction]:
    return [PlannedAction(kind=i["kind"], args=i["args"], description=i.get("description", "")) for i in items]
