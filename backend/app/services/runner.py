from importlib import import_module
from typing import Any, Dict, Optional
from uuid import UUID
import asyncio
import traceback
from sqlalchemy.orm import Session
from app.db import crud, models
from app.utils.workspace import user_workspace

def _safe_payload(base: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return dict(base) if isinstance(base, dict) else {}

def _format_error(e: Exception) -> Dict[str, Any]:
    return {
        "ok": False,
        "error": f"{type(e).__name__}: {e}",
        "traceback": traceback.format_exc(),
    }

def execute_run(
    db: Session,
    run_id: UUID,
    automation: models.Automation,
    user_id: UUID,
    payload: Optional[Dict[str, Any]] = None,
) -> bool:
    crud.set_run_status_running(db, run_id)
    try:
        ws = user_workspace(user_id) if user_id else None
        default_data = _safe_payload(getattr(automation, "default_payload", None))
        request_data = _safe_payload(payload)
        data = {**default_data, **request_data}
        if ws:
            data["_workspace"] = ws
        if user_id:
            data["_user_id"] = str(user_id)
        if getattr(automation, "id", None):
            data["_automation_id"] = str(automation.id)
        try:
            mod = import_module(automation.module_path)
        except Exception as e:
            crud.set_run_status_final(db, run_id, "failed", _format_error(e))
            return False
        if not hasattr(mod, automation.func_name):
            crud.set_run_status_final(
                db,
                run_id,
                "failed",
                {"ok": False, "error": f"Função '{automation.func_name}' não encontrada no módulo '{automation.module_path}'"},
            )
            return False
        fn = getattr(mod, automation.func_name)
        try:
            if asyncio.iscoroutinefunction(fn):
                ret = asyncio.run(fn(data))
            else:
                ret = fn(data)
        except TypeError as e:
            if "positional arguments but" in str(e) or "takes 0 positional arguments" in str(e):
                if asyncio.iscoroutinefunction(fn):
                    ret = asyncio.run(fn())
                else:
                    ret = fn()
            else:
                raise
        if ret is None:
            result = {"ok": True}
        elif isinstance(ret, dict):
            result = ret
        else:
            result = {"ok": True, "data": ret}
        crud.set_run_status_final(db, run_id, "success", result)
        return True
    except Exception as e:
        crud.set_run_status_final(db, run_id, "failed", _format_error(e))
        return False
