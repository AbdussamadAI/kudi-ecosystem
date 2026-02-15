"""
Company Income Tax (CIT) Calculator
Based on Nigeria Tax Act 2025, Chapter 2, Part IX, Section 56

CIT Rates:
  - Small companies: 0%
  - All other companies: 30%
  - Minimum effective tax rate: 15% (for MNEs and companies with ≥₦20B turnover)

Development Levy (Section 59):
  - 4% on assessable profits of all companies (except small companies and non-residents)
"""

from dataclasses import dataclass, field
from enum import Enum


class CompanySize(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


SMALL_COMPANY_TURNOVER_THRESHOLD = 25_000_000.0
LARGE_COMPANY_TURNOVER_THRESHOLD = 100_000_000.0
MNE_TURNOVER_THRESHOLD = 20_000_000_000.0

CIT_RATE_SMALL = 0.00
CIT_RATE_STANDARD = 0.30
MINIMUM_EFFECTIVE_RATE = 0.15
DEVELOPMENT_LEVY_RATE = 0.04


@dataclass
class CITResult:
    company_size: CompanySize
    gross_profit: float
    allowable_deductions: float
    assessable_profit: float
    cit_rate: float
    cit_liability: float
    development_levy: float
    total_tax_liability: float
    effective_rate: float
    minimum_tax_applied: bool = False
    breakdown: dict = field(default_factory=dict)


class CITCalculator:
    """
    Deterministic Company Income Tax calculator for Nigerian companies.
    All calculations follow the Nigeria Tax Act 2025.
    """

    def classify_company(self, annual_turnover: float) -> CompanySize:
        if annual_turnover <= SMALL_COMPANY_TURNOVER_THRESHOLD:
            return CompanySize.SMALL
        elif annual_turnover <= LARGE_COMPANY_TURNOVER_THRESHOLD:
            return CompanySize.MEDIUM
        return CompanySize.LARGE

    def calculate(
        self,
        gross_profit: float,
        allowable_deductions: float = 0.0,
        annual_turnover: float = 0.0,
        is_mne: bool = False,
        company_size: CompanySize | None = None,
    ) -> CITResult:
        if gross_profit < 0:
            raise ValueError("Gross profit cannot be negative")

        if company_size is None:
            company_size = self.classify_company(annual_turnover)

        assessable_profit = max(gross_profit - allowable_deductions, 0.0)

        if company_size == CompanySize.SMALL:
            cit_rate = CIT_RATE_SMALL
        else:
            cit_rate = CIT_RATE_STANDARD

        cit_liability = assessable_profit * cit_rate

        development_levy = 0.0
        if company_size != CompanySize.SMALL:
            development_levy = assessable_profit * DEVELOPMENT_LEVY_RATE

        total_before_minimum = cit_liability + development_levy

        minimum_tax_applied = False
        if is_mne or annual_turnover >= MNE_TURNOVER_THRESHOLD:
            effective = (total_before_minimum / assessable_profit) if assessable_profit > 0 else 0
            if effective < MINIMUM_EFFECTIVE_RATE and assessable_profit > 0:
                minimum_tax = assessable_profit * MINIMUM_EFFECTIVE_RATE
                cit_liability = minimum_tax - development_levy
                minimum_tax_applied = True

        total_tax_liability = cit_liability + development_levy
        effective_rate = (
            (total_tax_liability / assessable_profit * 100) if assessable_profit > 0 else 0.0
        )

        breakdown = {
            "cit_rate_applied": cit_rate * 100,
            "cit_amount": round(cit_liability, 2),
            "development_levy_rate": DEVELOPMENT_LEVY_RATE * 100 if company_size != CompanySize.SMALL else 0,
            "development_levy_amount": round(development_levy, 2),
        }

        return CITResult(
            company_size=company_size,
            gross_profit=gross_profit,
            allowable_deductions=allowable_deductions,
            assessable_profit=round(assessable_profit, 2),
            cit_rate=cit_rate,
            cit_liability=round(cit_liability, 2),
            development_levy=round(development_levy, 2),
            total_tax_liability=round(total_tax_liability, 2),
            effective_rate=round(effective_rate, 2),
            minimum_tax_applied=minimum_tax_applied,
            breakdown=breakdown,
        )
