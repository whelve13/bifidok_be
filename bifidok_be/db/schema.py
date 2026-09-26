"""
SQLAlchemy database models for Enterprise AI Sales Intelligence Platform.
Follows Section 3.2 of Enterprise_AI_Sales_Intelligence_Platform_Annex.md
with 500MB storage budget optimizations (bounded quote/reasoning lengths).
"""
import enum
import uuid
from datetime import datetime, timezone
from typing import Optional

import sqlalchemy as sa
from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class GUID(sa.TypeDecorator):
    """Platform-independent GUID/UUID type.
    Uses PostgreSQL's native UUID or SQLite CHAR(32)/UUID,
    handling Python UUID objects and string UUIDs seamlessly.
    """
    impl = sa.Uuid
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, uuid.UUID):
            return value
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError):
            return value


class SignalWeightType(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    DISQUALIFY = "DISQUALIFY"


class Company(Base):
    __tablename__ = "companies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=False, index=True)
    industry = Column(String(100), nullable=True)
    geography = Column(String(100), nullable=True)
    employee_count = Column(Integer, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    signal_evaluations = relationship(
        "SignalEvaluation",
        back_populates="company",
        cascade="all, delete-orphan",
    )
    lead_scores = relationship(
        "LeadScore",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class ServiceOffering(Base):
    __tablename__ = "service_offerings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)

    signal_rules = relationship(
        "SignalRule",
        back_populates="service",
        cascade="all, delete-orphan",
    )
    lead_scores = relationship(
        "LeadScore",
        back_populates="service",
        cascade="all, delete-orphan",
    )


class SignalRule(Base):
    __tablename__ = "signal_rules"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    service_id = Column(
        GUID,
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    question = Column(Text, nullable=False)
    guidance_notes = Column(Text, nullable=True)
    weight = Column(
        sa.Enum(SignalWeightType, name="signal_weight_type"),
        nullable=False,
        default=SignalWeightType.MEDIUM,
    )
    is_negative = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    service = relationship("ServiceOffering", back_populates="signal_rules")
    evaluations = relationship(
        "SignalEvaluation",
        back_populates="rule",
        cascade="all, delete-orphan",
    )


class SignalEvaluation(Base):
    __tablename__ = "signal_evaluations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = Column(
        GUID,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id = Column(
        GUID,
        ForeignKey("signal_rules.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url = Column(Text, nullable=False)
    detected = Column(Boolean, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence_quote = Column(String(280), nullable=False)
    reasoning = Column(String(200), nullable=False)
    evaluated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "rule_id",
            "source_url",
            name="uq_signal_eval_company_rule_url",
        ),
        CheckConstraint(
            "confidence >= 0.0 AND confidence <= 1.0",
            name="chk_signal_eval_confidence",
        ),
    )

    company = relationship("Company", back_populates="signal_evaluations")
    rule = relationship("SignalRule", back_populates="evaluations")


class LeadScore(Base):
    __tablename__ = "lead_scores"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    company_id = Column(
        GUID,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    service_id = Column(
        GUID,
        ForeignKey("service_offerings.id", ondelete="CASCADE"),
        nullable=False,
    )
    composite_score = Column(Integer, nullable=False)
    is_disqualified = Column(Boolean, nullable=False, default=False)
    disqualification_reason = Column(Text, nullable=True)
    executive_summary = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "service_id",
            name="uq_lead_score_company_service",
        ),
        CheckConstraint(
            "composite_score >= 0 AND composite_score <= 100",
            name="chk_lead_score_composite_score",
        ),
    )

    company = relationship("Company", back_populates="lead_scores")
    service = relationship("ServiceOffering", back_populates="lead_scores")


class MCPApiKey(Base):
    __tablename__ = "mcp_api_keys"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    tenant_name = Column(String(100), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
    )
