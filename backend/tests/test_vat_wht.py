"""
Tests for VAT and WHT Calculators.
VAT: Section 148 — 7.5%
WHT: Rates vary by payment type and recipient type.
"""

import pytest
from app.core.tax_rules.vat import VATCalculator, VATCategory
from app.core.tax_rules.wht import WHTCalculator, WHTPaymentType, RecipientType


@pytest.fixture
def vat_calc():
    return VATCalculator()


@pytest.fixture
def wht_calc():
    return WHTCalculator()


class TestVAT:
    def test_simple_vat(self, vat_calc):
        result = vat_calc.calculate_simple(100_000)
        assert result["vat_rate"] == 7.5
        assert result["vat_amount"] == 7_500
        assert result["total_with_vat"] == 107_500

    def test_extract_vat_from_inclusive(self, vat_calc):
        result = vat_calc.extract_vat_from_inclusive(107_500)
        assert result["amount_before_vat"] == 100_000
        assert result["vat_amount"] == 7_500

    def test_exempt_supply(self, vat_calc):
        cat = vat_calc.classify_supply("basic_food_items")
        assert cat == VATCategory.EXEMPT
        assert vat_calc.calculate_vat_on_supply(100_000, cat) == 0

    def test_zero_rated_supply(self, vat_calc):
        cat = vat_calc.classify_supply("non_oil_exports")
        assert cat == VATCategory.ZERO_RATED
        assert vat_calc.calculate_vat_on_supply(100_000, cat) == 0

    def test_standard_supply(self, vat_calc):
        cat = vat_calc.classify_supply("consulting_services")
        assert cat == VATCategory.STANDARD

    def test_batch_calculation(self, vat_calc):
        result = vat_calc.calculate(
            output_supplies=[
                {"description": "Service A", "amount": 100_000, "category": "standard"},
                {"description": "Food", "amount": 50_000, "category": "basic_food_items"},
            ],
            input_purchases=[
                {"amount": 30_000, "category": "standard"},
            ],
        )
        assert result.taxable_supplies == 100_000
        assert result.exempt_supplies == 50_000
        assert result.output_vat == 7_500
        assert result.input_vat == 2_250
        assert result.net_vat_payable == 5_250


class TestWHT:
    def test_contract_company(self, wht_calc):
        result = wht_calc.calculate_single(1_000_000, WHTPaymentType.CONTRACT, RecipientType.COMPANY)
        assert result.wht_rate == 0.10
        assert result.wht_amount == 100_000
        assert result.net_amount == 900_000

    def test_consultancy_individual(self, wht_calc):
        result = wht_calc.calculate_single(500_000, WHTPaymentType.CONSULTANCY, RecipientType.INDIVIDUAL)
        assert result.wht_rate == 0.05
        assert result.wht_amount == 25_000
        assert result.net_amount == 475_000

    def test_consultancy_company(self, wht_calc):
        result = wht_calc.calculate_single(500_000, WHTPaymentType.CONSULTANCY, RecipientType.COMPANY)
        assert result.wht_rate == 0.10
        assert result.wht_amount == 50_000

    def test_dividend(self, wht_calc):
        result = wht_calc.calculate_single(1_000_000, WHTPaymentType.DIVIDEND, RecipientType.INDIVIDUAL)
        assert result.wht_rate == 0.10
        assert result.wht_amount == 100_000

    def test_rent(self, wht_calc):
        result = wht_calc.calculate_single(2_000_000, WHTPaymentType.RENT, RecipientType.COMPANY)
        assert result.wht_rate == 0.10
        assert result.wht_amount == 200_000

    def test_construction(self, wht_calc):
        result = wht_calc.calculate_single(5_000_000, WHTPaymentType.CONSTRUCTION, RecipientType.COMPANY)
        assert result.wht_rate == 0.05
        assert result.wht_amount == 250_000

    def test_negative_amount_raises(self, wht_calc):
        with pytest.raises(ValueError):
            wht_calc.calculate_single(-100, WHTPaymentType.CONTRACT, RecipientType.COMPANY)

    def test_batch_calculation(self, wht_calc):
        result = wht_calc.calculate_batch([
            {"amount": 1_000_000, "payment_type": "contract", "recipient_type": "company"},
            {"amount": 500_000, "payment_type": "consultancy", "recipient_type": "individual"},
        ])
        assert result.total_gross == 1_500_000
        assert result.total_wht == 125_000
        assert result.total_net == 1_375_000
