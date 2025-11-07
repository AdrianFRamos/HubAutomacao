import importlib
import inspect
from types import ModuleType

def load_callable(module_path: str):
    if ":" in module_path:
        mod_name, func_name = module_path.split(":", 1)
    else:
        mod_name, func_name = module_path, "main"
    mod: ModuleType = importlib.import_module(mod_name)
    fn = getattr(mod, func_name, None)
    if not callable(fn):
        raise RuntimeError(f"'{func_name}' não é callable em {mod_name}")
    return fn

def smart_call(fn, ctx: dict | None = None, payload: dict | None = None):
    ctx = ctx or {}
    payload = payload or {}
    sig = inspect.signature(fn)
    params = sig.parameters
    if len(params) == 0:
        return fn()
    if all(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
        return fn(**payload)
    if len(params) == 1:
        return fn(ctx)
    return fn(ctx, **payload)

def run_module(module_path: str, ctx: dict | None = None, **payload):
    fn = load_callable(module_path)
    return smart_call(fn, ctx=ctx, payload=payload)
