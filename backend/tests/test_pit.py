"""
Tests for the Personal Income Tax (PIT) Calculator.
Validates against Nigeria Tax Act 2025, Fourth Schedule.

Tax Brackets:
  (a) First ₦800,000 at 0%
  (b) Next ₦2,200,000 at 15%
  (c) Next ₦9,000,000 at 18%
  (d) Next ₦13,000,000 at 21%
  (e) Next ₦25,000,000 at 23%
  (f) Above ₦50,000,000 at 25%
"""

import pytest
from app.core.tax_rules.pit import PITCalculator, Deductions


@pytest.fixture
def calc():
    return PITCalculator()


class TestPITBrackets:
    """Test tax calculation at each bracket boundary."""

    def test_zero_income(self, calc):
        result = calc.calculate(0)
        assert result.tax_liability == 0
        assert result.effective_rate == 0

    def test_within_first_bracket_zero_rate(self, calc):
        # ₦500K is below minimum wage threshold (₦840K), so exempt
        result = calc.calculate(500_000)
        assert result.tax_liability == 0
        assert result.is_minimum_wage_exempt is True

    def test_exactly_first_bracket(self, calc):
        result = calc.calculate(800_000)
        assert result.tax_liability == 0

    def test_into_second_bracket(self, calc):
        # 800K at 0% + 200K at 15% = 30,000
        result = calc.calculate(1_000_000)
        assert result.tax_liability == 30_000

    def test_exactly_second_bracket_boundary(self, calc):
        # 800K at 0% + 2,200K at 15% = 330,000
        result = calc.calculate(3_000_000)
        assert result.tax_liability == 330_000

    def test_into_third_bracket(self, calc):
        # 800K at 0% + 2,200K at 15% + 2,000K at 18% = 330K + 360K = 690K
        result = calc.calculate(5_000_000)
        assert result.tax_liability == 690_000

    def test_exactly_third_bracket_boundary(self, calc):
        # 800K + 2,200K + 9,000K = 12,000K
        # 0 + 330K + 1,620K = 1,950K
        result = calc.calculate(12_000_000)
        assert result.tax_liability == 1_950_000

    def test_into_fourth_bracket(self, calc):
        # 12M boundary = 1,950K tax
        # Next 3M at 21% = 630K
        # Total = 2,580K
        result = calc.calculate(15_000_000)
        assert result.tax_liability == 2_580_000

    def test_exactly_fourth_bracket_boundary(self, calc):
        # 800K + 2,200K + 9,000K + 13,000K = 25,000K
        # 0 + 330K + 1,620K + 2,730K = 4,680K
        result = calc.calculate(25_000_000)
        assert result.tax_liability == 4_680_000

    def test_into_fifth_bracket(self, calc):
        # 25M boundary = 4,680K
        # Next 5M at 23% = 1,150K
        # Total = 5,830K
        result = calc.calculate(30_000_000)
        assert result.tax_liability == 5_830_000

    def test_exactly_fifth_bracket_boundary(self, calc):
        # 800K + 2,200K + 9,000K + 13,000K + 25,000K = 50,000K
        # 0 + 330K + 1,620K + 2,730K + 5,750K = 10,430K
        result = calc.calculate(50_000_000)
        assert result.tax_liability == 10_430_000

    def test_into_sixth_bracket(self, calc):
        # 50M boundary = 10,430K
        # Next 10M at 25% = 2,500K
        # Total = 12,930K
        result = calc.calculate(60_000_000)
        assert result.tax_liability == 12_930_000

    def test_high_income(self, calc):
        # 50M boundary = 10,430K
        # Next 50M at 25% = 12,500K
        # Total = 22,930K
        result = calc.calculate(100_000_000)
        assert result.tax_liability == 22_930_000


class TestPITDeductions:
    """Test deduction calculations."""

    def test_pension_deduction(self, calc):
        deductions = Deductions(pension=500_000)
        result = calc.calculate(5_000_000, deductions)
        assert result.total_deductions == 500_000
        assert result.taxable_income == 4_500_000

    def test_rent_relief_capped(self, calc):
        # 20% of 5M = 1M, but capped at 500K
        deductions = Deductions(annual_rent_paid=5_000_000)
        assert deductions.rent_relief == 500_000

    def test_rent_relief_below_cap(self, calc):
        # 20% of 1M = 200K, below cap
        deductions = Deductions(annual_rent_paid=1_000_000)
        assert deductions.rent_relief == 200_000

    def test_all_deductions_combined(self, calc):
        deductions = Deductions(
            pension=300_000,
            nhf=100_000,
            nhis=50_000,
            life_insurance=200_000,
            housing_loan_interest=150_000,
            annual_rent_paid=2_000_000,  # 20% = 400K
        )
        expected_total = 300_000 + 100_000 + 50_000 + 200_000 + 150_000 + 400_000
        assert deductions.total == expected_total

        result = calc.calculate(10_000_000, deductions)
        assert result.taxable_income == 10_000_000 - expected_total
        assert result.total_deductions == expected_total

    def test_deductions_exceeding_income(self, calc):
        deductions = Deductions(pension=6_000_000)
        result = calc.calculate(5_000_000, deductions)
        assert result.taxable_income == 0
        assert result.tax_liability == 0


class TestPITMinimumWage:
    """Test minimum wage exemption."""

    def test_minimum_wage_earner_exempt(self, calc):
        result = calc.calculate(840_000, is_minimum_wage_earner=True)
        assert result.is_minimum_wage_exempt is True
        assert result.tax_liability == 0

    def test_below_minimum_wage_threshold(self, calc):
        # Annual minimum wage = 70K * 12 = 840K
        result = calc.calculate(800_000)
        assert result.is_minimum_wage_exempt is True
        assert result.tax_liability == 0


class TestPITPAYE:
    """Test PAYE estimation."""

    def test_monthly_paye_estimate(self, calc):
        result = calc.estimate_monthly_paye(500_000)
        assert result["annual_gross"] == 6_000_000
        assert result["monthly_paye"] > 0
        assert result["monthly_paye"] == round(result["annual_tax"] / 12, 2)


class TestPITEdgeCases:
    """Test edge cases."""

    def test_negative_income_raises(self, calc):
        with pytest.raises(ValueError):
            calc.calculate(-1)

    def test_no_deductions_default(self, calc):
        result = calc.calculate(5_000_000)
        assert result.total_deductions == 0

    def test_bracket_breakdown_count(self, calc):
        result = calc.calculate(60_000_000)
        assert len(result.bracket_breakdown) == 6

    def test_effective_rate_reasonable(self, calc):
        result = calc.calculate(10_000_000)
        assert 0 < result.effective_rate < 25
