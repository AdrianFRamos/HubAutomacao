from __future__ import annotations
import uuid
from typing import Optional, Any, Dict, List, Sequence, Union
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.db import models
from datetime import datetime, timezone, timedelta
import logging

log = logging.getLogger("crud")

# ---------- Helpers ----------
def _to_uuid(val: Union[str, UUID, None]) -> Optional[UUID]:
    if val is None:
        return None
    if isinstance(val, UUID):
        return val
    try:
        return UUID(str(val))
    except Exception:
        return None

def _to_str_uuid(val: Union[str, UUID, None]) -> Optional[str]:
    u = _to_uuid(val)
    return str(u) if u is not None else None

# ---------- Usuário ----------
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    if not email:
        return None
    return db.query(models.User).filter(func.lower(models.User.email) == email.lower()).first()

def get_user(db: Session, user_id: Union[str, UUID]) -> Optional[models.User]:
    u = _to_uuid(user_id)
    if u is None:
        return None
    return db.query(models.User).filter(models.User.id == u).first()

def get_user_global_role(db: Session, user_id: Union[str, UUID]) -> str:
    u = get_user(db, user_id)
    return (u.role or "").lower() if u else ""

def get_user_sector_ids(db: Session, user_id: Union[str, UUID]) -> List[UUID]:
    uid = _to_uuid(user_id)
    if uid is None:
        return []
    rows = db.query(models.SectorMember.sector_id).filter(models.SectorMember.user_id == uid).all()
    return [r[0] for r in rows]

# alias compatível
def user_sector_ids(db: Session, user_id: Union[str, UUID]) -> set[str]:
    return {str(s) for s in get_user_sector_ids(db, user_id)}

def create_user(db: Session, name: str, email: str, password_hash: str, role: str = "operator") -> models.User:
    u = models.User(name=name, email=email, password=password_hash, role=role)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u

# ---------- Setor ----------
def list_user_sectors(db: Session, user_id: Union[str, UUID]) -> Sequence[models.Sector]:
    uid = _to_uuid(user_id)
    if uid is None:
        return []
    q = (
        db.query(models.Sector)
        .join(models.SectorMember, models.Sector.id == models.SectorMember.sector_id)
        .filter(models.SectorMember.user_id == uid)
    )
    return q.all()

# ---------- Automações ----------
def create_automation(db: Session, name: str, description: Optional[str], module_path: str, func_name: str, owner_type: str, owner_id: Union[str, UUID]) -> models.Automation:
    owner_id_uuid = _to_uuid(owner_id)
    a = models.Automation(
        name=name,
        description=description,
        module_path=module_path,
        func_name=func_name,
        owner_type=owner_type,
        owner_id=owner_id_uuid,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a

def get_automation_by_id(db: Session, automation_id: str | UUID):
    try:
        _ = UUID(str(automation_id))
        return (
            db.query(models.Automation)
            .filter(models.Automation.id == str(automation_id))
            .first()
        )
    except Exception:
        return None

def get_automation_by_id_or_name(db: Session, lookup: str):
    found = get_automation_by_id(db, lookup)
    if found:
        return found
    return (
        db.query(models.Automation)
        .filter(models.Automation.name == lookup)
        .first()
    )

def user_can_execute_automation(db, user_id, automation) -> bool:
    try:
        return user_can_access_automation(db, user_id, automation)
    except NameError:
        user = db.query(models.User).filter(models.User.id == user_id).first()
        if not user:
            return False
        role = (user.role or "").strip().lower()
        if role == "admin" or getattr(user, "is_admin", False):
            return True
        if getattr(automation, "owner_type", None) == "sector":
            sector_id = getattr(automation, "owner_id", None)
            try:
                sector_id = UUID(str(sector_id)) if sector_id else None
            except Exception:
                sector_id = None
            if not sector_id:
                return False
            exists = db.query(models.SectorMember).filter(
                models.SectorMember.user_id == user.id,
                models.SectorMember.sector_id == sector_id
            ).first()
            return exists is not None
        if getattr(automation, "owner_type", None) == "user":
            return str(getattr(automation, "owner_id", "")) == str(user.id)

        return False

def list_automations(db: Session, owner_type: Optional[str] = None, owner_id: Optional[Union[str, UUID]] = None) -> Sequence[models.Automation]:
    q = db.query(models.Automation)
    if owner_type:
        q = q.filter(models.Automation.owner_type == owner_type)
    if owner_id:
        oid = _to_uuid(owner_id)
        if oid:
            q = q.filter(models.Automation.owner_id == oid)
        else:
            q = q.filter(models.Automation.owner_id == owner_id)
    return q.order_by(text("created_at DESC")).all()

def list_automations_for_user(db: Session, user_id: Union[str, UUID]) -> list:
    role_global = get_user_global_role(db, user_id)
    if role_global == "admin":
        return db.query(models.Automation).order_by(text("created_at DESC")).all()
    sector_ids = get_user_sector_ids(db, user_id)
    q_user = db.query(models.Automation).filter(
        models.Automation.owner_type == 'user',
        models.Automation.owner_id == _to_uuid(user_id)
    )
    roles_map = get_user_roles_by_sector(db, user_id)
    is_manager_somewhere = any((r or "").lower() == "manager" for r in roles_map.values())
    if is_manager_somewhere and sector_ids:
        q_sector = db.query(models.Automation).filter(
            models.Automation.owner_type == 'sector',
            models.Automation.owner_id.in_(sector_ids)
        )
        return q_user.union_all(q_sector).order_by(text("created_at DESC")).all()
    return q_user.order_by(text("created_at DESC")).all()

def list_automations_assigned_to_user(db: Session, user_id: Union[str, UUID]) -> List[models.Automation]:
    uid = _to_uuid(user_id)
    return (
        db.query(models.Automation)
        .join(models.AutomationOperator, models.AutomationOperator.automation_id == models.Automation.id)
        .filter(models.AutomationOperator.user_id == uid)
        .order_by(models.Automation.created_at.desc())
        .all()
    )

def user_can_access_automation(db: Session, user_id: Union[str, UUID], automation: models.Automation) -> bool:
    role_global = get_user_global_role(db, user_id)
    if role_global == "admin":
        return True
    if automation.owner_type == 'user':
        return str(automation.owner_id) == str(_to_uuid(user_id))
    roles_map = get_user_roles_by_sector(db, user_id)
    user_sector_role = (roles_map.get(str(automation.owner_id)) or "").lower()
    return user_sector_role == "manager"

def create_run(
    db: Session,
    *,
    automation_id: str,
    user_id: Optional[str] = None,
    status: str = "queued",
    payload: Optional[dict] = None,
    started_at: Optional[datetime] = None,
) -> models.Run:
    run = models.Run(
        automation_id=str(automation_id),
        user_id=str(user_id) if user_id else None,
        status=status,
        payload=payload or {},
        started_at=started_at,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run

def set_run_status_running(db: Session, run_id: Union[str, UUID]):
    rid = _to_str_uuid(run_id)
    db.execute(text("UPDATE runs SET status='running', started_at=now() WHERE id=:id"), {"id": rid})
    db.commit()

def set_run_status_final(db: Session, run_id: Union[str, UUID], status: str, result: Optional[Dict[str, Any]] = None):
    rid = _to_str_uuid(run_id)
    status_norm = status.lower()
    db.execute(
        text("UPDATE runs SET status=:st, finished_at=now(), result=:res WHERE id=:id"),
        {"st": status_norm, "res": result, "id": rid}
    )
    db.commit()

def get_run(db: Session, run_id: Union[str, UUID]) -> Optional[models.Run]:
    rid = _to_uuid(run_id)
    if rid is None:
        return None
    return db.query(models.Run).filter(models.Run.id == rid).first()

def list_runs_for_user(db: Session, user_id: Union[str, UUID], automation_id: Optional[Union[str, UUID]] = None) -> list[models.Run]:
    role_global = get_user_global_role(db, user_id)
    q = db.query(models.Run).join(models.Automation, models.Run.automation_id == models.Automation.id)
    if role_global == "admin":
        if automation_id:
            q = q.filter(models.Run.automation_id == _to_uuid(automation_id))
        return q.order_by(text("runs.started_at DESC NULLS LAST, runs.created_at DESC NULLS LAST, runs.id DESC")).all()

    roles_map = get_user_roles_by_sector(db, user_id)
    manager_sector_ids = [_to_uuid(sid) for sid, r in roles_map.items() if (r or "").lower() == "manager"]
    cond = ((models.Automation.owner_type == 'user') & (models.Automation.owner_id == _to_uuid(user_id)))
    if manager_sector_ids:
        cond = cond | ((models.Automation.owner_type == 'sector') & (models.Automation.owner_id.in_(manager_sector_ids)))
    q = q.filter(cond)
    if automation_id:
        q = q.filter(models.Run.automation_id == _to_uuid(automation_id))
    return q.order_by(
        models.Run.started_at.desc().nullslast(),
        models.Run.created_at.desc().nullslast(),
        models.Run.id.desc(),
    ).all()

def get_user_roles_by_sector(db: Session, user_id: Union[str, UUID]) -> dict:
    uid = _to_uuid(user_id)
    if uid is None:
        return {}
    rows = (
        db.query(models.SectorMember.sector_id, models.SectorMember.role)
        .filter(models.SectorMember.user_id == uid)
        .all()
    )
    return {str(sid): (role or "") for sid, role in rows}

def user_is_operator_of_automation(db: Session, user_id: Union[str, UUID], automation_id: Union[str, UUID]) -> bool:
    uid = _to_uuid(user_id)
    aid = _to_uuid(automation_id)
    if uid is None or aid is None:
        return False
    exists = (
        db.query(models.AutomationOperator)
        .filter(
            models.AutomationOperator.user_id == uid,
            models.AutomationOperator.automation_id == aid,
        )
        .first()
    )
    return bool(exists)

def assign_operator(db: Session, automation_id: Union[str, UUID], user_id: Union[str, UUID]) -> models.AutomationOperator:
    aid = _to_uuid(automation_id)
    uid = _to_uuid(user_id)
    if aid is None or uid is None:
        raise ValueError("automation_id/user_id inválidos")
    ex = (
        db.query(models.AutomationOperator)
        .filter_by(automation_id=aid, user_id=uid)
        .first()
    )
    if ex:
        return ex
    ao = models.AutomationOperator(automation_id=aid, user_id=uid)
    db.add(ao)
    db.commit()
    db.refresh(ao)
    return ao

# ---------- Secrets (USANDO UUID de verdade) ----------
def upsert_secret(db: Session, *, owner_type: str, owner_id: Union[str, UUID], key: str, value_ciphertext: str) -> models.Secret:
    oid = _to_uuid(owner_id)
    if oid is None:
        raise ValueError("owner_id inválido (esperado UUID)")
    existing = (
        db.query(models.Secret)
        .filter(
            models.Secret.owner_type == owner_type,
            models.Secret.owner_id == str(oid),
            models.Secret.key == key,
        )
        .first()
    )
    if existing:
        existing.value_ciphertext = value_ciphertext
        db.commit()
        db.refresh(existing)
        return existing
    s = models.Secret(owner_type=owner_type, owner_id=str(oid), key=key, value_ciphertext=value_ciphertext)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def list_secrets(db: Session, *, owner_type: str, owner_id: Union[str, UUID]) -> list[models.Secret]:
    oid = _to_uuid(owner_id)
    if oid is None:
        raise ValueError("owner_id inválido (esperado UUID)")
    return (
        db.query(models.Secret)
        .filter(models.Secret.owner_type == owner_type, models.Secret.owner_id == str(oid))
        .order_by(models.Secret.created_at.desc())
        .all()
    )

def get_secret(db: Session, secret_id: Union[str, UUID]) -> Optional[models.Secret]:
    sid = _to_str_uuid(secret_id)
    if not sid:
        return None
    return db.query(models.Secret).filter(models.Secret.id == sid).first()

def delete_secret(db: Session, secret_id: Union[str, UUID]) -> None:
    sid = _to_str_uuid(secret_id)
    if not sid:
        return
    db.query(models.Secret).filter(models.Secret.id == sid).delete()
    db.commit()

# ---------- Schedules ----------
def _compute_initial_next_run(*, type: str, run_at: Optional[datetime], interval_seconds: Optional[int]) -> Optional[datetime]:
    now = datetime.now(timezone.utc)
    if type == "once":
        return run_at if run_at and run_at > now else now
    if type == "interval":
        if not interval_seconds or interval_seconds <= 0:
            return None
        return now + timedelta(seconds=interval_seconds)
    return None

def create_schedule(
    db: Session,
    *,
    automation_id: Union[str, UUID],
    owner_type: str,
    owner_id: Union[str, UUID],
    type: str,
    run_at: Optional[datetime],
    interval_seconds: Optional[int],
    enabled: bool = True,
) -> models.Schedule:
    next_run = _compute_initial_next_run(type=type, run_at=run_at, interval_seconds=interval_seconds)
    sc = models.Schedule(
        automation_id=_to_uuid(automation_id),
        owner_type=owner_type,
        owner_id=str(_to_uuid(owner_id) or owner_id),
        type=type,
        run_at=run_at,
        interval_seconds=interval_seconds,
        enabled=enabled,
        next_run_at=next_run,
    )
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc

def list_schedules(db: Session, *, automation_id: Optional[Union[str, UUID]] = None) -> list[models.Schedule]:
    q = db.query(models.Schedule)
    if automation_id:
        q = q.filter(models.Schedule.automation_id == _to_uuid(automation_id))
    return q.order_by(models.Schedule.created_at.desc()).all()

def get_schedule(db: Session, schedule_id: Union[str, UUID]) -> Optional[models.Schedule]:
    sid = _to_str_uuid(schedule_id)
    if not sid:
        return None
    return db.query(models.Schedule).filter(models.Schedule.id == sid).first()

def update_schedule(
    db: Session,
    schedule_id: Union[str, UUID],
    *,
    enabled: Optional[bool] = None,
    run_at: Optional[datetime] = None,
    interval_seconds: Optional[int] = None,
) -> Optional[models.Schedule]:
    sc = get_schedule(db, schedule_id)
    if not sc:
        return None
    if enabled is not None:
        sc.enabled = enabled
    if run_at is not None:
        sc.run_at = run_at
    if interval_seconds is not None:
        sc.interval_seconds = interval_seconds
    if sc.next_run_at is None or (sc.type == "once" and run_at is not None) or (sc.type == "interval" and interval_seconds is not None):
        sc.next_run_at = _compute_initial_next_run(type=sc.type, run_at=sc.run_at, interval_seconds=sc.interval_seconds)
    db.commit()
    db.refresh(sc)
    return sc

def delete_schedule(db: Session, schedule_id: Union[str, UUID]) -> None:
    sid = _to_str_uuid(schedule_id)
    if not sid:
        return
    db.query(models.Schedule).filter(models.Schedule.id == sid).delete()
    db.commit()

def find_due_schedules(db: Session, *, limit: int = 50) -> list[models.Schedule]:
    now = datetime.now(timezone.utc)
    return (
        db.query(models.Schedule)
        .filter(models.Schedule.enabled == True)
        .filter(models.Schedule.next_run_at != None)
        .filter(models.Schedule.next_run_at <= now)
        .order_by(models.Schedule.next_run_at.asc())
        .limit(limit)
        .all()
    )

def mark_schedule_triggered(db: Session, sc: models.Schedule) -> None:
    now = datetime.now(timezone.utc)
    sc.last_run_at = now
    if sc.type == "once":
        sc.enabled = False
        sc.next_run_at = None
    else:
        delta = timedelta(seconds=sc.interval_seconds or 0)
        sc.next_run_at = now + (delta if delta.total_seconds() > 0 else timedelta(seconds=60))
    db.commit()

# ---------- Sectors ----------
def list_sectors(db: Session) -> List[models.Sector]:
    return db.query(models.Sector).order_by(models.Sector.name.asc()).all()

def get_sector(db: Session, sector_id: UUID) -> Optional[models.Sector]:
    return db.query(models.Sector).filter(models.Sector.id == sector_id).first()

def create_sector(db: Session, name: str) -> models.Sector:
    s = models.Sector(name=name)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s

def is_user_in_sector(db: Session, user_id: UUID, sector_id: UUID) -> bool:
    return db.query(models.SectorMember).filter(
        models.SectorMember.user_id == user_id,
        models.SectorMember.sector_id == sector_id
    ).first() is not None

# ---------- Runs ----------
def start_run(db: Session, automation_id: UUID, user_id: UUID, payload: dict) -> models.Run:
    r = models.Run(
        automation_id=automation_id,
        user_id=user_id,
        status="running",
        started_at=datetime.utcnow(),
        payload=payload or {}
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

def finish_run(
    db: Session,
    run_id: UUID,
    status: str = "success",
    result: Optional[Any] = None,
    error: Optional[str] = None,
    finished_at: Optional[datetime] = None,
    **extra
):
    run = db.query(models.Run).filter(models.Run.id == run_id).first()
    if not run:
        return None

    run.status = status
    run.finished_at = finished_at or datetime.utcnow()
    if result is not None:
        run.result = result
    if error:
        run.error = error

    db.commit()
    db.refresh(run)
    return run