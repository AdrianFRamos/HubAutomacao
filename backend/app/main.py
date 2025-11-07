from app.api.routes import sectors
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.automations import router as automations_router
from app.api.routes.runs import router as runs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.runs_sync import router as runs_sync_router
from app.api.routes.secrets import router as secrets_router
from app.api.routes.schedules import router as schedules_router
import asyncio
import logging
from app.db.session import SessionLocal
from app.db import crud
from app.services.queue import queue
from app.core.config import settings

log = logging.getLogger("automacao")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Automacao_API", version="1.0.0")

_allowed = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "capacitor://localhost",
    "tauri://localhost",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", _allowed),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(auth_router)
app.include_router(automations_router)
app.include_router(sectors.router)
app.include_router(runs_router)
app.include_router(runs_sync_router)
app.include_router(secrets_router)
app.include_router(schedules_router)

_scheduler_task: asyncio.Task | None = None
_SCHEDULER_INTERVAL = getattr(settings, "SCHEDULER_INTERVAL", 15)

async def _poll_schedules_loop():
    log.info("Scheduler loop iniciado (interval=%ss)", _SCHEDULER_INTERVAL)
    while True:
        try:
            await asyncio.sleep(_SCHEDULER_INTERVAL)
            db = SessionLocal()
            try:
                due = crud.find_due_schedules(db, limit=50)
                if due:
                    log.info("Schedules vencidas: %d", len(due))
                for sc in due:
                    try:
                        run = crud.create_run(
                            db,
                            automation_id=sc.automation_id,
                            user_id=None,
                            status="queued",
                            payload=None,
                        )
                        user_id_str = ""
                        queue.enqueue(
                            "app.services.worker.process_run",
                            {"run_id": str(run.id), "user_id": user_id_str},
                        )
                        crud.mark_schedule_triggered(db, sc)
                        log.info("Enfileirado run=%s para schedule=%s", run.id, sc.id)
                    except Exception:
                        log.exception("Erro ao enfileirar schedule=%s", getattr(sc, "id", "<unknown>"))
            except Exception:
                log.exception("Erro ao buscar schedules vencidas")
            finally:
                db.close()
        except asyncio.CancelledError:
            log.info("Scheduler cancelado")
            raise
        except Exception:
            log.exception("Erro inesperado no loop do scheduler")

@app.on_event("startup")
async def on_startup():
    global _scheduler_task
    if _scheduler_task is None:
        _scheduler_task = asyncio.create_task(_poll_schedules_loop())
        log.info("Scheduler task criada")

@app.on_event("shutdown")
async def on_shutdown():
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        try:
            await _scheduler_task
        except asyncio.CancelledError:
            log.info("Scheduler task finalizada")
        _scheduler_task = None
