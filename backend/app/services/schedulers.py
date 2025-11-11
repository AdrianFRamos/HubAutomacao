from __future__ import annotations
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from app.db.database import SessionLocal
from app.db import models
from app.core.config import settings

try:
    from croniter import croniter
    _HAS_CRONITER = True
except Exception:
    _HAS_CRONITER = False

try:
    from app.services.queue import enqueue_run
    _HAS_ENQUEUE_HELPER = True
except Exception:
    _HAS_ENQUEUE_HELPER = False
    try:
        from rq import Queue
        from redis import Redis
        from app.worker import process_run
        _redis = Redis.from_url(getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
        _queue = Queue("runs", connection=_redis)
    except Exception:
        _queue = None

logger = logging.getLogger(__name__)
TZ_UTC = timezone.utc

@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(tz=TZ_UTC)


def _compute_next_run(now_utc: datetime, schedule: "models.Schedule") -> datetime | None:
    stype = (getattr(schedule, "type", None) or "").lower()
    if stype == "cron":
        dow = (getattr(schedule, "days_of_week", "") or "*").strip()
        minute = getattr(schedule, "minute", 0) or 0
        hour = getattr(schedule, "hour", 0) or 0
        cron_expr = f"{minute} {hour} * * {dow}"
        if _HAS_CRONITER:
            try:
                itr = croniter(cron_expr, now_utc)
                return itr.get_next(datetime).astimezone(TZ_UTC)
            except Exception as e:
                logger.warning("Falha ao avaliar cron '%s': %s", cron_expr, e)
                return (now_utc + timedelta(seconds=60)).astimezone(TZ_UTC)
        else:
            return (now_utc + timedelta(seconds=60)).astimezone(TZ_UTC)
    if stype == "interval":
        interval_sec = getattr(schedule, "interval_seconds", None)
        if interval_sec and isinstance(interval_sec, int) and interval_sec > 0:
            return (now_utc + timedelta(seconds=interval_sec)).astimezone(TZ_UTC)
        logger.warning("Schedule %s com interval_seconds inválido.", getattr(schedule, "id", None))
        return None
    if stype == "once":
        run_at = getattr(schedule, "run_at", None)
        if isinstance(run_at, datetime):
            when = run_at.astimezone(TZ_UTC) if run_at.tzinfo else run_at.replace(tzinfo=TZ_UTC)
            return when if when > now_utc else None
        return None
    logger.warning("Schedule %s sem estratégia de disparo reconhecida.", getattr(schedule, "id", None))
    return None


def _enqueue_run_safe(run_id: str | int) -> None:
    if _HAS_ENQUEUE_HELPER:
        enqueue_run(run_id)
        return
    if _queue is not None:
        _queue.enqueue(process_run, run_id)
        return
    logger.error("Nenhuma fila configurada para processar runs; run %s ficará 'queued' até existir worker.", run_id)


def dispatch_due_schedules() -> dict:
    processed = 0
    skipped = 0
    created_runs = 0
    now = _utcnow()
    with session_scope() as db:
        q = (
            select(models.Schedule)
            .where(
                getattr(models.Schedule, "is_active", True) == True,
                getattr(models.Schedule, "next_run_at", now) <= now,
            )
            .order_by(getattr(models.Schedule, "next_run_at", now).asc())
        )
        try:
            q = q.with_for_update(skip_locked=True)
            supports_skip_locked = True
        except Exception:
            supports_skip_locked = False

        try:
            schedules = list(db.execute(q).scalars().all())
        except OperationalError as e:
            logger.warning("Banco não suportou SKIP LOCKED (%s); refazendo sem for_update.", e)
            q = (
                select(models.Schedule)
                .where(
                    getattr(models.Schedule, "is_active", True) == True,
                    getattr(models.Schedule, "next_run_at", now) <= now,
                )
                .order_by(getattr(models.Schedule, "next_run_at", now).asc())
            )
            schedules = list(db.execute(q).scalars().all())
        for sch in schedules:
            processed += 1
            recent_seconds = 5
            recent_cut = now - timedelta(seconds=recent_seconds)

            run_exists_q = (
                select(func.count(models.Run.id))
                .where(
                    getattr(models.Run, "schedule_id", None) == getattr(sch, "id"),
                    getattr(models.Run, "created_at", now) >= recent_cut,
                    getattr(models.Run, "status", "queued").in_(("queued", "running")),
                )
            )
            existing = db.execute(run_exists_q).scalar_one()
            if existing and existing > 0:
                skipped += 1
                continue
            run = models.Run(
                automation_id=getattr(sch, "automation_id"),
                schedule_id=getattr(sch, "id"),
                status="queued",
                trigger="schedule",
                payload=getattr(sch, "payload", None),
                created_at=now,
            )
            db.add(run)
            db.flush()
            next_at = _compute_next_run(now, sch)
            setattr(sch, "last_run_at", now)
            setattr(sch, "next_run_at", next_at)
            created_runs += 1
            try:
                _enqueue_run_safe(run.id)
            except Exception as e:
                logger.exception("Falha ao enfileirar run %s do schedule %s: %s", run.id, sch.id, e)
    summary = {
        "processed_schedules": processed,
        "skipped_due_to_recent_run": skipped,
        "created_runs": created_runs,
        "ts": now.isoformat(),
        "skip_locked": supports_skip_locked,
    }
    logger.info("dispatch_due_schedules summary: %s", summary)
    return summary
