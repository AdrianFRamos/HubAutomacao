from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator
from typing import Optional, Literal
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import crud, models

router = APIRouter(prefix="/schedules", tags=["schedules"])

def _normalize_roles_map(roles_map):
    if not roles_map:
        return {}
    return {str(k): v for k, v in roles_map.items()}

class ScheduleIn(BaseModel):
    automation_id: str
    owner_type: Literal["user", "sector"]
    owner_id: str
    type: Literal["once", "interval"]
    run_at: Optional[datetime] = None
    interval_seconds: Optional[int] = None
    enabled: bool = True

    @field_validator("run_at", mode="before")
    @classmethod
    def ensure_tz(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v)
            except Exception:
                return v
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

@router.post("", status_code=201)
def create_schedule(
    body: ScheduleIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    auto = crud.get_automation_by_id(db, body.automation_id)
    if not auto:
        raise HTTPException(status_code=404, detail="Automação não encontrada")
    if body.type == "once":
        if not body.run_at:
            raise HTTPException(status_code=400, detail="run_at é obrigatório quando type='once'")
    elif body.type == "interval":
        if not body.interval_seconds or body.interval_seconds <= 0:
            raise HTTPException(status_code=400, detail="interval_seconds deve ser > 0 quando type='interval'")
    if current.role != "admin":
        if auto.owner_type == "sector":
            roles = _normalize_roles_map(crud.get_user_roles_by_sector(db, current.id))
            if (roles.get(str(auto.owner_id)) or "").lower() != "manager":
                raise HTTPException(status_code=403, detail="Sem permissão")
        else:
            if str(auto.owner_id) != str(current.id):
                raise HTTPException(status_code=403, detail="Sem permissão")
    if body.owner_type == "sector":
        roles = _normalize_roles_map(crud.get_user_roles_by_sector(db, current.id))
        if str(body.owner_id) not in roles:
            raise HTTPException(status_code=403, detail="Usuário não pertence ao setor informado")
    sc = crud.create_schedule(
        db,
        automation_id=body.automation_id,
        owner_type=body.owner_type,
        owner_id=str(body.owner_id),
        type=body.type,
        run_at=body.run_at,
        interval_seconds=body.interval_seconds,
        enabled=body.enabled,
    )
    return {
        "id": sc.id,
        "automation_id": sc.automation_id,
        "type": sc.type,
        "enabled": sc.enabled,
        "next_run_at": sc.next_run_at,
    }

@router.get("")
def list_schedules(
    automation_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    items = crud.list_schedules(db, automation_id=automation_id)
    out = []
    for sc in items:
        auto = crud.get_automation_by_id(db, sc.automation_id)
        if not auto:
            continue
        allowed = False
        if current.role == "admin":
            allowed = True
        elif auto.owner_type == "sector":
            roles = _normalize_roles_map(crud.get_user_roles_by_sector(db, current.id))
            allowed = (roles.get(str(auto.owner_id)) or "").lower() in ("manager",)
        else:
            allowed = str(auto.owner_id) == str(current.id)
        if allowed:
            out.append(
                {
                    "id": sc.id,
                    "automation_id": sc.automation_id,
                    "type": sc.type,
                    "enabled": sc.enabled,
                    "run_at": sc.run_at,
                    "interval_seconds": sc.interval_seconds,
                    "next_run_at": sc.next_run_at,
                    "last_run_at": sc.last_run_at,
                    "owner_type": sc.owner_type,
                    "owner_id": sc.owner_id,
                }
            )
    return out

class SchedulePatch(BaseModel):
    enabled: Optional[bool] = None
    run_at: Optional[datetime] = None
    interval_seconds: Optional[int] = None
    @field_validator("run_at", mode="before")
    @classmethod
    def ensure_tz(cls, v):
        if v is None:
            return v
        if isinstance(v, str):
            try:
                v = datetime.fromisoformat(v)
            except Exception:
                return v
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

@router.patch("/{schedule_id}")
def patch_schedule(
    schedule_id: str,
    body: SchedulePatch,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    sc = crud.get_schedule(db, schedule_id)
    if not sc:
        raise HTTPException(status_code=404, detail="Schedule não encontrado")
    auto = crud.get_automation_by_id(db, sc.automation_id)
    if not auto:
        raise HTTPException(status_code=404, detail="Automação não encontrada")
    if current.role != "admin":
        if auto.owner_type == "sector":
            roles = _normalize_roles_map(crud.get_user_roles_by_sector(db, current.id))
            if (roles.get(str(auto.owner_id)) or "").lower() != "manager":
                raise HTTPException(status_code=403, detail="Sem permissão")
        else:
            if str(auto.owner_id) != str(current.id):
                raise HTTPException(status_code=403, detail="Sem permissão")
    sc = crud.update_schedule(
        db,
        schedule_id,
        enabled=body.enabled,
        run_at=body.run_at,
        interval_seconds=body.interval_seconds,
    )
    return {
        "id": sc.id,
        "enabled": sc.enabled,
        "next_run_at": sc.next_run_at,
        "run_at": sc.run_at,
        "interval_seconds": sc.interval_seconds,
    }

@router.delete("/{schedule_id}", status_code=204)
def delete_schedule(
    schedule_id: str,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    sc = crud.get_schedule(db, schedule_id)
    if not sc:
        return
    auto = crud.get_automation_by_id(db, sc.automation_id)
    if not auto:
        return
    if current.role != "admin":
        if auto.owner_type == "sector":
            roles = _normalize_roles_map(crud.get_user_roles_by_sector(db, current.id))
            if (roles.get(str(auto.owner_id)) or "").lower() != "manager":
                raise HTTPException(status_code=403, detail="Sem permissão")
        else:
            if str(auto.owner_id) != str(current.id):
                raise HTTPException(status_code=403, detail="Sem permissão")

    crud.delete_schedule(db, schedule_id)
    return
