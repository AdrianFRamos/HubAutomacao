import time
import logging
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.db import database, crud
from app.services.queue import queue

# --- Configuração de Logging Estruturado ---
log = logging.getLogger("scheduler")

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        return json.dumps(log_record, default=str)

logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()],
)

for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())
# -------------------------------------------

def _poll_schedules_loop():
    """Loop principal que verifica o banco de dados por agendamentos pendentes."""
    log.info("Iniciando o loop de polling do scheduler...")
    while True:
        db: Session = database.SessionLocal()
        try:
            schedules = crud.get_due_schedules(db)
            if schedules:
                log.info(f"Encontrados {len(schedules)} agendamentos para executar.")
            for schedule in schedules:
                try:
                    log.info(f"Enfileirando job para o agendamento {schedule.id} (automação {schedule.automation_id})")
                    run = crud.create_run(
                        db,
                        automation_id=schedule.automation_id,
                        user_id=schedule.owner_id if schedule.owner_type == 'user' else None,
                        status="queued",
                        payload=schedule.payload or {},
                    )
                    queue.enqueue("app.worker.process_run", {"run_id": str(run.id), "user_id": str(run.user_id)})
                    crud.update_schedule_next_run(db, schedule.id)
                except Exception as e:
                    log.error(f"Erro ao processar agendamento {schedule.id}: {e}", exc_info=True)
        except Exception as e:
            log.error(f"Erro no loop de polling do scheduler: {e}", exc_info=True)
        finally:
            db.close()
        
        # Aguarda 60 segundos antes da próxima verificação
        time.sleep(60)

if __name__ == "__main__":
    _poll_schedules_loop()
