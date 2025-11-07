from fastapi import Depends, HTTPException, status
from app.api.deps import get_current_user
from app.db import models

def require_role(*roles: str):
    def _wrap(current: models.User = Depends(get_current_user)) -> models.User:
        user_role = (current.role or "").lower()
        allowed = [r.lower() for r in roles]

        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: requer uma das roles {roles}",
            )
        return current
    return _wrap
