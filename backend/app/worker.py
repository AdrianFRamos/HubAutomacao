import logging
from uuid import UUID
from sqlalchemy.orm import Session
from app.db import database
from app.db import models, crud

log = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)

def _parse_uuid_or_none(value: str):
    if value is None:
        return None
    s = str(value).strip()
    if s == "":
        return None
    return UUID(s)

def process_run(job_payload: dict):
    try:
        run_id = _parse_uuid_or_none(job_payload.get("run_id"))
        if run_id is None:
            log.error("process_run: run_id ausente ou inválido no payload: %s", job_payload)
            return
        try:
            user_id = _parse_uuid_or_none(job_payload.get("user_id"))
        except ValueError:
            log.error("process_run: user_id inválido no payload: %s", job_payload)
            user_id = None
    except Exception:
        log.exception("process_run: erro ao parsear IDs do payload: %s", job_payload)
        return
    db: Session = database.SessionLocal()
    try:
        run = crud.get_run(db, run_id)
        if not run:
            log.warning("process_run: run não encontrado: %s", run_id)
            return
        auto = crud.get_automation_by_id(db, run.automation_id)
        if not auto:
            log.error("process_run: automação não encontrada para run %s (automation_id=%s)", run_id, run.automation_id)
            try:
                crud.set_run_status_final(db, run_id, "failed", {"ok": False, "error": "Automação não encontrada"})
            except Exception:
                log.exception("process_run: falha ao setar status final para run %s", run_id)
            return
        if user_id is not None:
            try:
                allowed = crud.user_can_access_automation(db, user_id, auto)
            except Exception:
                log.exception("process_run: erro ao verificar permissão para user %s e automation %s", user_id, auto.id)
                try:
                    crud.set_run_status_final(db, run_id, "failed", {"ok": False, "error": "Erro ao verificar permissões"})
                except Exception:
                    log.exception("process_run: falha ao setar status final para run %s", run_id)
                return
            if not allowed:
                log.warning("process_run: usuário %s não tem acesso à automação %s", user_id, auto.id)
                try:
                    crud.set_run_status_final(
                        db,
                        run_id,
                        "failed",
                        {"ok": False, "error": "Acesso Não Autorizado"},
                    )
                except Exception:
                    log.exception("process_run: falha ao setar status final (sem permissão) para run %s", run_id)
                return
        try:
            from app.services.runner import execute_run
        except Exception:
            log.exception("process_run: não foi possível importar execute_run")
            crud.set_run_status_final(db, run_id, "failed", {"ok": False, "error": "Erro interno do worker"})
            return
        try:
            success = execute_run(db, run.id, auto, user_id, run.payload or {})
            if not success:
                log.warning("process_run: execute_run retornou False para run %s", run_id)
            else:
                log.info("process_run: execute_run finalizou com sucesso para run %s", run_id)
        except Exception:
            log.exception("process_run: exceção durante execução do run %s", run_id)
            try:
                crud.set_run_status_final(db, run_id, "failed", {"ok": False, "error": "Erro durante execução"})
            except Exception:
                log.exception("process_run: falha ao setar status final após exceção para run %s", run_id)
    finally:
        db.close()
