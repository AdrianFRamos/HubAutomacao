import os
from uuid import UUID
from app.core.config import settings

def user_workspace(user_id: UUID) -> str:
    root = getattr(settings, "WORKSPACE_ROOT", None)
    if not root:
        raise ValueError("WORKSPACE_ROOT não está definido nas configurações.")
    path = os.path.join(root, str(user_id))
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"Falha ao criar diretório de trabalho: {e}")
    return os.path.abspath(path)
