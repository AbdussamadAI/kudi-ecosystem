from __future__ import annotations

import uuid
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import String, Float, Enum, ForeignKey, Date, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.user import User

from app.models.base import Base, UUIDMixin, TimestampMixin


class TransactionType(str, PyEnum):
    INCOME = "income"
    EXPENSE = "expense"


class IncomeCategory(str, PyEnum):
    SALARY = "salary"
    FREELANCE = "freelance"
    BUSINESS = "business"
    INVESTMENT = "investment"
    RENTAL = "rental"
    CAPITAL_GAINS = "capital_gains"
    FOREX_GAINS = "forex_gains"
    CRYPTO_GAINS = "crypto_gains"
    DIVIDEND = "dividend"
    OTHER = "other"


class ExpenseCategory(str, PyEnum):
    BUSINESS_EXPENSE = "business_expense"
    PERSONAL = "personal"
    DEDUCTIBLE = "deductible"
    NON_DEDUCTIBLE = "non_deductible"
    RENT = "rent"
    INSURANCE = "insurance"
    PENSION = "pension"
    NHF = "nhf"
    NHIS = "nhis"
    OTHER = "other"


class Currency(str, PyEnum):
    NGN = "NGN"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    BTC = "BTC"
    USDT = "USDT"
    ETH = "ETH"


class Transaction(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum"), nullable=False
    )
    income_category: Mapped[IncomeCategory | None] = mapped_column(
        Enum(IncomeCategory, name="income_category_enum"), nullable=True
    )
    expense_category: Mapped[ExpenseCategory | None] = mapped_column(
        Enum(ExpenseCategory, name="expense_category_enum"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency_enum"), default=Currency.NGN
    )
    amount_ngn: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_rate: Mapped[float] = mapped_column(Float, default=1.0)
    transaction_date: Mapped[str] = mapped_column(Date, nullable=False)
    is_vat_applicable: Mapped[bool] = mapped_column(default=False)
    is_wht_applicable: Mapped[bool] = mapped_column(default=False)
    is_capital: Mapped[bool] = mapped_column(default=False)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    ai_classified: Mapped[bool] = mapped_column(default=False)

    user: Mapped["User"] = relationship(back_populates="transactions")
