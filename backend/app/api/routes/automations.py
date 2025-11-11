from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Literal
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text
from importlib import import_module
from app.db.database import get_db
from app.db import crud, models
from app.api.deps import get_current_user

router = APIRouter(prefix="/automations", tags=["automations"])

class AutomationIn(BaseModel):
    name: str
    description: Optional[str] = None
    module_path: str
    func_name: str
    owner_type: Literal['user', 'sector'] = 'user'
    owner_id: Optional[UUID] = None
    default_payload: Optional[dict] = Field(None, description="Payload padrão para a automação, usado como configuração.")
    config_schema: Optional[dict] = Field(None, description="Schema JSON para o formulário de configuração no frontend.")

class CronScheduleIn(BaseModel):
    enabled: bool = True
    days_of_week: str = Field(..., example="mon,wed,fri")
    hour: int = Field(..., ge=0, le=23, example=8)
    minute: int = Field(..., ge=0, le=59, example=30)

def _assert_sector_membership(db: Session, current: models.User, sector_id: UUID):
    role = (current.role or "").strip().lower()
    if role == "admin" or bool(getattr(current, "is_admin", False)):
        return
    try:
        sector_uuid = UUID(str(sector_id))
    except Exception:
        raise HTTPException(status_code=400, detail="sector_id inválido")
    if hasattr(crud, "is_user_in_sector") and callable(crud.is_user_in_sector):
        if crud.is_user_in_sector(db, current.id, sector_uuid):
            return
        raise HTTPException(status_code=403, detail="Usuario não é um membro desse setor")
    sector_ids = crud.get_user_sector_ids(db, current.id)
    try:
        allowed = {UUID(str(s)) for s in sector_ids}
    except Exception:
        allowed = set(sector_ids)
    if sector_uuid not in allowed:
        raise HTTPException(status_code=403, detail="Usuario não é um membro desse setor")

def _load_callable(module_path: str, func_name: str):
    try:
        mod = import_module(module_path)
        fn = getattr(mod, func_name)
    except Exception as e:
        raise RuntimeError(f"Falha ao importar {module_path}.{func_name}: {e}")
    return fn

def _schedule_job_for_automation(db: Session, automation: models.Automation, cron: CronScheduleIn):
    fn = _load_callable(automation.module_path, automation.func_name)
    add_automation_job(
        automation_id=str(automation.id),
        days_of_week=cron.days_of_week,
        hour=cron.hour,
        minute=cron.minute,
        callback=lambda: fn(), 
    )

@router.post("")
def create_automation(
    data: AutomationIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    owner_type = data.owner_type or 'user'
    if owner_type == 'sector':
        if not data.owner_id:
            raise HTTPException(status_code=400, detail="owner_id é obrigatório quando owner_type='sector'")
        _assert_sector_membership(db, current, data.owner_id)
        owner_id = data.owner_id
    else:
        owner_id = current.id

    a = crud.create_automation(
        db,
        data.name,
        data.description,
        data.module_path,
        data.func_name,
        owner_type,
        owner_id,
        data.default_payload,
        data.config_schema,
    )
    return a

@router.get("")
def list_automations(
    grouped: bool = Query(False),
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    autos = crud.list_automations_for_user(db, current.id)
    items = [
        {
            "id": str(getattr(a, "id", "")),
            "name": a.name,
            "description": getattr(a, "description", None),
            "owner_type": a.owner_type,
            "owner_id": str(getattr(a, "owner_id", "")),
            "created_at": getattr(a, "created_at", None),
            "sector_id": str(getattr(a, "owner_id", "")) if a.owner_type == "sector" else None,
            "sector": a.sector.name if a.sector else None, # Adiciona o nome do setor
        }
        for a in autos
    ]
    if not grouped:
        return items
    grouped_map = {}
    for it in items:
        key = ("user", it["owner_id"]) if it["owner_type"] == "user" else ("sector", it["sector_id"])
        grouped_map.setdefault(key, []).append(it)
    out = []
    mine = [x for x in items if x["owner_type"] == "user" and x["owner_id"] == str(current.id)]
    if mine:
        out.append({"group": "mine", "title": "Minhas automações", "automations": mine})
    for (otype, oid), arr in grouped_map.items():
        if otype == "sector":
            # Tenta obter o nome do setor do primeiro item do grupo
            sector_name = arr[0].get("sector") if arr and arr[0].get("sector") else "Setor Desconhecido"
            out.append({"group": "sector", "sector_id": oid, "title": sector_name, "automations": arr})
    return out

@router.post("/{automation_id}/schedule/cron")
def upsert_cron_schedule(
    automation_id: UUID,
    body: CronScheduleIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    autos = crud.list_automations_for_user(db, current.id)
    auto = next((a for a in autos if str(getattr(a, "id", "")) == str(automation_id)), None)
    if not auto:
        raise HTTPException(status_code=404, detail="Automação não encontrada ou sem permissão")
    if auto.owner_type == "sector":
        _assert_sector_membership(db, current, auto.owner_id)
    db.execute(
        text("""
            INSERT INTO schedules (automation_id, owner_type, owner_id, type, run_at, interval_seconds,
                                   enabled, days_of_week, hour, minute, next_run_at)
            VALUES (:automation_id, :owner_type, :owner_id, 'cron', NULL, NULL,
                    :enabled, :days_of_week, :hour, :minute, NULL)
            ON CONFLICT (id) DO NOTHING
        """),
        {
            "automation_id": str(auto.id),
            "owner_type": auto.owner_type,
            "owner_id": str(auto.owner_id),
            "enabled": body.enabled,
            "days_of_week": body.days_of_week,
            "hour": body.hour,
            "minute": body.minute,
        },
    )
    db.execute(
        text("""
            UPDATE schedules
            SET type='cron',
                enabled=:enabled,
                days_of_week=:days_of_week,
                hour=:hour,
                minute=:minute,
                run_at=NULL,
                interval_seconds=NULL
            WHERE automation_id=:automation_id
        """),
        {
            "enabled": body.enabled,
            "days_of_week": body.days_of_week,
            "hour": body.hour,
            "minute": body.minute,
            "automation_id": str(auto.id),
        },
    )
    db.commit()
    if body.enabled:
        _schedule_job_for_automation(db, auto, body)
    else:
        remove_automation_job(str(auto.id))
    return {"message": "Agendamento CRON atualizado", "automation_id": str(auto.id)}

@router.delete("/{automation_id}/schedule")
def disable_schedule(
    automation_id: UUID,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    autos = crud.list_automations_for_user(db, current.id)
    auto = next((a for a in autos if str(getattr(a, "id", "")) == str(automation_id)), None)
    if not auto:
        raise HTTPException(status_code=404, detail="Automação não encontrada ou sem permissão")
    db.execute(
        text("UPDATE schedules SET enabled = FALSE WHERE automation_id = :aid"),
        {"aid": str(auto.id)}
    )
    db.commit()
    remove_automation_job(str(auto.id))
    return {"message": "Agendamento desabilitado", "automation_id": str(auto.id)}
