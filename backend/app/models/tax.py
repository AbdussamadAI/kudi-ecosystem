from __future__ import annotations

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, Enum, ForeignKey, Integer, Boolean, Text, Date
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDMixin, TimestampMixin


class TaxType(str, PyEnum):
    PIT = "pit"
    CIT = "cit"
    VAT = "vat"
    WHT = "wht"
    DEVELOPMENT_LEVY = "development_levy"


class ComplianceStatus(str, PyEnum):
    PENDING = "pending"
    COMPLETED = "completed"
    OVERDUE = "overdue"
    NOT_APPLICABLE = "not_applicable"


class TaxCalculation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tax_calculations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_type: Mapped[TaxType] = mapped_column(
        Enum(TaxType, name="tax_type_enum"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    gross_income: Mapped[float] = mapped_column(Float, nullable=False)
    total_deductions: Mapped[float] = mapped_column(Float, default=0.0)
    taxable_income: Mapped[float] = mapped_column(Float, nullable=False)
    tax_liability: Mapped[float] = mapped_column(Float, nullable=False)
    effective_rate: Mapped[float] = mapped_column(Float, nullable=False)
    breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_scenario: Mapped[bool] = mapped_column(Boolean, default=False)
    scenario_label: Mapped[str | None] = mapped_column(String(255), nullable=True)


class TaxDeduction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tax_deductions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    deduction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)


class ComplianceItem(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "compliance_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    due_date: Mapped[str | None] = mapped_column(Date, nullable=True)
    status: Mapped[ComplianceStatus] = mapped_column(
        Enum(ComplianceStatus, name="compliance_status_enum"),
        default=ComplianceStatus.PENDING,
    )
    tax_type: Mapped[TaxType] = mapped_column(
        Enum(TaxType, name="tax_type_enum_compliance"), nullable=False
    )
