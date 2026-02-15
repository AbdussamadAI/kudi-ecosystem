"""
Value Added Tax (VAT) Calculator
Based on Nigeria Tax Act 2025, Chapter 6, Section 148

VAT Rate: 7.5% on taxable supplies

Key provisions:
  - Section 144: Imposition of VAT
  - Section 146: Taxable supplies
  - Section 148: Rate of VAT (7.5%)
  - Section 149: Value of taxable supplies
  - Section 156: Credit for input tax and remission of VAT
  - Section 186: Exempt supplies
  - Section 187: Zero-rated supplies (0%)
"""

from dataclasses import dataclass, field
from enum import Enum


class VATCategory(str, Enum):
    STANDARD = "standard"
    EXEMPT = "exempt"
    ZERO_RATED = "zero_rated"


VAT_RATE = 0.075
ZERO_RATE = 0.00

EXEMPT_CATEGORIES = [
    "medical_pharmaceutical",
    "basic_food_items",
    "books_educational_materials",
    "baby_products",
    "fertilizer_agricultural_equipment",
    "agricultural_produce",
    "veterinary_medicine",
    "farming_machinery",
    "locally_produced_sanitary_towels",
    "renewable_energy_equipment",
]

ZERO_RATED_CATEGORIES = [
    "non_oil_exports",
    "goods_services_to_free_trade_zones",
    "humanitarian_donor_funded_projects",
]


@dataclass
class VATLineItem:
    description: str
    amount: float
    category: VATCategory = VATCategory.STANDARD
    vat_amount: float = 0.0
    total_with_vat: float = 0.0


@dataclass
class VATResult:
    total_supplies: float
    taxable_supplies: float
    exempt_supplies: float
    zero_rated_supplies: float
    output_vat: float
    input_vat: float
    net_vat_payable: float
    effective_rate: float
    line_items: list[VATLineItem] = field(default_factory=list)
    breakdown: dict = field(default_factory=dict)


class VATCalculator:
    """
    Deterministic VAT calculator for Nigerian businesses.
    All calculations follow the Nigeria Tax Act 2025.
    """

    def classify_supply(self, category: str) -> VATCategory:
        if category.lower() in EXEMPT_CATEGORIES:
            return VATCategory.EXEMPT
        if category.lower() in ZERO_RATED_CATEGORIES:
            return VATCategory.ZERO_RATED
        return VATCategory.STANDARD

    def calculate_vat_on_supply(self, amount: float, category: VATCategory = VATCategory.STANDARD) -> float:
        if category == VATCategory.EXEMPT or category == VATCategory.ZERO_RATED:
            return 0.0
        return round(amount * VAT_RATE, 2)

    def calculate(
        self,
        output_supplies: list[dict] | None = None,
        input_purchases: list[dict] | None = None,
    ) -> VATResult:
        if output_supplies is None:
            output_supplies = []
        if input_purchases is None:
            input_purchases = []

        total_supplies = 0.0
        taxable_supplies = 0.0
        exempt_supplies = 0.0
        zero_rated_supplies = 0.0
        output_vat = 0.0
        line_items = []

        for supply in output_supplies:
            amount = supply.get("amount", 0.0)
            desc = supply.get("description", "")
            cat_str = supply.get("category", "standard")
            category = self.classify_supply(cat_str) if cat_str not in VATCategory.__members__.values() else VATCategory(cat_str)

            vat_amount = self.calculate_vat_on_supply(amount, category)
            total_supplies += amount

            if category == VATCategory.STANDARD:
                taxable_supplies += amount
                output_vat += vat_amount
            elif category == VATCategory.EXEMPT:
                exempt_supplies += amount
            elif category == VATCategory.ZERO_RATED:
                zero_rated_supplies += amount

            line_items.append(VATLineItem(
                description=desc,
                amount=amount,
                category=category,
                vat_amount=vat_amount,
                total_with_vat=amount + vat_amount,
            ))

        input_vat = 0.0
        for purchase in input_purchases:
            amount = purchase.get("amount", 0.0)
            cat_str = purchase.get("category", "standard")
            category = self.classify_supply(cat_str) if cat_str not in VATCategory.__members__.values() else VATCategory(cat_str)

            if category == VATCategory.STANDARD:
                input_vat += round(amount * VAT_RATE, 2)

        net_vat_payable = round(output_vat - input_vat, 2)
        effective_rate = (output_vat / taxable_supplies * 100) if taxable_supplies > 0 else 0.0

        breakdown = {
            "vat_rate": VAT_RATE * 100,
            "output_vat": round(output_vat, 2),
            "input_vat": round(input_vat, 2),
            "net_payable": net_vat_payable,
        }

        return VATResult(
            total_supplies=round(total_supplies, 2),
            taxable_supplies=round(taxable_supplies, 2),
            exempt_supplies=round(exempt_supplies, 2),
            zero_rated_supplies=round(zero_rated_supplies, 2),
            output_vat=round(output_vat, 2),
            input_vat=round(input_vat, 2),
            net_vat_payable=net_vat_payable,
            effective_rate=round(effective_rate, 2),
            line_items=line_items,
            breakdown=breakdown,
        )

    def calculate_simple(self, amount: float) -> dict:
        vat_amount = round(amount * VAT_RATE, 2)
        return {
            "amount": amount,
            "vat_rate": VAT_RATE * 100,
            "vat_amount": vat_amount,
            "total_with_vat": round(amount + vat_amount, 2),
        }

    def extract_vat_from_inclusive(self, inclusive_amount: float) -> dict:
        amount_before_vat = round(inclusive_amount / (1 + VAT_RATE), 2)
        vat_amount = round(inclusive_amount - amount_before_vat, 2)
        return {
            "inclusive_amount": inclusive_amount,
            "amount_before_vat": amount_before_vat,
            "vat_amount": vat_amount,
            "vat_rate": VAT_RATE * 100,
        }
