from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
scheduler.start()

def add_automation_job(automation_id: str, days_of_week: str, hour: int, minute: int, callback):
    job_id = f"automation_{automation_id}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass
    trigger = CronTrigger(day_of_week=days_of_week, hour=hour, minute=minute)
    scheduler.add_job(
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
    """Desabilita/remover o cron job da automação."""
    job_id = f"automation_{automation_id}"
    try:
        scheduler.remove_job(job_id)
        logging.info(f"Agendamento removido para automação {automation_id}")
    except Exception:
        pass
