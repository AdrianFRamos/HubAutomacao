from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import (String,ForeignKey,DateTime,Text,Boolean,Integer,func,UniqueConstraint,)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

def uuid4() -> uuid.UUID:
    return uuid.uuid4()

# --------- Usuários e Setores ---------
class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False, index=True, unique=True)
    password: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False, default="operator")
    is_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
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
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
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
    type: Mapped[str] = mapped_column(String, nullable=False)  # 'once' | 'interval'
    run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    interval_seconds: Mapped[Optional[int]] = mapped_column(Integer)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
