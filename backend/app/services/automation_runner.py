from sqlalchemy.orm import Session
from app.core.automation_loader import run_module
from app.db import models

def build_ctx(db: Session, automation: models.Automation):
    return {
        "db": db,
        "logger": None,
        "secrets": {},      
    }

def run_automation(db: Session, automation: models.Automation, payload: dict | None):
    ctx = build_ctx(db, automation)
    return run_module(automation.module_path, ctx, **(payload or {}))
