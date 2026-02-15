"""
Pydantic schemas for API request/response validation.
"""

from datetime import date, datetime
from enum import Enum
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


# ── Auth Schemas ──

class UserType(str, Enum):
    INDIVIDUAL = "individual"
    FREELANCER = "freelancer"
    SME = "sme"


class SubscriptionTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    BUSINESS = "business"


class UserRegister(BaseModel):
    email: str = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=255)
    user_type: UserType
    password: str = Field(..., min_length=8)


class UserLogin(BaseModel):
    email: str
    password: str


class UserProfileUpdate(BaseModel):
    full_name: str | None = None
    user_type: UserType | None = None
    tin: str | None = None
    state_of_residence: str | None = None
    employment_status: str | None = None
    company_name: str | None = None
    rc_number: str | None = None
    company_size: str | None = None
    annual_gross_income: float | None = None
    phone_number: str | None = None


class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    user_type: UserType
    subscription_tier: SubscriptionTier
    created_at: datetime

    class Config:
        from_attributes = True


class UserProfileResponse(BaseModel):
    id: UUID
    user_id: UUID
    tin: str | None = None
    state_of_residence: str | None = None
    employment_status: str | None = None
    company_name: str | None = None
    rc_number: str | None = None
    company_size: str | None = None
    annual_gross_income: float | None = None
    phone_number: str | None = None

    class Config:
        from_attributes = True


# ── Transaction Schemas ──

class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


class Currency(str, Enum):
    NGN = "NGN"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    BTC = "BTC"
    USDT = "USDT"
    ETH = "ETH"


class TransactionCreate(BaseModel):
    transaction_type: TransactionType
    description: str = Field(..., min_length=1, max_length=500)
    amount: float = Field(..., gt=0)
    currency: Currency = Currency.NGN
    transaction_date: date
    income_category: str | None = None
    expense_category: str | None = None
    is_vat_applicable: bool = False
    is_wht_applicable: bool = False
    is_capital: bool = False


class TransactionResponse(BaseModel):
    id: UUID
    user_id: UUID
    transaction_type: TransactionType
    description: str
    amount: float
    currency: Currency
    amount_ngn: float
    exchange_rate: float
    transaction_date: date
    income_category: str | None = None
    expense_category: str | None = None
    is_vat_applicable: bool
    is_wht_applicable: bool
    is_capital: bool
    source: str
    ai_classified: bool
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    transactions: list[TransactionResponse]
    total: int
    page: int
    page_size: int


# ── Tax Schemas ──

class PITCalculateRequest(BaseModel):
    gross_income: float = Field(..., gt=0)
    pension: float = Field(default=0, ge=0)
    nhf: float = Field(default=0, ge=0)
    nhis: float = Field(default=0, ge=0)
    life_insurance: float = Field(default=0, ge=0)
    housing_loan_interest: float = Field(default=0, ge=0)
    annual_rent_paid: float = Field(default=0, ge=0)
    is_minimum_wage: bool = False


class CITCalculateRequest(BaseModel):
    gross_profit: float = Field(..., gt=0)
    allowable_deductions: float = Field(default=0, ge=0)
    annual_turnover: float = Field(default=0, ge=0)
    is_mne: bool = False


class VATCalculateRequest(BaseModel):
    amount: float = Field(..., gt=0)
    is_inclusive: bool = False


class WHTCalculateRequest(BaseModel):
    gross_amount: float = Field(..., gt=0)
    payment_type: str
    recipient_type: str = "company"


class ScenarioRequest(BaseModel):
    scenario_type: str = Field(..., description="income_change, deduction_impact, or individual_vs_company")
    current_income: float = Field(..., gt=0)
    projected_income: float | None = None
    current_deductions: dict | None = None
    projected_deductions: dict | None = None
    business_expenses: float = 0


# ── Chat Schemas ──

class ChatMessageCreate(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    conversation_id: UUID | None = None


class ChatMessageResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    tool_calls: dict | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    messages: list[ChatMessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    conversations: list[ConversationResponse]
    total: int


# ── Report Schemas ──

class ReportRequest(BaseModel):
    report_type: str = Field(..., description="tax_summary or compliance_checklist")
    year: int = Field(..., ge=2020, le=2030)
    period: str = "annual"


# ── Billing Schemas ──

class SubscriptionCreateRequest(BaseModel):
    plan: SubscriptionTier
    provider: str = "paystack"


class SubscriptionResponse(BaseModel):
    id: UUID
    plan_code: str
    is_active: bool
    provider: str
    current_period_end: datetime | None = None

    class Config:
        from_attributes = True
