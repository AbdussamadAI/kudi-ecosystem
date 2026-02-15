"""
Personal Income Tax (PIT) Calculator
Based on Nigeria Tax Act 2025, Chapter 2, Part IX, Section 58
Fourth Schedule — Individuals' Income Tax Rates

Tax Brackets (after relief allowance and exemptions):
  (a) First ₦800,000 at 0%
  (b) Next ₦2,200,000 at 15%
  (c) Next ₦9,000,000 at 18%
  (d) Next ₦13,000,000 at 21%
  (e) Next ₦25,000,000 at 23%
  (f) Above ₦50,000,000 at 25%

Eligible Deductions (Section 30):
  - National Housing Fund (NHF) contributions
  - National Health Insurance Scheme (NHIS) contributions
  - Pension Reform Act contributions
  - Interest on owner-occupied residential house loans
  - Life insurance premiums (self or spouse)
  - Rent relief: 20% of annual rent paid (max ₦500,000)
"""

from dataclasses import dataclass, field


TAX_BRACKETS: list[tuple[float, float]] = [
    (800_000.0, 0.00),
    (2_200_000.0, 0.15),
    (9_000_000.0, 0.18),
    (13_000_000.0, 0.21),
    (25_000_000.0, 0.23),
    (float("inf"), 0.25),
]

RENT_RELIEF_RATE = 0.20
RENT_RELIEF_MAX = 500_000.0


@dataclass
class Deductions:
    pension: float = 0.0
    nhf: float = 0.0
    nhis: float = 0.0
    life_insurance: float = 0.0
    housing_loan_interest: float = 0.0
    annual_rent_paid: float = 0.0

    @property
    def rent_relief(self) -> float:
        return min(self.annual_rent_paid * RENT_RELIEF_RATE, RENT_RELIEF_MAX)

    @property
    def total(self) -> float:
        return (
            self.pension
            + self.nhf
            + self.nhis
            + self.life_insurance
            + self.housing_loan_interest
            + self.rent_relief
        )


@dataclass
class BracketBreakdown:
    bracket_floor: float
    bracket_ceiling: float
    rate: float
    taxable_in_bracket: float
    tax_in_bracket: float


@dataclass
class PITResult:
    gross_income: float
    total_deductions: float
    deduction_details: dict
    taxable_income: float
    tax_liability: float
    effective_rate: float
    bracket_breakdown: list[BracketBreakdown] = field(default_factory=list)
    is_minimum_wage_exempt: bool = False


class PITCalculator:
    """
    Deterministic Personal Income Tax calculator for Nigerian individuals.
    All calculations follow the Nigeria Tax Act 2025.
    """

    MINIMUM_WAGE_ANNUAL = 70_000.0 * 12  # ₦70,000/month as of 2024

    def calculate(
        self,
        gross_income: float,
        deductions: Deductions | None = None,
        is_minimum_wage_earner: bool = False,
    ) -> PITResult:
        if gross_income < 0:
            raise ValueError("Gross income cannot be negative")

        if deductions is None:
            deductions = Deductions()

        if is_minimum_wage_earner or gross_income <= self.MINIMUM_WAGE_ANNUAL:
            return PITResult(
                gross_income=gross_income,
                total_deductions=0.0,
                deduction_details={},
                taxable_income=0.0,
                tax_liability=0.0,
                effective_rate=0.0,
                bracket_breakdown=[],
                is_minimum_wage_exempt=True,
            )

        total_deductions = deductions.total
        taxable_income = max(gross_income - total_deductions, 0.0)

        bracket_breakdown = self._calculate_brackets(taxable_income)
        tax_liability = sum(b.tax_in_bracket for b in bracket_breakdown)
        effective_rate = (tax_liability / gross_income * 100) if gross_income > 0 else 0.0

        deduction_details = {
            "pension": deductions.pension,
            "nhf": deductions.nhf,
            "nhis": deductions.nhis,
            "life_insurance": deductions.life_insurance,
            "housing_loan_interest": deductions.housing_loan_interest,
            "rent_relief": deductions.rent_relief,
            "annual_rent_paid": deductions.annual_rent_paid,
        }

        return PITResult(
            gross_income=gross_income,
            total_deductions=total_deductions,
            deduction_details=deduction_details,
            taxable_income=taxable_income,
            tax_liability=round(tax_liability, 2),
            effective_rate=round(effective_rate, 2),
            bracket_breakdown=bracket_breakdown,
        )

    def _calculate_brackets(self, taxable_income: float) -> list[BracketBreakdown]:
        breakdown = []
        remaining = taxable_income
        cumulative_floor = 0.0

        for bracket_size, rate in TAX_BRACKETS:
            if remaining <= 0:
                break

            taxable_in_bracket = min(remaining, bracket_size)
            tax_in_bracket = taxable_in_bracket * rate

            breakdown.append(
                BracketBreakdown(
                    bracket_floor=cumulative_floor,
                    bracket_ceiling=cumulative_floor + bracket_size if bracket_size != float("inf") else float("inf"),
                    rate=rate,
                    taxable_in_bracket=round(taxable_in_bracket, 2),
                    tax_in_bracket=round(tax_in_bracket, 2),
                )
            )

            remaining -= taxable_in_bracket
            cumulative_floor += bracket_size

        return breakdown

    def estimate_monthly_paye(
        self,
        monthly_gross: float,
        deductions: Deductions | None = None,
    ) -> dict:
        annual_gross = monthly_gross * 12
        result = self.calculate(annual_gross, deductions)
        monthly_tax = result.tax_liability / 12

        return {
            "monthly_gross": monthly_gross,
            "annual_gross": annual_gross,
            "annual_tax": result.tax_liability,
            "monthly_paye": round(monthly_tax, 2),
            "effective_rate": result.effective_rate,
        }
