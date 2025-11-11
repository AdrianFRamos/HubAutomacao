from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, Literal
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.db.database import get_db
from app.db import crud, models
from app.core.security import encrypt_secret, decrypt_secret

router = APIRouter(prefix="/secrets", tags=["secrets"])

class SecretIn(BaseModel):
    owner_type: Literal["user", "sector"]
    owner_id: str
    key: str
    value: str

class SecretOut(BaseModel):
    id: str
    owner_type: Literal["user", "sector"]
    owner_id: str
    key: str
    created_at: str

def _ensure_access(current: models.User, owner_type: str, owner_id: str, db: Session):
    if current.role == "admin":
        return
    if owner_type == "user":
        if str(owner_id) != str(current.id):
            raise HTTPException(status_code=403, detail="Sem permissão")
    else:
        sector_ids = {str(s) for s in crud.get_user_sector_ids(db, current.id)}
        roles_map = {str(k): v for k, v in (crud.get_user_roles_by_sector(db, current.id) or {}).items()}
        if str(owner_id) not in sector_ids or (roles_map.get(str(owner_id)) or "").lower() != "manager":
            raise HTTPException(status_code=403, detail="Sem permissão")

@router.post("", response_model=SecretOut)
def upsert(
    body: SecretIn,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    _ensure_access(current, body.owner_type, body.owner_id, db)
    ct = encrypt_secret(body.value)
    s = crud.upsert_secret(
        db,
        owner_type=body.owner_type,
        owner_id=str(body.owner_id),
        key=body.key,
        value_ciphertext=ct,
    )
    return SecretOut(
        id=str(s.id),
        owner_type=s.owner_type,
        owner_id=str(s.owner_id),
        key=s.key,
        created_at=str(s.created_at),
    )

@router.get("", response_model=list[SecretOut])
def list_for_owner(
    owner_type: Literal["user", "sector"] = Query(...),
    owner_id: str = Query(...),
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    _ensure_access(current, owner_type, owner_id, db)
    items = crud.list_secrets(db, owner_type=owner_type, owner_id=str(owner_id))
    return [
        SecretOut(
            id=str(s.id),
            owner_type=s.owner_type,
            owner_id=str(s.owner_id),
            key=s.key,
            created_at=str(s.created_at),
        )
        for s in items
    ]

class SecretValueOut(BaseModel):
    id: str
    key: str
    value: str

@router.get("/{secret_id}", response_model=SecretValueOut)
def read_secret(
    secret_id: str,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    s = crud.get_secret(db, secret_id)
    if not s:
        raise HTTPException(status_code=404, detail="Secret não encontrado")
    _ensure_access(current, s.owner_type, s.owner_id, db)
    value = decrypt_secret(s.value_ciphertext)

    return SecretValueOut(id=str(s.id), key=s.key, value=value)

@router.delete("/{secret_id}", status_code=204)
def delete_secret(
    secret_id: str,
    db: Session = Depends(get_db),
    current: models.User = Depends(get_current_user),
):
    s = crud.get_secret(db, secret_id)
    if not s:
        return
    _ensure_access(current, s.owner_type, s.owner_id, db)
    crud.delete_secret(db, secret_id)
    return
