# services/nl_service.py
from __future__ import annotations

import logging
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

def _find_evento_by_references(
    db: Session, 
    usuario_id: int, 
    evento_ref: Optional[str] = None, 
    materia_ref: Optional[str] = None
) -> Optional[models.Evento]:
    """
    Busca evento por nombre y/o materia. Si materia tiene un solo evento y no se especifica evento_ref, 
    retorna ese evento único.
    """
    # Si tenemos materia_ref, buscar la materia primero
    materia = None
    if materia_ref:
        materia = _get_materia_by_name(db, usuario_id, materia_ref)
        if not materia:
            return None
    
    # Construir query base
    query = select(models.Evento).join(models.Materia).where(
        models.Materia.materia_usuario_id == usuario_id
    )
    
    # Filtrar por materia si se especificó
    if materia:
        query = query.where(models.Evento.evento_materia_id == materia.materia_id)
    
    # Filtrar por nombre del evento si se especificó
    if evento_ref:
        query = query.where(models.Evento.evento_nombre.ilike(f"%{evento_ref.strip()}%"))
    
    eventos = db.execute(query).scalars().all()
    
    # Si encontramos exactamente un evento, retornarlo
    if len(eventos) == 1:
        return eventos[0]
    
    # Si hay múltiples eventos y no se especificó evento_ref, pero sí materia_ref
    # verificar si la materia tiene exactamente un evento
    if len(eventos) > 1 and not evento_ref and materia_ref:
        # Verificar cuántos eventos tiene esta materia específica
        materia_eventos = [e for e in eventos if e.evento_materia_id == materia.materia_id]
        if len(materia_eventos) == 1:
            return materia_eventos[0]
    
    return None

def _ensure_ownership_materia(db: Session, usuario_id: int, materia_id: int) -> models.Materia:
    mat = db.get(models.Materia, materia_id)
    if not mat or mat.materia_usuario_id != usuario_id:
        raise ValueError("Materia no encontrada")
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
) -> tuple[List[PlannedAction], List[str]]:
    """
    Normaliza un solo tool_call (puede expandirse a varias acciones).
    Soporta referencias por nombre de materia: arg 'materia_ref' (nombre) → materia_id.
    Retorna (acciones_exitosas, errores_encontrados)
    """
    name = raw.get("name")
    args = raw.get("args") or {}
    logging.info(f"_normalize_tool_call: Procesando tool '{name}' con args: {args}")
    out: List[PlannedAction] = []
    errors: List[str] = []

    try:
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
                errors.append(f"Crear materia: falta el nombre de la materia")
            else:
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
                errors.append(f"Actualizar materia: no se pudo identificar la materia (falta materia_id o materia_ref válido)")
            else:
                try:
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
                except ValueError as e:
                    errors.append(f"Actualizar materia: {str(e)}")

        elif name == "delete_materia":
            materia_id = args.get("materia_id")
            if materia_id is None:
                materia_ref = args.get("materia_ref")
                materia_id = materia_ref_to_id(materia_ref)
            if not materia_id:
                errors.append(f"Eliminar materia: no se pudo identificar la materia (falta materia_id o materia_ref válido)")
            else:
                try:
                    _ensure_ownership_materia(db, usuario_id, materia_id)
                    out.append(
                        PlannedAction(
                            kind="delete_materia",
                            args={"materia_id": materia_id},
                            description=f"Eliminar materia #{materia_id}",
                        )
                    )
                except ValueError as e:
                    errors.append(f"Eliminar materia: {str(e)}")

        elif name == "create_evento":
            # Permite materia_id o materia_ref
            materia_id = args.get("evento_materia_id")
            if materia_id is None:
                materia_ref = args.get("materia_ref")
                materia_id = materia_ref_to_id(materia_ref)
            
            evento_nombre = args.get("evento_nombre")
            evento_fecha = args.get("evento_fecha")   # se espera 'YYYY-MM-DD'
            evento_estado = args.get("evento_estado", "pendiente")
            
            # Validar datos requeridos
            validation_errors = []
            if not materia_id:
                validation_errors.append("falta referencia a la materia")
            if not evento_nombre:
                validation_errors.append("falta nombre del evento")
            if not evento_fecha:
                validation_errors.append("falta fecha del evento")
            
            if validation_errors:
                errors.append(f"Crear evento: {', '.join(validation_errors)}")
            else:
                try:
                    _ensure_ownership_materia(db, usuario_id, materia_id)
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
                except ValueError as e:
                    errors.append(f"Crear evento: {str(e)}")

        elif name == "update_evento":
            evento_id = args.get("evento_id")
            
            # Si no tenemos evento_id, intentar encontrarlo por referencias
            if not evento_id:
                evento_ref = args.get("evento_ref")
                materia_ref = args.get("materia_ref")
                
                if evento_ref or materia_ref:
                    try:
                        evento = _find_evento_by_references(db, usuario_id, evento_ref, materia_ref)
                        if evento:
                            evento_id = evento.evento_id
                            logging.info(f"_normalize_tool_call: Evento encontrado por referencias - ID: {evento_id}")
                        else:
                            errors.append(f"Actualizar evento: no se encontró evento con referencias evento_ref='{evento_ref}', materia_ref='{materia_ref}'")
                    except Exception as e:
                        errors.append(f"Actualizar evento: error buscando por referencias - {str(e)}")
            
            if not evento_id:
                if not args.get("evento_ref") and not args.get("materia_ref"):
                    errors.append(f"Actualizar evento: proporciona evento_id, evento_ref, o materia_ref")
            else:
                try:
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
                except ValueError as e:
                    errors.append(f"Actualizar evento: {str(e)}")

        elif name == "delete_evento":
            evento_id = args.get("evento_id")
            
            # Si no tenemos evento_id, intentar encontrarlo por referencias
            if not evento_id:
                evento_ref = args.get("evento_ref")
                materia_ref = args.get("materia_ref")
                
                if evento_ref or materia_ref:
                    try:
                        evento = _find_evento_by_references(db, usuario_id, evento_ref, materia_ref)
                        if evento:
                            evento_id = evento.evento_id
                            logging.info(f"_normalize_tool_call: Evento encontrado por referencias - ID: {evento_id}")
                        else:
                            errors.append(f"Eliminar evento: no se encontró evento con referencias evento_ref='{evento_ref}', materia_ref='{materia_ref}'")
                    except Exception as e:
                        errors.append(f"Eliminar evento: error buscando por referencias - {str(e)}")
            
            if not evento_id:
                if not args.get("evento_ref") and not args.get("materia_ref"):
                    errors.append(f"Eliminar evento: proporciona evento_id, evento_ref, o materia_ref")
            else:
                try:
                    _ensure_ownership_evento(db, usuario_id, int(evento_id))
                    out.append(
                        PlannedAction(
                            kind="delete_evento",
                            args={"evento_id": int(evento_id)},
                            description=f"Eliminar evento #{evento_id}",
                        )
                    )
                except ValueError as e:
                    errors.append(f"Eliminar evento: {str(e)}")

        else:
            if name:
                errors.append(f"Acción desconocida: {name}")
            else:
                errors.append("Tool call sin nombre válido")

    except Exception as e:
        logging.error(f"_normalize_tool_call: Error inesperado procesando tool '{name}': {str(e)}")
        errors.append(f"Error procesando acción '{name}': {str(e)}")

    # herramientas desconocidas: se ignoran
    return out, errors


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
    NUEVA FUNCIONALIDAD: Procesa múltiples acciones de manera independiente,
    reportando errores individuales sin cancelar toda la operación.
    """
    logging.info(f"plan_actions: Procesando texto del usuario: '{user_text}'")
    
    # 1) tool calls -> acciones normalizadas
    tool_calls = llm.get_tool_calls(user_text, locale="es-AR")
    logging.info(f"plan_actions: Recibidas {len(tool_calls)} tool calls: {tool_calls}")
    
    actions: List[PlannedAction] = []
    processing_errors: List[str] = []
    
    # Procesar cada tool call de manera independiente
    for i, call in enumerate(tool_calls):
        try:
            normalized_actions, call_errors = _normalize_tool_call(call, db, usuario_id)
            logging.info(f"plan_actions: Tool call {i+1} '{call.get('name')}' generó {len(normalized_actions)} acciones normalizadas")
            actions.extend(normalized_actions)
            
            # Agregar errores específicos de este call
            if call_errors:
                processing_errors.extend(call_errors)
                logging.warning(f"plan_actions: Tool call {i+1} tuvo {len(call_errors)} errores: {call_errors}")
                
        except Exception as e:
            error_msg = f"Error procesando instrucción {i+1} ('{call.get('name', 'unknown')}'): {str(e)}"
            processing_errors.append(error_msg)
            logging.error(f"plan_actions: {error_msg}")

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
    
    # Agregar resumen de errores al inicio si los hay
    if processing_errors:
        summary_lines.append("❌ ERRORES ENCONTRADOS:")
        for error in processing_errors:
            summary_lines.append(f"   • {error}")
        summary_lines.append("")  # línea en blanco para separar
    
    if not actions and not processing_errors:
        logging.warning(f"plan_actions: No se generaron acciones ni errores para el texto '{user_text}'. Tool calls recibidas: {tool_calls}")
        return PlanResult(actions=[], summary="No se detectaron acciones válidas. Podés reformular o ser más específico.")
    
    # Procesar acciones válidas
    if actions:
        summary_lines.append("📋 ACCIONES PLANIFICADAS:")
        
        for a in actions:
            a.allow = True
            a.resolved = {}
            a.conflict = None

            kind = a.kind
            args = a.args

            if kind == "create_materia":
                nombre = args.get("materia_nombre", "")
                logging.info(f"plan_actions: Verificando si materia '{nombre}' ya existe para usuario {usuario_id}")
                m = _find_materia_by_name(usuario_id, nombre) if nombre else None
                a.resolved["materia_id"] = m.materia_id if m else None
                if m:
                    a.allow = False
                    a.conflict = "Materia ya existe; solo se permite update/delete."
                    logging.warning(f"plan_actions: Materia '{nombre}' ya existe (id={m.materia_id}), bloqueando creación")
                    summary_lines.append(f"   ✖ Crear materia '{nombre}': ya existe (id={m.materia_id}).")
                else:
                    logging.info(f"plan_actions: Materia '{nombre}' no existe, permitiendo creación")
                    summary_lines.append(f"   ✔ Crear materia '{nombre}': permitido (no existe).")

            elif kind in ("update_materia", "delete_materia"):
                mid = args.get("materia_id")
                if not mid and "materia_nombre" in args:
                    m2 = _find_materia_by_name(usuario_id, args["materia_nombre"])
                    mid = m2.materia_id if m2 else None
                a.resolved["materia_id"] = mid
                if not mid or not db.get(models.Materia, mid):
                    a.allow = False
                    a.conflict = "Materia no existe; no se permite update/delete."
                    summary_lines.append(f"   ✖ {kind.replace('_', ' ').title()} materia: no existe.")
                else:
                    summary_lines.append(f"   ✔ {kind.replace('_', ' ').title()} materia #{mid}: permitido.")

            elif kind == "create_evento":
                mid = args.get("evento_materia_id")
                nombre = args.get("evento_nombre", "")
                fecha_val = args.get("evento_fecha")
                a.resolved["materia_id"] = mid

                m_ok = bool(mid and db.get(models.Materia, mid))
                if not m_ok:
                    a.allow = False
                    a.conflict = "Materia no existe; no se puede crear el evento."
                    summary_lines.append(f"   ✖ Crear evento '{nombre}': materia #{mid} no existe.")
                else:
                    ev = _find_evento_by_natural_key(mid, nombre, fecha_val)
                    a.resolved["evento_id"] = ev.evento_id if ev else None
                    if ev:
                        a.allow = False
                        a.conflict = "Evento ya existe; solo se permite update/delete."
                        summary_lines.append(
                            f"   ✖ Crear evento '{nombre}' ({fecha_val}) en materia #{mid}: ya existe (id={ev.evento_id})."
                        )
                    else:
                        summary_lines.append(
                            f"   ✔ Crear evento '{nombre}' ({fecha_val}) en materia #{mid}: permitido (no existe)."
                        )

            elif kind in ("update_evento", "delete_evento"):
                evid = args.get("evento_id")
                a.resolved["evento_id"] = evid  # ← corregido el typo
                ev = db.get(models.Evento, evid) if evid else None
                if not ev:
                    a.allow = False
                    a.conflict = "Evento no existe; no se permite update/delete."
                    summary_lines.append(f"   ✖ {kind.replace('_', ' ').title()} evento: no existe.")
                else:
                    a.resolved["materia_id"] = ev.evento_materia_id
                    summary_lines.append(f"   ✔ {kind.replace('_', ' ').title()} evento #{evid}: permitido.")

            else:
                a.allow = False
                a.conflict = "Acción desconocida."
                summary_lines.append(f"   ✖ Acción desconocida: {kind}.")
    
    # Agregar resumen final
    valid_actions = [a for a in actions if getattr(a, 'allow', True)]
    total_requested = len(tool_calls)
    total_valid = len(valid_actions)
    total_errors = len(processing_errors)
    
    if total_requested > 1:
        summary_lines.append("")
        if total_errors > 0 and total_valid > 0:
            summary_lines.append(f"📊 RESUMEN: Se detectaron {total_requested} instrucciones. {total_valid} se pueden ejecutar, {total_errors} tuvieron errores.")
        elif total_errors > 0:
            summary_lines.append(f"📊 RESUMEN: Se detectaron {total_requested} instrucciones. Ninguna se pudo interpretar correctamente.")
        elif total_valid == total_requested:
            summary_lines.append(f"📊 RESUMEN: Se detectaron {total_requested} instrucciones. Todas se pueden ejecutar.")
        else:
            summary_lines.append(f"📊 RESUMEN: Se detectaron {total_requested} instrucciones. {total_valid} se pueden ejecutar.")

    summary = "\n".join(summary_lines)
    return PlanResult(actions=actions, summary=summary)


def execute_actions(
    db: Session,
    usuario_id: int,
    actions: List[PlannedAction],
) -> List[Dict[str, Any]]:
    """
    Ejecuta las acciones usando los servicios de dominio.
    Retorna una lista de resultados serializables.
    NUEVA FUNCIONALIDAD: Procesa acciones de manera independiente,
    continuando con las siguientes aunque alguna falle.
    """
    logging.info(f"execute_actions: Ejecutando {len(actions)} acciones para usuario {usuario_id}")
    results: List[Dict[str, Any]] = []
    execution_errors: List[str] = []

    for i, a in enumerate(actions):
        try:
            logging.info(f"execute_actions: Procesando acción {i+1}/{len(actions)}: {a.kind}")
            
            # Verificar que la acción esté permitida
            if not getattr(a, 'allow', True):
                logging.warning(f"execute_actions: Acción {a.kind} no permitida, saltando")
                error_msg = f"Acción {i+1} ({a.kind}): no permitida - {getattr(a, 'conflict', 'sin razón específica')}"
                execution_errors.append(error_msg)
                results.append({
                    "kind": a.kind, 
                    "status": "skipped", 
                    "reason": getattr(a, 'conflict', 'no permitida'),
                    "description": a.description
                })
                continue

            # Ejecutar según el tipo de acción
            if a.kind == "create_materia":
                logging.info(f"execute_actions: Creando materia con args: {a.args}")
                payload = schemas.MateriaCreate(**a.args)
                m = subject_service.create_subject(db, usuario_id, payload)
                # Convertir el objeto ORM a diccionario serializable
                materia_dict = {
                    "materia_id": m.materia_id,
                    "materia_nombre": m.materia_nombre,
                    "materia_descripcion": m.materia_descripcion,
                    "materia_usuario_id": m.materia_usuario_id,
                    "materia_created_at": m.materia_created_at.isoformat() if m.materia_created_at else None
                }
                results.append({"kind": a.kind, "status": "success", "materia": materia_dict})
                logging.info(f"execute_actions: Materia creada exitosamente: {materia_dict}")

            elif a.kind == "update_materia":
                # Hacer copia de args para no modificar el original
                args_copy = a.args.copy()
                mid = args_copy.pop("materia_id")
                logging.info(f"execute_actions: Actualizando materia {mid} con args: {args_copy}")
                payload = schemas.MateriaUpdate(**args_copy)
                m = subject_service.update_subject(db, usuario_id, mid, payload)
                # Convertir el objeto ORM a diccionario serializable
                materia_dict = {
                    "materia_id": m.materia_id,
                    "materia_nombre": m.materia_nombre,
                    "materia_descripcion": m.materia_descripcion,
                    "materia_usuario_id": m.materia_usuario_id,
                    "materia_created_at": m.materia_created_at.isoformat() if m.materia_created_at else None
                }
                results.append({"kind": a.kind, "status": "success", "materia": materia_dict})
                logging.info(f"execute_actions: Materia actualizada exitosamente: {materia_dict}")

            elif a.kind == "delete_materia":
                mid = a.args["materia_id"]
                logging.info(f"execute_actions: Eliminando materia {mid}")
                subject_service.delete_subject(db, usuario_id, mid)
                results.append({"kind": a.kind, "status": "success", "deleted": {"materia_id": mid}})
                logging.info(f"execute_actions: Materia {mid} eliminada exitosamente")

            elif a.kind == "create_evento":
                logging.info(f"execute_actions: Creando evento con args: {a.args}")
                payload = schemas.EventoCreate(**a.args)
                e = event_service.create_event(db, usuario_id, payload)
                # Convertir el objeto ORM a diccionario serializable
                evento_dict = {
                    "evento_id": e.evento_id,
                    "evento_nombre": e.evento_nombre,
                    "evento_fecha": e.evento_fecha.isoformat() if e.evento_fecha else None,
                    "evento_estado": e.evento_estado,
                    "evento_materia_id": e.evento_materia_id,
                    "evento_created_at": e.evento_created_at.isoformat() if e.evento_created_at else None
                }
                results.append({"kind": a.kind, "status": "success", "evento": evento_dict})
                logging.info(f"execute_actions: Evento creado exitosamente: {evento_dict}")

            elif a.kind == "update_evento":
                # Hacer copia de args para no modificar el original
                args_copy = a.args.copy()
                evid = args_copy.pop("evento_id")
                logging.info(f"execute_actions: Actualizando evento {evid} con args: {args_copy}")
                payload = schemas.EventoUpdate(**args_copy)
                e = event_service.update_event(db, usuario_id, evid, payload)
                # Convertir el objeto ORM a diccionario serializable
                evento_dict = {
                    "evento_id": e.evento_id,
                    "evento_nombre": e.evento_nombre,
                    "evento_fecha": e.evento_fecha.isoformat() if e.evento_fecha else None,
                    "evento_estado": e.evento_estado,
                    "evento_materia_id": e.evento_materia_id,
                    "evento_created_at": e.evento_created_at.isoformat() if e.evento_created_at else None
                }
                results.append({"kind": a.kind, "status": "success", "evento": evento_dict})
                logging.info(f"execute_actions: Evento actualizado exitosamente: {evento_dict}")

            elif a.kind == "delete_evento":
                evid = a.args["evento_id"]
                logging.info(f"execute_actions: Eliminando evento {evid}")
                event_service.delete_event(db, usuario_id, evid)
                results.append({"kind": a.kind, "status": "success", "deleted": {"evento_id": evid}})
                logging.info(f"execute_actions: Evento {evid} eliminado exitosamente")
                
            else:
                logging.warning(f"execute_actions: Tipo de acción desconocido: {a.kind}")
                error_msg = f"Acción {i+1}: tipo desconocido '{a.kind}'"
                execution_errors.append(error_msg)
                results.append({
                    "kind": a.kind, 
                    "status": "error", 
                    "error": "Tipo de acción desconocido",
                    "description": a.description
                })
                
        except Exception as e:
            logging.error(f"execute_actions: Error ejecutando acción {a.kind}: {str(e)}", exc_info=True)
            error_msg = f"Acción {i+1} ({a.kind}): {str(e)}"
            execution_errors.append(error_msg)
            results.append({
                "kind": a.kind, 
                "status": "error", 
                "error": str(e),
                "description": a.description
            })
            # Continuamos con las siguientes acciones

    successful_results = [r for r in results if r.get("status") == "success"]
    failed_results = [r for r in results if r.get("status") in ["error", "skipped"]]
    
    logging.info(f"execute_actions: Ejecución completada - {len(successful_results)} exitosas, {len(failed_results)} fallidas/omitidas")
    
    # Agregar resumen de ejecución al final de los resultados
    if len(actions) > 1:
        summary_result = {
            "kind": "execution_summary",
            "status": "summary",
            "total_actions": len(actions),
            "successful": len(successful_results),
            "failed": len([r for r in results if r.get("status") == "error"]),
            "skipped": len([r for r in results if r.get("status") == "skipped"]),
            "errors": execution_errors if execution_errors else None
        }
        results.append(summary_result)
    
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
    """Deserializa acciones desde el formato JSON a PlannedAction"""
    logging.info(f"deserialize_actions: Deserializando {len(items)} acciones")
    result = []
    
    for i, item in enumerate(items):
        try:
            logging.info(f"deserialize_actions: Procesando acción {i}: {item}")
            
            # Validar campos requeridos
            if "kind" not in item:
                raise ValueError(f"Acción {i} falta campo 'kind'. Campos disponibles: {list(item.keys())}")
            if "args" not in item:
                raise ValueError(f"Acción {i} falta campo 'args'. Campos disponibles: {list(item.keys())}")
                
            action = PlannedAction(
                kind=item["kind"], 
                args=item["args"], 
                description=item.get("description", "")
            )
            
            # Preservar atributos adicionales si existen
            if "allow" in item:
                action.allow = item["allow"]
            if "resolved" in item:
                action.resolved = item["resolved"]
            if "conflict" in item:
                action.conflict = item["conflict"]
                
            result.append(action)
            logging.info(f"deserialize_actions: Acción {i} deserializada exitosamente: {action.kind}")
            
        except Exception as e:
            logging.error(f"deserialize_actions: Error procesando acción {i}: {str(e)}")
            logging.error(f"deserialize_actions: Formato de acción inválido: {item}")
            raise ValueError(f"Error en acción {i}: {str(e)}. Formato esperado: {{\"kind\": \"create_materia\", \"args\": {{...}}, \"description\": \"...\", \"allow\": true}}")
    
    logging.info(f"deserialize_actions: {len(result)} acciones deserializadas exitosamente")
    return result