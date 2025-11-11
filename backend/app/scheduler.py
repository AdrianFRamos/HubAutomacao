from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

scheduler: Optional[BackgroundScheduler] = None

def get_scheduler() -> BackgroundScheduler:
    global scheduler
    if scheduler is None:
        scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
    return scheduler

def start_scheduler():
    sch = get_scheduler()
    if not sch.running:
        sch.start()
        logging.info("APScheduler iniciado.")
    try:
        register_jobs()
    except Exception as e:
        logging.warning(f"Falha ao registrar jobs do scheduler: {e}")

def shutdown_scheduler():
    sch = scheduler
    if sch and sch.running:
        sch.shutdown(wait=False)
        logging.info("APScheduler parado.")

def register_jobs():
    sch = get_scheduler()
    try:
        from app.services.schedules import dispatch_due_schedules
        sch.add_job(
            dispatch_due_schedules,
            "interval",
            seconds=30,
            id="poll_due_schedules",
            replace_existing=True,
        )
    except Exception as e:
        logging.warning(f"Não foi possível registrar 'dispatch_due_schedules': {e}")

def add_automation_job(automation_id: str, days_of_week: str, hour: int, minute: int, callback):
    sch = get_scheduler()
    job_id = f"automation_{automation_id}"
    try:
        sch.remove_job(job_id)
    except Exception:
        pass
    trigger = CronTrigger(day_of_week=days_of_week, hour=hour, minute=minute)
    sch.add_job(
        func=callback,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=60,   
        coalesce=True,           
        max_instances=1,
    )
    logging.info(
        f"[{datetime.now()}] Agendamento CRON criado: auto={automation_id} "
        f"{days_of_week} às {hour:02d}:{minute:02d}"
    )

def remove_automation_job(automation_id: str):
    sch = get_scheduler()
    job_id = f"automation_{automation_id}"
    try:
        sch.remove_job(job_id)
        logging.info(f"Agendamento removido para automação {automation_id}")
    except Exception:
        pass
