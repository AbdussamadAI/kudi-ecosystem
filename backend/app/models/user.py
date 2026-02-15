from __future__ import annotations

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import String, Boolean, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.chat import ChatConversation
    from app.models.billing import Subscription

from app.models.base import Base, UUIDMixin, TimestampMixin


class UserType(str, PyEnum):
    INDIVIDUAL = "individual"
    FREELANCER = "freelancer"
    SME = "sme"


class SubscriptionTier(str, PyEnum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    supabase_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    user_type: Mapped[UserType] = mapped_column(
        Enum(UserType, name="user_type_enum"), nullable=False
    )
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(SubscriptionTier, name="subscription_tier_enum"),
        default=SubscriptionTier.FREE,
    )

    profile: Mapped["UserProfile"] = relationship(back_populates="user", uselist=False)
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    conversations: Mapped[list["ChatConversation"]] = relationship(back_populates="user")
    subscription: Mapped["Subscription"] = relationship(back_populates="user", uselist=False)


class UserProfile(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    tin: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state_of_residence: Mapped[str | None] = mapped_column(String(100), nullable=True)
    employment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rc_number: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company_size: Mapped[str | None] = mapped_column(String(20), nullable=True)
    annual_gross_income: Mapped[float | None] = mapped_column(nullable=True)
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    user: Mapped["User"] = relationship(back_populates="profile")
