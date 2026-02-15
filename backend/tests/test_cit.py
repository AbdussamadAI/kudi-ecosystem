"""
Tests for the Company Income Tax (CIT) Calculator.
Validates against Nigeria Tax Act 2025, Section 56.

CIT Rates:
  - Small companies (turnover ≤ ₦25M): 0%
  - All other companies: 30%
  - Development Levy: 4% (non-small companies)
  - Minimum effective rate: 15% (MNEs / turnover ≥ ₦20B)
"""

import pytest
from app.core.tax_rules.cit import CITCalculator, CompanySize


@pytest.fixture
def calc():
    return CITCalculator()


class TestCompanyClassification:
    def test_small_company(self, calc):
        assert calc.classify_company(20_000_000) == CompanySize.SMALL

    def test_small_company_boundary(self, calc):
        assert calc.classify_company(25_000_000) == CompanySize.SMALL

    def test_medium_company(self, calc):
        assert calc.classify_company(50_000_000) == CompanySize.MEDIUM

    def test_large_company(self, calc):
        assert calc.classify_company(200_000_000) == CompanySize.LARGE


class TestCITCalculation:
    def test_small_company_zero_tax(self, calc):
        result = calc.calculate(gross_profit=5_000_000, annual_turnover=20_000_000)
        assert result.cit_liability == 0
        assert result.development_levy == 0
        assert result.total_tax_liability == 0

    def test_standard_company_30_percent(self, calc):
        result = calc.calculate(gross_profit=10_000_000, annual_turnover=50_000_000)
        assert result.cit_rate == 0.30
        assert result.cit_liability == 3_000_000
        assert result.development_levy == 400_000
        assert result.total_tax_liability == 3_400_000

    def test_deductions_reduce_assessable_profit(self, calc):
        result = calc.calculate(
            gross_profit=10_000_000,
            allowable_deductions=3_000_000,
            annual_turnover=50_000_000,
        )
        assert result.assessable_profit == 7_000_000
        assert result.cit_liability == 2_100_000

    def test_negative_profit_raises(self, calc):
        with pytest.raises(ValueError):
            calc.calculate(gross_profit=-1)

    def test_effective_rate(self, calc):
        result = calc.calculate(gross_profit=10_000_000, annual_turnover=50_000_000)
        expected_rate = (result.total_tax_liability / result.assessable_profit) * 100
        assert result.effective_rate == round(expected_rate, 2)
