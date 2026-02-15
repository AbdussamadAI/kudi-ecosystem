"""
Withholding Tax (WHT) Calculator
Based on Nigeria Tax Act 2025

WHT is deducted at source on certain payments. Rates vary by payment type
and whether the recipient is a company or individual.

Common WHT Rates:
  - Dividends, interest, rent: 10%
  - Royalties: 10%
  - Commission, consultancy, professional fees: 10% (companies), 5% (individuals)
  - Construction/building: 5% (companies), 5% (individuals)
  - Supply of goods: 5% (companies), 5% (individuals)
  - All types of contracts/agency arrangements: 10%
  - Directors' fees: 10%
"""

from dataclasses import dataclass, field
from enum import Enum


class RecipientType(str, Enum):
    INDIVIDUAL = "individual"
    COMPANY = "company"


class WHTPaymentType(str, Enum):
    DIVIDEND = "dividend"
    INTEREST = "interest"
    RENT = "rent"
    ROYALTY = "royalty"
    COMMISSION = "commission"
    CONSULTANCY = "consultancy"
    PROFESSIONAL_FEES = "professional_fees"
    TECHNICAL_FEES = "technical_fees"
    MANAGEMENT_FEES = "management_fees"
    CONSTRUCTION = "construction"
    SUPPLY_OF_GOODS = "supply_of_goods"
    CONTRACT = "contract"
    DIRECTORS_FEES = "directors_fees"


WHT_RATES: dict[WHTPaymentType, dict[RecipientType, float]] = {
    WHTPaymentType.DIVIDEND: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
    WHTPaymentType.INTEREST: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
    WHTPaymentType.RENT: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
    WHTPaymentType.ROYALTY: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
    WHTPaymentType.COMMISSION: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.10},
    WHTPaymentType.CONSULTANCY: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.10},
    WHTPaymentType.PROFESSIONAL_FEES: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.10},
    WHTPaymentType.TECHNICAL_FEES: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.10},
    WHTPaymentType.MANAGEMENT_FEES: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.10},
    WHTPaymentType.CONSTRUCTION: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.05},
    WHTPaymentType.SUPPLY_OF_GOODS: {RecipientType.INDIVIDUAL: 0.05, RecipientType.COMPANY: 0.05},
    WHTPaymentType.CONTRACT: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
    WHTPaymentType.DIRECTORS_FEES: {RecipientType.INDIVIDUAL: 0.10, RecipientType.COMPANY: 0.10},
}


@dataclass
class WHTLineItem:
    payment_type: WHTPaymentType
    recipient_type: RecipientType
    gross_amount: float
    wht_rate: float
    wht_amount: float
    net_amount: float


@dataclass
class WHTResult:
    total_gross: float
    total_wht: float
    total_net: float
    line_items: list[WHTLineItem] = field(default_factory=list)
    breakdown: dict = field(default_factory=dict)


class WHTCalculator:
    """
    Deterministic Withholding Tax calculator for Nigerian transactions.
    All calculations follow the Nigeria Tax Act 2025.
    """

    def get_rate(self, payment_type: WHTPaymentType, recipient_type: RecipientType) -> float:
        rates = WHT_RATES.get(payment_type)
        if rates is None:
            raise ValueError(f"Unknown payment type: {payment_type}")
        return rates.get(recipient_type, 0.10)

    def calculate_single(
        self,
        gross_amount: float,
        payment_type: WHTPaymentType,
        recipient_type: RecipientType = RecipientType.COMPANY,
    ) -> WHTLineItem:
        if gross_amount < 0:
            raise ValueError("Gross amount cannot be negative")

        rate = self.get_rate(payment_type, recipient_type)
        wht_amount = round(gross_amount * rate, 2)
        net_amount = round(gross_amount - wht_amount, 2)

        return WHTLineItem(
            payment_type=payment_type,
            recipient_type=recipient_type,
            gross_amount=gross_amount,
            wht_rate=rate,
            wht_amount=wht_amount,
            net_amount=net_amount,
        )

    def calculate_batch(
        self,
        payments: list[dict],
    ) -> WHTResult:
        line_items = []
        total_gross = 0.0
        total_wht = 0.0

        for payment in payments:
            gross = payment.get("amount", 0.0)
            ptype = WHTPaymentType(payment.get("payment_type", "contract"))
            rtype = RecipientType(payment.get("recipient_type", "company"))

            item = self.calculate_single(gross, ptype, rtype)
            line_items.append(item)
            total_gross += gross
            total_wht += item.wht_amount

        total_net = round(total_gross - total_wht, 2)

        breakdown_by_type = {}
        for item in line_items:
            key = item.payment_type.value
            if key not in breakdown_by_type:
                breakdown_by_type[key] = {"gross": 0.0, "wht": 0.0, "rate": item.wht_rate * 100}
            breakdown_by_type[key]["gross"] += item.gross_amount
            breakdown_by_type[key]["wht"] += item.wht_amount

        return WHTResult(
            total_gross=round(total_gross, 2),
            total_wht=round(total_wht, 2),
            total_net=total_net,
            line_items=line_items,
            breakdown=breakdown_by_type,
        )
