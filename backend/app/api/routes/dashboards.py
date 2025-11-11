from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.database import get_db
from app.db import crud, models
from app.api.deps import get_current_user
import uuid

router = APIRouter(prefix="/dashboards", tags=["dashboards"])

# --------- Schemas ---------
class DashboardConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    menu_path: List[str] = Field(..., min_items=1)
    search_text: Optional[str] = None
    search_image: Optional[str] = None
    click_coords: Optional[dict] = None
    menu_coords: Optional[dict] = None
    screenshot_region: List[int] = Field(..., min_items=4, max_items=4)
    has_period_selector: bool = False
    available_periodicities: List[str] = Field(default_factory=list)
    is_active: bool = True

class DashboardConfigUpdate(BaseModel):
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    menu_path: Optional[List[str]] = None
    search_text: Optional[str] = None
    search_image: Optional[str] = None
    click_coords: Optional[dict] = None
    menu_coords: Optional[dict] = None
    screenshot_region: Optional[List[int]] = Field(None, min_items=4, max_items=4)
    has_period_selector: Optional[bool] = None
    available_periodicities: Optional[List[str]] = None
    is_active: Optional[bool] = None

class DashboardConfigResponse(BaseModel):
    id: str
    name: str
    display_name: str
    description: Optional[str]
    menu_path: List[str]
    search_text: Optional[str]
    search_image: Optional[str]
    click_coords: Optional[dict]
    menu_coords: Optional[dict]
    screenshot_region: List[int]
    has_period_selector: bool
    available_periodicities: List[str]
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

# --------- Endpoints ---------
@router.get("", response_model=List[DashboardConfigResponse])
def list_dashboards(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Lista todas as configurações de dashboards
    """
    dashboards = crud.list_dashboard_configs(db, is_active=is_active, skip=skip, limit=limit)
    
    return [
        DashboardConfigResponse(
            id=str(d.id),
            name=d.name,
            display_name=d.display_name,
            description=d.description,
            menu_path=d.menu_path,
            search_text=d.search_text,
            search_image=d.search_image,
            click_coords=d.click_coords,
            menu_coords=d.menu_coords,
            screenshot_region=d.screenshot_region,
            has_period_selector=d.has_period_selector,
            available_periodicities=d.available_periodicities,
            is_active=d.is_active,
            created_at=d.created_at.isoformat(),
            updated_at=d.updated_at.isoformat()
        )
        for d in dashboards
    ]

@router.get("/{dashboard_id}", response_model=DashboardConfigResponse)
def get_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtém configuração de um dashboard específico
    """
    dashboard = crud.get_dashboard_config(db, dashboard_id)
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard não encontrado"
        )
    
    return DashboardConfigResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        display_name=dashboard.display_name,
        description=dashboard.description,
        menu_path=dashboard.menu_path,
        search_text=dashboard.search_text,
        search_image=dashboard.search_image,
        click_coords=dashboard.click_coords,
        menu_coords=dashboard.menu_coords,
        screenshot_region=dashboard.screenshot_region,
        has_period_selector=dashboard.has_period_selector,
        available_periodicities=dashboard.available_periodicities,
        is_active=dashboard.is_active,
        created_at=dashboard.created_at.isoformat(),
        updated_at=dashboard.updated_at.isoformat()
    )

@router.get("/by-name/{name}", response_model=DashboardConfigResponse)
def get_dashboard_by_name(
    name: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Obtém configuração de um dashboard por nome
    """
    dashboard = crud.get_dashboard_config_by_name(db, name)
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dashboard '{name}' não encontrado"
        )
    
    return DashboardConfigResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        display_name=dashboard.display_name,
        description=dashboard.description,
        menu_path=dashboard.menu_path,
        search_text=dashboard.search_text,
        search_image=dashboard.search_image,
        click_coords=dashboard.click_coords,
        menu_coords=dashboard.menu_coords,
        screenshot_region=dashboard.screenshot_region,
        has_period_selector=dashboard.has_period_selector,
        available_periodicities=dashboard.available_periodicities,
        is_active=dashboard.is_active,
        created_at=dashboard.created_at.isoformat(),
        updated_at=dashboard.updated_at.isoformat()
    )

@router.post("", response_model=DashboardConfigResponse, status_code=status.HTTP_201_CREATED)
def create_dashboard(
    data: DashboardConfigCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Cria nova configuração de dashboard
    Requer permissão de admin
    """
    # Verifica se usuário é admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem criar dashboards"
        )
    
    # Verifica se já existe dashboard com mesmo nome
    existing = crud.get_dashboard_config_by_name(db, data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dashboard com nome '{data.name}' já existe"
        )
    
    dashboard = crud.create_dashboard_config(
        db=db,
        name=data.name,
        display_name=data.display_name,
        description=data.description,
        menu_path=data.menu_path,
        search_text=data.search_text,
        search_image=data.search_image,
        click_coords=data.click_coords,
        menu_coords=data.menu_coords,
        screenshot_region=data.screenshot_region,
        has_period_selector=data.has_period_selector,
        available_periodicities=data.available_periodicities,
        is_active=data.is_active
    )
    
    return DashboardConfigResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        display_name=dashboard.display_name,
        description=dashboard.description,
        menu_path=dashboard.menu_path,
        search_text=dashboard.search_text,
        search_image=dashboard.search_image,
        click_coords=dashboard.click_coords,
        menu_coords=dashboard.menu_coords,
        screenshot_region=dashboard.screenshot_region,
        has_period_selector=dashboard.has_period_selector,
        available_periodicities=dashboard.available_periodicities,
        is_active=dashboard.is_active,
        created_at=dashboard.created_at.isoformat(),
        updated_at=dashboard.updated_at.isoformat()
    )

@router.put("/{dashboard_id}", response_model=DashboardConfigResponse)
def update_dashboard(
    dashboard_id: str,
    data: DashboardConfigUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Atualiza configuração de dashboard
    Requer permissão de admin
    """
    # Verifica se usuário é admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem atualizar dashboards"
        )
    
    # Atualiza apenas campos fornecidos
    update_data = data.dict(exclude_unset=True)
    
    dashboard = crud.update_dashboard_config(db, dashboard_id, **update_data)
    
    if not dashboard:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard não encontrado"
        )
    
    return DashboardConfigResponse(
        id=str(dashboard.id),
        name=dashboard.name,
        display_name=dashboard.display_name,
        description=dashboard.description,
        menu_path=dashboard.menu_path,
        search_text=dashboard.search_text,
        search_image=dashboard.search_image,
        click_coords=dashboard.click_coords,
        menu_coords=dashboard.menu_coords,
        screenshot_region=dashboard.screenshot_region,
        has_period_selector=dashboard.has_period_selector,
        available_periodicities=dashboard.available_periodicities,
        is_active=dashboard.is_active,
        created_at=dashboard.created_at.isoformat(),
        updated_at=dashboard.updated_at.isoformat()
    )

@router.delete("/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(
    dashboard_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Remove configuração de dashboard
    Requer permissão de admin
    """
    # Verifica se usuário é admin
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas administradores podem remover dashboards"
        )
    
    success = crud.delete_dashboard_config(db, dashboard_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dashboard não encontrado"
        )
    
    return None
