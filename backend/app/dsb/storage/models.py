from __future__ import annotations
"""
DSB Storage Models — SQLAlchemy ORM модели для всех 7 таблиц.
Схема полная — готова под все 8 учений, хотя на старте активно только одно.

Поле source_system отличает данные разных учений в одних таблицах.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Float, Integer,
    String, Text, ForeignKey, func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
    _VECTOR_AVAILABLE = True
except ImportError:
    _VECTOR_AVAILABLE = False
    Vector = None  # type: ignore

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Таблица 0: Основная таблица портрета ────────────────────────────────────
class DigitalPortrait(Base):
    __tablename__ = "dsb_digital_portraits"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    birth_data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    status: Mapped[str] = mapped_column(String(32), default="generating")
    # status: generating | ready | error

    version: Mapped[int] = mapped_column(Integer, default=1)
    systems_used: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    # ['western_astrology'] на старте

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    facts = relationship("PortraitFact", back_populates="portrait", cascade="all, delete-orphan")
    aspect_chains = relationship("PortraitAspectChain", back_populates="portrait", cascade="all, delete-orphan")
    patterns = relationship("PortraitPattern", back_populates="portrait", cascade="all, delete-orphan")
    recommendations = relationship("PortraitRecommendation", back_populates="portrait", cascade="all, delete-orphan")
    shadow_audits = relationship("PortraitShadowAudit", back_populates="portrait", cascade="all, delete-orphan")
    meta_patterns = relationship("PortraitMetaPattern", back_populates="portrait", cascade="all, delete-orphan")
    summaries = relationship("PortraitSummary", back_populates="portrait", cascade="all, delete-orphan")
    raw_data = relationship("PortraitRawData", back_populates="portrait", cascade="all, delete-orphan")


# ─── Таблица 0.5: Сырые данные калькуляторов ────────────────────────────────
class PortraitRawData(Base):
    __tablename__ = "dsb_raw_data"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    system_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # western_astrology | bazi | ...

    data_group: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # planets | aspects | houses | patterns

    data_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    # Sun | Moon-Sun-Trine | House-1

    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="raw_data")


# ─── Таблица 1: Атомарные факты (из Слоя 2) ─────────────────────────────────
class PortraitFact(Base):
    __tablename__ = "dsb_portrait_facts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    source_system: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # western_astrology | bazi | human_design | ...

    sphere_primary: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    spheres_affected: Mapped[list] = mapped_column(ARRAY(Integer), default=list)
    position: Mapped[str] = mapped_column(Text, nullable=False)
    influence_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)

    light_aspect: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    shadow_aspect: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    energy_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    core_theme: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    developmental_task: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    integration_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    triggers: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    timing: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    book_references: Mapped[list] = mapped_column(ARRAY(Text), default=list)

    weight: Mapped[float] = mapped_column(Float, default=0.5)
    confidence: Mapped[float] = mapped_column(Float, default=0.5)
    raw_uis: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="facts")

    __table_args__ = (
        CheckConstraint("sphere_primary BETWEEN 1 AND 12", name="ck_fact_sphere"),
        CheckConstraint("influence_level IN ('high', 'medium', 'low')", name="ck_fact_influence"),
    )


# ─── Таблица 2: Аспектные цепочки ────────────────────────────────────────────
class PortraitAspectChain(Base):
    __tablename__ = "dsb_portrait_aspect_chains"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    sphere: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    chain_name: Mapped[str] = mapped_column(Text, nullable=False)
    systems_involved: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    convergence_score: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="aspect_chains")

    __table_args__ = (
        CheckConstraint("convergence_score BETWEEN 0 AND 1", name="ck_chain_convergence"),
    )


# ─── Таблица 3: Синтезированные паттерны ─────────────────────────────────────
class PortraitPattern(Base):
    __tablename__ = "dsb_portrait_patterns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    sphere: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    pattern_name: Mapped[str] = mapped_column(Text, nullable=False)
    formula: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    systems_supporting: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    convergence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    influence_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="patterns")


# ─── Таблица 4: Рекомендации ──────────────────────────────────────────────────
class PortraitRecommendation(Base):
    __tablename__ = "dsb_portrait_recommendations"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    sphere: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    source_systems: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    influence_level: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # practical | mindset | timing | partnership | spiritual

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="recommendations")


# ─── Таблица 5: Теневой аудит ────────────────────────────────────────────────
class PortraitShadowAudit(Base):
    __tablename__ = "dsb_portrait_shadow_audit"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    sphere: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    risk_name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_systems: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    convergence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    antidote: Mapped[str] = mapped_column(Text, nullable=False)

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="shadow_audits")


# ─── Таблица 6: Межсферные суперпаттерны (от Meta Agent) ────────────────────
class PortraitMetaPattern(Base):
    __tablename__ = "dsb_portrait_meta_patterns"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    pattern_name: Mapped[str] = mapped_column(Text, nullable=False)
    spheres_involved: Mapped[list] = mapped_column(ARRAY(Integer), default=list)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    systems_supporting: Mapped[list] = mapped_column(ARRAY(Text), default=list)
    convergence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    key_manifestations: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    embedding = mapped_column(Vector(1536) if _VECTOR_AVAILABLE and Vector else JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="meta_patterns")


# ─── Таблица 7: Краткий формат (от Compressor) ──────────────────────────────
class PortraitSummary(Base):
    __tablename__ = "dsb_portrait_summaries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    portrait_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("dsb_digital_portraits.id", ondelete="CASCADE"), index=True)

    sphere: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # NULL для overall
    brief_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_overall: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    portrait = relationship("DigitalPortrait", back_populates="summaries")
