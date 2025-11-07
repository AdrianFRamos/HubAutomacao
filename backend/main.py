import sys
import json
import argparse
import secrets
import hashlib
import traceback
from typing import Any, Dict, Optional
from pathlib import Path
import importlib
import secrets as _secrets

BASE_DIR = Path(__file__).resolve().parent
USERS_FILE = BASE_DIR / "users" / "users.json"

# --------- UTIL ---------
def _print_json(payload: Dict[str, Any], exitcode: int = 0) -> None:
    sys.stdout.write(json.dumps(payload, ensure_ascii=False))
    sys.stdout.flush()
    sys.exit(exitcode)

def _load_users() -> list[dict]:
    try:
        if not USERS_FILE.exists():
            return []
        with USERS_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            return []
    except json.JSONDecodeError as e:
        raise RuntimeError(f"users.json inválido: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Erro ao ler users.json: {e}") from e

def _verify_password(raw: str, record: dict) -> bool:
    if record is None:
        return False
    pwd_hash = record.get("password_hash")
    if pwd_hash:
        try:
            algo, hexd = pwd_hash.split(":", 1)
        except Exception:
            return False
        if algo != "sha256":
            return False
        raw_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        return _secrets.compare_digest(raw_hash, hexd)
    pwd_plain = record.get("password")
    if pwd_plain is not None:
        return _secrets.compare_digest(raw, str(pwd_plain))

    return False

# --------- AUTH ---------
def cmd_login(username: str, password: str):
    try:
        users = _load_users()
    except Exception as e:
        _print_json({"ok": False, "message": f"Erro ao carregar usuários: {e}"}, exitcode=1)
    uname_norm = username.strip().lower()
    for u in users:
        if str(u.get("username", "")).strip().lower() == uname_norm and _verify_password(password, u):
            token = "py-" + secrets.token_urlsafe(24)
            _print_json({"ok": True, "token": token, "username": u.get("username")})
    _print_json({"ok": False, "message": "Usuário ou senha inválidos."}, exitcode=1)

# --------- AUTOMACOES ---------
def _run_comercial_dashboard() -> bool:
    try:
        mod = importlib.import_module("modules.comercial.dashboard.run_comercial")
        fn = getattr(mod, "main", None) or getattr(mod, "run", None)
        if not fn:
            raise RuntimeError("Função 'main' ou 'run' não encontrada no módulo comercial.dashboard.run_comercial")
        res = fn() if callable(fn) else None
        return True
    except Exception as e:
        tb = traceback.format_exc()
        _print_json({"ok": False, "message": f"Falha na automação Comercial: {e}", "traceback": tb}, exitcode=2)
        return False 

AUTOMATION_MAP = {
    "comercial_dashboard": _run_comercial_dashboard,
}

def cmd_list_automations():
    _print_json({"ok": True, "automations": list(AUTOMATION_MAP.keys())})

def cmd_run_automation(name: str):
    fn = AUTOMATION_MAP.get(name)
    if not fn:
        _print_json({"ok": False, "message": f"Automação '{name}' não encontrada."}, exitcode=2)
    ok = fn()
    if ok:
        _print_json({"ok": True, "name": name, "message": "Automação executada com sucesso."})
    else:
        _print_json({"ok": False, "name": name, "message": "Automação retornou falha."}, exitcode=3)

# --------- CLI ---------
def main(argv: Optional[list[str]] = None):
    parser = argparse.ArgumentParser(prog="backend", description="Backend CLI (IPC-friendly)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_login = sub.add_parser("login", help="Autentica usuário")
    p_login.add_argument("username")
    p_login.add_argument("password")
    p_run = sub.add_parser("run", help="Executa automação")
    p_run.add_argument("name", help=f"Nome em {list(AUTOMATION_MAP.keys())}")
    sub.add_parser("list", help="Lista automações disponíveis")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "login":
            return cmd_login(args.username, args.password)
        elif args.cmd == "run":
            return cmd_run_automation(args.name)
        elif args.cmd == "list":
            return cmd_list_automations()
    except SystemExit:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        _print_json({"ok": False, "message": f"Erro interno: {e}", "traceback": tb}, exitcode=99)

if __name__ == "__main__":
    main()
