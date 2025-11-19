from datetime import datetime, timezone
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import crud, models
from app.services.queue import queue
from app.core.executor import run_sync 

router = APIRouter(prefix="/runs", tags=["runs"])

class RunMode(str, Enum):
    ASYNC = "async"
    SYNC = "sync"

class RunRequest(BaseModel):
    automation_id: str = Field(..., description="UUID ou nome da automação a executar")
    payload: Optional[Dict[str, Any]] = Field(default_factory=dict)
    mode: RunMode = Field(RunMode.ASYNC, description="Modo de execução: 'async' (fila) ou 'sync' (imediato)")
    timeout_sec: int = Field(default=900, ge=10, le=7200, description="Timeout da execução em segundos (apenas para mode='sync')")

@router.post("")
def create_run(
    data: RunRequest,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    auto_id_lookup = None
    try:
        auto_id_lookup = UUID(data.automation_id)
    except ValueError:
        auto_id_lookup = data.automation_id
        
    automation = crud.get_automation_by_id_or_name(db, auto_id_lookup)
    
    if not automation or not getattr(automation, "enabled", True):
        raise HTTPException(status_code=404, detail="Automação não encontrada ou desabilitada.")
    
    allowed = crud.user_can_execute_automation(db, current.id, automation)
    if not allowed:
        raise HTTPException(status_code=403, detail="Sem permissão para executar essa automação.")

    run = crud.create_run(
        db,
        automation_id=automation.id,          
        user_id=current.id,            
        status="queued" if data.mode == RunMode.ASYNC else "running",
        payload=data.payload or {},
        started_at=None if data.mode == RunMode.ASYNC else datetime.now(timezone.utc),
    )
    
    if data.mode == RunMode.ASYNC:
        queue.enqueue(
            "app.worker.process_run",
            {"run_id": str(run.id), "user_id": str(current.id)},
        )
        return run
    
    elif data.mode == RunMode.SYNC:
        module_path = automation.module_path
        func_name = automation.func_name
        command = None
        
        if module_path and isinstance(module_path, str) and module_path.startswith("shell:"):
            command = module_path.replace("shell:", "", 1).strip()
            module_path = None
            func_name = None
        elif isinstance(module_path, str):
            module_path = module_path.strip()
            
        try:
            result = run_sync(
                module_path=module_path,
                func_name=func_name,
                command=command,
                payload=data.payload or {},
                timeout_sec=data.timeout_sec,
                cwd=None,
            )
            
            status_val = "success" if getattr(result, "ok", False) else "failed"
            stdout_str = result.stdout if isinstance(result.stdout, str) or result.stdout is None else str(result.stdout)
            stderr_str = result.stderr if isinstance(result.stderr, str) or result.stderr is None else str(result.stderr)
            
            crud.finish_run(
                db,
                run_id=run.id,
                status=status_val,
                finished_at=datetime.now(timezone.utc),
                result={
                    "ok": bool(getattr(result, "ok", False)),
                    "exit_code": getattr(result, "exit_code", None),
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "payload_result": getattr(result, "result", None),
                    "error": getattr(result, "error", None),
                },
            )
            
            if not getattr(result, "ok", False):
                raise HTTPException(
                    status_code=500,
                    detail={
                        "message": "Execução falhou",
                        "error": getattr(result, "error", None),
                        "stderr": (stderr_str or "")[-2000:],
                    },
                )
            
            return {
                "message": "Execução concluída",
                "run_id": str(run.id),
                "ok": True,
                "exit_code": getattr(result, "exit_code", None),
                "stdout": stdout_str,
                "stderr": stderr_str,
                "result": getattr(result, "result", None),
            }
            
        except HTTPException:
            raise
        except Exception as e:
            crud.finish_run(
                db,
                run_id=run.id,
                status="failed",
                finished_at=datetime.now(timezone.utc),
                result={
                    "ok": False,
                    "exit_code": None,
                    "stdout": None,
                    "stderr": None,
                    "payload_result": None,
                    "error": f"{type(e).__name__}: {e}",
                },
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "message": "Erro inesperado durante a execução",
                    "error": f"{type(e).__name__}: {e}",
                },
            )

@router.get("")
def list_runs(
    automation_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    return crud.list_runs_for_user(db, current.id, automation_id)
