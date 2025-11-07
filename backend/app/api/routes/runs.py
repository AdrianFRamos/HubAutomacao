from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db import crud, models
from app.api.deps import get_current_user
from app.services.queue import queue

router = APIRouter(prefix="/runs", tags=["runs"])

class RunIn(BaseModel):
    automation_id: UUID
    payload: Optional[dict] = None

@router.post("")
def create_run(
    data: RunIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    auto = crud.get_automation_by_id(db, str(data.automation_id))
    if not auto or not getattr(auto, "enabled", True):
        raise HTTPException(status_code=404, detail="Automação não encontrada ou desabilitada")
    if not crud.user_can_access_automation(db, current.id, auto):
        raise HTTPException(status_code=403, detail="Solicitação Recusada")
    run = crud.create_run(
        db,
        automation_id=auto.id,          
        user_id=current.id,            
        status="queued",
        payload=data.payload or {},
        started_at=None,
    )
    queue.enqueue(
        "app.worker.process_run",
        {"run_id": str(run.id), "user_id": str(current.id)},
    )
    return run

@router.get("")
def list_runs(
    automation_id: Optional[UUID] = None,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    return crud.list_runs_for_user(db, current.id, automation_id)
