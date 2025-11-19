from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db import crud

router = APIRouter(prefix="/sectors", tags=["sectors"])

@router.get("/")
def list_sectors(db: Session = Depends(get_db)):
    items = crud.list_sectors(db)
    return [{"id": str(s.id), "name": s.name} for s in items]
