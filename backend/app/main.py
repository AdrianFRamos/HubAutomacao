import asyncio
import logging
import json
from datetime import datetime
from enum import Enum

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# from app.scheduler import register_jobs, shutdown_scheduler, start_scheduler # Removido, pois a lógica de agendamento será desacoplada
# from app.db.database import SessionLocal # Removido, pois a lógica de agendamento será desacoplada
# from app.db import crud # Removido, pois a lógica de agendamento será desacoplada
# from app.services.queue import queue # Removido, pois a lógica de agendamento será desacoplada
from app.core.config import settings

# --- Configuração de Logging Estruturado ---
log = logging.getLogger("automacao")

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
            "process": record.process,
            "thread": record.thread,
        }
        # Adiciona campos extras (como correlation_id, se existirem)
        for key, value in record.__dict__.items():
            if key not in log_record and not key.startswith('_') and key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename', 'funcName', 'levelname', 'levelno', 'lineno', 'module', 'msecs', 'message', 'msg', 'name', 'pathname', 'process', 'processName', 'relativeCreated', 'thread', 'threadName'):
                log_record[key] = value
                
        return json.dumps(log_record, default=str)

# Configuração básica do logging
logging.basicConfig(
    level=logging.INFO, # Usando INFO como padrão, mas o ideal seria ler de settings
    handlers=[logging.StreamHandler()],
)

# Configura o logger principal para usar o formatador JSON
for handler in logging.getLogger().handlers:
    handler.setFormatter(JsonFormatter())

log.info("Iniciando aplicação", extra={"port": settings.APP_PORT, "env": "development"})
# -------------------------------------------

app = FastAPI(title="Automacao_API", version="1.0.0", redirect_slashes=False)

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
    expose_headers=["*"],
)

# Importação das Rotas
from app.api.routes.automations import router as automations_router
from app.api.routes.runs import router as runs_router
from app.api.routes.auth import router as auth_router
from app.api.routes.secrets import router as secrets_router
from app.api.routes.schedules import router as schedules_router
from app.api.routes.sectors import router as sectors_router
from app.api.routes.dashboards import router as dashboards_router 

@app.get("/health")
def health():
    return {"ok": True}

app.include_router(auth_router)
app.include_router(automations_router)
app.include_router(runs_router)
app.include_router(secrets_router)
app.include_router(schedules_router)
app.include_router(sectors_router)
app.include_router(dashboards_router)

@app.on_event("startup")
async def on_startup():
    log.info("API iniciada com sucesso.")

@app.on_event("shutdown")
async def on_shutdown():
    log.info("API encerrada.")
