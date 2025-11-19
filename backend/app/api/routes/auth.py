from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from typing import Optional, Literal
from app.db.database import get_db
from app.db import crud, models
from app.core.security import hash_password, verify_password, create_access_token
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterIn(BaseModel):
    name: str
    email: EmailStr
    password: str
    sector_id: Optional[UUID] = None
    role: Optional[Literal["admin", "manager", "operator"]] = None

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    normalized_email = data.email.lower()
    exists = crud.get_user_by_email(db, normalized_email)
    if exists:
        raise HTTPException(status_code=409, detail="E-mail já cadastrado")
    role = data.role or "operator"
    pwd_hash = hash_password(data.password)

    # Validação: setor obrigatório para manager/operator
    if role in ("manager", "operator"):
        if not data.sector_id:
            raise HTTPException(status_code=422, detail="Setor é obrigatório para Manager ou Operator")
        sector = db.query(models.Sector).filter(models.Sector.id == data.sector_id).first()
        if not sector:
            raise HTTPException(status_code=404, detail="Setor não encontrado")
    # Para admin, ignora sector_id

    user = crud.create_user(db, data.name, normalized_email, pwd_hash, role=role)

    if role in ("manager", "operator"):
        sector_member = models.SectorMember(
            sector_id=data.sector_id,
            user_id=user.id,
            role=role
        )
        db.add(sector_member)
        db.commit()
        db.refresh(sector_member)

    return {"ok": True, "user_id": str(user.id)}

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = crud.get_user_by_email(db, data.email.lower())
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Acesso Não Autorizado"
        )
    token = create_access_token({"sub": str(user.id)})
    return TokenOut(access_token=token)

class MeOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: Literal["admin", "manager", "operator"]

@router.get("/me", response_model=MeOut)
def me(current: models.User = Depends(get_current_user)):
    return MeOut(
        id=str(current.id),
        name=current.name,
        email=current.email,
        role=(current.role or "operator"),
    )
