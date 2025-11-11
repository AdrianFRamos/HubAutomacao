from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
import enum
from sqlalchemy import (String,ForeignKey,DateTime,Text,Boolean,Integer,func,UniqueConstraint,)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base

def uuid4() -> uuid.UUID:
    return uuid.uuid4()

# --------- Usuários e Setores ---------
class RoleEnum(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    operator = "operator"

class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="user", cascade="all, delete-orphan"
    )

class Sector(Base):
    __tablename__ = "sector"
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    members: Mapped[list["SectorMember"]] = relationship(
        "SectorMember", back_populates="sector", cascade="all, delete-orphan"
    )

class SectorMember(Base):
    __tablename__ = "sector_members"
    sector_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("sector.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String, nullable=False, default="member")
    sector: Mapped["Sector"] = relationship("Sector", back_populates="members")
    user: Mapped["User"] = relationship("User")


# --------- Automações ---------
class Automation(Base):
    __tablename__ = "automations"
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    module_path: Mapped[str] = mapped_column(String, nullable=False)
    func_name: Mapped[str] = mapped_column(String, nullable=False)
    owner_type: Mapped[str] = mapped_column(String, nullable=False, default="user")
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    default_payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict) # Payload padrão para a automação
    config_schema: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict) # Schema para o formulário de configuração no frontend
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    # Relacionamento para obter o nome do setor quando owner_type é 'sector'
    sector: Mapped[Optional["Sector"]] = relationship(
        "Sector",
        primaryjoin="and_(Automation.owner_id == Sector.id, Automation.owner_type == 'sector')",
        foreign_keys="[Automation.owner_id]",
        viewonly=True,
    )

    runs: Mapped[list["Run"]] = relationship(
        "Run", back_populates="automation", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["AutomationOperator"]] = relationship(
        "AutomationOperator",
        back_populates="automation",
        cascade="all, delete-orphan",
    )

class AutomationOperator(Base):
    __tablename__ = "automation_operators"
    __table_args__ = (
        UniqueConstraint("automation_id", "user_id", name="uq_automation_user"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    automation: Mapped["Automation"] = relationship("Automation", back_populates="assignments")
    user: Mapped["User"] = relationship("User")


# --------- Execuções ---------
class Run(Base):
    __tablename__ = "runs"
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="queued")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    user: Mapped[Optional["User"]] = relationship("User", back_populates="runs")
    automation: Mapped["Automation"] = relationship("Automation", back_populates="runs")

# --------- Segredos ---------
class Secret(Base):
    __tablename__ = "secrets"
    __table_args__ = (
        UniqueConstraint("owner_type", "owner_id", "key", name="ux_secrets_owner_key"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    owner_type: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    key: Mapped[str] = mapped_column(String, nullable=False)
    value_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

# --------- Agendamentos ---------
class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), nullable=False
    )
    owner_type: Mapped[str] = mapped_column(String, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now()
    )
    days_of_week: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    hour: Mapped[Optional[int]] = mapped_column(Integer)
    minute: Mapped[Optional[int]] = mapped_column(Integer)


# --------- Dashboard Configs ---------
class DashboardConfig(Base):
    """
    Configuração de dashboards do sistema DELPHOS.BI
    Armazena informações de navegação, busca e captura de screenshots
    """
    __tablename__ = "dashboard_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(
        String(200), nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Navegação no menu
    menu_path: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="Caminho no menu hierárquico, ex: ['Dashboards', 'Geradores', 'Planilhas']"
    )
    
    # Busca visual
    search_text: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="Texto para buscar na lista de dashboards"
    )
    search_image: Mapped[Optional[str]] = mapped_column(
        String(500),
        comment="Nome do arquivo de imagem de referência"
    )
    
    # Coordenadas (fallback)
    click_coords: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Coordenadas de clique {x, y}"
    )
    menu_coords: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        comment="Coordenadas dos itens de menu {0: {x, y}, 1: {x, y}, ...}"
    )
    
    # Screenshot
    screenshot_region: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=lambda: [0, 40, 1920, 1000],
        comment="Região de captura [x, y, largura, altura]"
    )
    
    # Configuração de período
    has_period_selector: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
        comment="Se o dashboard possui seletor de período"
    )
    available_periodicities: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=list,
        comment="Periodicidades disponíveis: ['diario', 'mensal', 'anual']"
    )
    
    # Status
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
