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
    created_runs = 0
    skipped = 0
    now = _utcnow()
    with session_scope() as db:
        try:
            schedules = db.query(models.Schedule).filter(
                getattr(models.Schedule, "enabled", True) == True,
                getattr(models.Schedule, "next_run_at", now) <= now,
            ).order_by(models.Schedule.next_run_at.asc()).all()
        except OperationalError as e:
            logger.exception("Erro ao consultar schedules: %s", e)
            schedules = []

        for sch in schedules:
            processed += 1
            try:
                user_id = sch.owner_id if getattr(sch, "owner_type", "") == "user" else None
                run = None
                try:
                    run = __create_run_and_enqueue(db, sch, user_id)
                except Exception as e:
                    logger.exception("Falha ao criar/enfileirar run para schedule %s: %s", getattr(sch, "id", None), e)
                    skipped += 1
                    continue
                try:
                    next_at = _compute_next_run(now, sch)
                    sch.last_run_at = now
                    sch.next_run_at = next_at
                    db.add(sch)
                    db.commit()
                except Exception:
                    logger.exception("Falha ao atualizar next_run para schedule %s", getattr(sch, "id", None))
                created_runs += 1
            except Exception:
                logger.exception("Erro ao processar schedule %s", getattr(sch, "id", None))
                skipped += 1

    summary = {
        "processed_schedules": processed,
        "skipped_due_to_errors": skipped,
        "created_runs": created_runs,
        "ts": now.isoformat(),
    }
    logger.info("dispatch_due_schedules summary: %s", summary)
    return summary


def __create_run_and_enqueue(db: Session, schedule: models.Schedule, user_id=None):
    payload = getattr(schedule, "payload", None) or {}
    run = models.Run(
        automation_id=getattr(schedule, "automation_id"),
        user_id=user_id,
        status="queued",
        payload=payload,
    )
    db.add(run)
    db.flush()
    try:
        if _HAS_ENQUEUE_HELPER:
            from app.services.queue import queue as _q
            _q.enqueue("app.worker.process_run", {"run_id": str(run.id), "user_id": str(user_id) if user_id else None})
        elif _queue is not None:
            _queue.enqueue("app.worker.process_run", {"run_id": str(run.id), "user_id": str(user_id) if user_id else None})
    except Exception:
        logger.exception("Falha ao enfileirar run %s", getattr(run, "id", None))
    return run
