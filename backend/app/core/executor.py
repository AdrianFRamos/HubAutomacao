from __future__ import annotations
import importlib
import json
import traceback
import inspect
from dataclasses import dataclass
from subprocess import Popen, PIPE, STDOUT, TimeoutExpired
from typing import Any, Dict, Optional

import importlib
import traceback
from datetime import datetime
from app.db.database import SessionLocal
from app.db.models import Run, Automation

@dataclass
class ExecResult:
    ok: bool
    exit_code: Optional[int]
    stdout: str
    stderr: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]

def _json_serializable_or_none(value: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("A função de automação deve retornar um dict (JSON-serializable).")
    try:
        json.dumps(value)
    except Exception as e:
        raise TypeError(f"Retorno não é JSON-serializable: {e}")
    return value

def _import_and_call(module_path: str, func_name: str, payload: dict | None):
    mod = importlib.import_module(module_path)
    func = getattr(mod, func_name)
    payload = payload or {}
    
    try:
        return func(payload)
    except TypeError as e:
        if "positional arguments but" in str(e) or "takes 0 positional arguments" in str(e):
            return func()
        else:
            raise

def _run_external(command: str, timeout: int, cwd: Optional[str] = None) -> ExecResult:
    try:
        proc = Popen(command, shell=True, stdout=PIPE, stderr=STDOUT, cwd=cwd, text=True)
        try:
            out, _ = proc.communicate(timeout=timeout)
            ok = proc.returncode == 0
            return ExecResult(
                ok=ok,
                exit_code=proc.returncode,
                stdout=out or "",
                stderr="" if ok else (out or ""),
                result=None,
                error=None if ok else f"Processo retornou código {proc.returncode}",
            )
        except TimeoutExpired:
            proc.kill()
            out, _ = proc.communicate()
            return ExecResult(
                ok=False,
                exit_code=None,
                stdout=out or "",
                stderr=(out or "") + "\nTimeoutExpired: processo excedeu o tempo limite",
                result=None,
                error="TimeoutExpired",
            )
    except Exception as e:
        return ExecResult(
            ok=False,
            exit_code=None,
            stdout="",
            stderr=traceback.format_exc(),
            result=None,
            error=str(e),
        )

def run_sync(
    *,
    module_path: Optional[str] = None,
    func_name: Optional[str] = None,
    command: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    timeout_sec: int = 900,
    cwd: Optional[str] = None,
) -> ExecResult:
    payload = payload or {}
    if command:
        return _run_external(command, timeout=timeout_sec, cwd=cwd)
    if not module_path or not func_name:
        return ExecResult(
            ok=False,
            exit_code=None,
            stdout="",
            stderr="",
            result=None,
            error="Informe command OU (module_path + func_name).",
        )
    try:
        ret = _import_and_call(module_path, func_name, payload or {})
        if ret is None:
            return ExecResult(ok=True, exit_code=0, stdout="", stderr="", result=None, error=None)
        if isinstance(ret, dict):
            ok = bool(ret.get("ok", True))
            return ExecResult(ok=ok, exit_code=0, stdout="", stderr="", result=ret, error=None if ok else ret.get("error"))
        return ExecResult(ok=True, exit_code=0, stdout="", stderr="", result={"data": ret}, error=None)
    except Exception as e:
        return ExecResult(
            ok=False,
            exit_code=None,
            stdout="",
            stderr=traceback.format_exc(),
            result=None,
            error=str(e),
        )

