"""
Transaction Classifier Engine
Classifies transactions into income/expense categories, determines tax relevance,
and separates capital from profit.

Classification logic:
  - Income: salary, freelance, business, investment, rental, capital gains, forex, crypto, dividend
  - Expense: business, personal, deductible, non-deductible
  - Tax flags: VAT-applicable, WHT-applicable, exempt
  - Capital vs Profit distinction (critical for KudiCore vision)
"""

from dataclasses import dataclass
from enum import Enum


class TransactionClassification(str, Enum):
    INCOME_SALARY = "income_salary"
    INCOME_FREELANCE = "income_freelance"
    INCOME_BUSINESS = "income_business"
    INCOME_INVESTMENT = "income_investment"
    INCOME_RENTAL = "income_rental"
    INCOME_CAPITAL_GAINS = "income_capital_gains"
    INCOME_FOREX_GAINS = "income_forex_gains"
    INCOME_CRYPTO_GAINS = "income_crypto_gains"
    INCOME_DIVIDEND = "income_dividend"
    INCOME_OTHER = "income_other"
    EXPENSE_BUSINESS = "expense_business"
    EXPENSE_PERSONAL = "expense_personal"
    EXPENSE_DEDUCTIBLE = "expense_deductible"
    EXPENSE_NON_DEDUCTIBLE = "expense_non_deductible"
    CAPITAL_INFLOW = "capital_inflow"
    CAPITAL_OUTFLOW = "capital_outflow"
    TRANSFER = "transfer"
    UNKNOWN = "unknown"


INCOME_KEYWORDS = {
    "salary": TransactionClassification.INCOME_SALARY,
    "wage": TransactionClassification.INCOME_SALARY,
    "paye": TransactionClassification.INCOME_SALARY,
    "payroll": TransactionClassification.INCOME_SALARY,
    "freelance": TransactionClassification.INCOME_FREELANCE,
    "contract": TransactionClassification.INCOME_FREELANCE,
    "upwork": TransactionClassification.INCOME_FREELANCE,
    "fiverr": TransactionClassification.INCOME_FREELANCE,
    "toptal": TransactionClassification.INCOME_FREELANCE,
    "invoice": TransactionClassification.INCOME_FREELANCE,
    "consulting": TransactionClassification.INCOME_FREELANCE,
    "sales": TransactionClassification.INCOME_BUSINESS,
    "revenue": TransactionClassification.INCOME_BUSINESS,
    "business income": TransactionClassification.INCOME_BUSINESS,
    "interest": TransactionClassification.INCOME_INVESTMENT,
    "dividend": TransactionClassification.INCOME_DIVIDEND,
    "rental": TransactionClassification.INCOME_RENTAL,
    "rent received": TransactionClassification.INCOME_RENTAL,
    "property income": TransactionClassification.INCOME_RENTAL,
    "forex": TransactionClassification.INCOME_FOREX_GAINS,
    "fx gain": TransactionClassification.INCOME_FOREX_GAINS,
    "crypto": TransactionClassification.INCOME_CRYPTO_GAINS,
    "bitcoin": TransactionClassification.INCOME_CRYPTO_GAINS,
    "trading profit": TransactionClassification.INCOME_FOREX_GAINS,
}

EXPENSE_KEYWORDS = {
    "office": TransactionClassification.EXPENSE_BUSINESS,
    "equipment": TransactionClassification.EXPENSE_BUSINESS,
    "software": TransactionClassification.EXPENSE_BUSINESS,
    "subscription": TransactionClassification.EXPENSE_BUSINESS,
    "internet": TransactionClassification.EXPENSE_BUSINESS,
    "transport": TransactionClassification.EXPENSE_BUSINESS,
    "fuel": TransactionClassification.EXPENSE_BUSINESS,
    "travel": TransactionClassification.EXPENSE_BUSINESS,
    "advertising": TransactionClassification.EXPENSE_BUSINESS,
    "marketing": TransactionClassification.EXPENSE_BUSINESS,
    "rent paid": TransactionClassification.EXPENSE_DEDUCTIBLE,
    "pension": TransactionClassification.EXPENSE_DEDUCTIBLE,
    "nhf": TransactionClassification.EXPENSE_DEDUCTIBLE,
    "nhis": TransactionClassification.EXPENSE_DEDUCTIBLE,
    "insurance": TransactionClassification.EXPENSE_DEDUCTIBLE,
    "food": TransactionClassification.EXPENSE_PERSONAL,
    "groceries": TransactionClassification.EXPENSE_PERSONAL,
    "entertainment": TransactionClassification.EXPENSE_PERSONAL,
    "clothing": TransactionClassification.EXPENSE_PERSONAL,
}

CAPITAL_KEYWORDS = [
    "loan received",
    "capital injection",
    "investment deposit",
    "principal",
    "deposit",
    "funding",
    "equity",
    "loan repayment",
    "capital withdrawal",
]

VAT_APPLICABLE_CATEGORIES = [
    TransactionClassification.INCOME_BUSINESS,
    TransactionClassification.INCOME_FREELANCE,
    TransactionClassification.EXPENSE_BUSINESS,
]

WHT_APPLICABLE_CATEGORIES = [
    TransactionClassification.INCOME_FREELANCE,
    TransactionClassification.INCOME_RENTAL,
    TransactionClassification.INCOME_DIVIDEND,
    TransactionClassification.INCOME_INVESTMENT,
]


@dataclass
class ClassificationResult:
    classification: TransactionClassification
    confidence: float
    is_income: bool
    is_expense: bool
    is_capital: bool
    is_vat_applicable: bool
    is_wht_applicable: bool
    is_taxable: bool
    suggested_category: str
    reasoning: str


class TransactionClassifier:
    """
    Rule-based transaction classifier.
    Uses keyword matching for initial classification.
    AI-enhanced classification is handled by the AI layer calling this as a tool.
    """

    def classify(
        self,
        description: str,
        amount: float,
        is_credit: bool = True,
    ) -> ClassificationResult:
        desc_lower = description.lower().strip()

        for keyword in CAPITAL_KEYWORDS:
            if keyword in desc_lower:
                is_inflow = is_credit
                classification = (
                    TransactionClassification.CAPITAL_INFLOW
                    if is_inflow
                    else TransactionClassification.CAPITAL_OUTFLOW
                )
                return ClassificationResult(
                    classification=classification,
                    confidence=0.7,
                    is_income=False,
                    is_expense=False,
                    is_capital=True,
                    is_vat_applicable=False,
                    is_wht_applicable=False,
                    is_taxable=False,
                    suggested_category="capital",
                    reasoning=f"Matched capital keyword: '{keyword}'",
                )

        if is_credit:
            for keyword, classification in INCOME_KEYWORDS.items():
                if keyword in desc_lower:
                    return ClassificationResult(
                        classification=classification,
                        confidence=0.75,
                        is_income=True,
                        is_expense=False,
                        is_capital=False,
                        is_vat_applicable=classification in VAT_APPLICABLE_CATEGORIES,
                        is_wht_applicable=classification in WHT_APPLICABLE_CATEGORIES,
                        is_taxable=True,
                        suggested_category=classification.value.replace("income_", ""),
                        reasoning=f"Matched income keyword: '{keyword}'",
                    )

            return ClassificationResult(
                classification=TransactionClassification.INCOME_OTHER,
                confidence=0.3,
                is_income=True,
                is_expense=False,
                is_capital=False,
                is_vat_applicable=False,
                is_wht_applicable=False,
                is_taxable=True,
                suggested_category="other_income",
                reasoning="No specific keyword matched; classified as other income",
            )
        else:
            for keyword, classification in EXPENSE_KEYWORDS.items():
                if keyword in desc_lower:
                    return ClassificationResult(
                        classification=classification,
                        confidence=0.75,
                        is_income=False,
                        is_expense=True,
                        is_capital=False,
                        is_vat_applicable=classification in VAT_APPLICABLE_CATEGORIES,
                        is_wht_applicable=False,
                        is_taxable=False,
                        suggested_category=classification.value.replace("expense_", ""),
                        reasoning=f"Matched expense keyword: '{keyword}'",
                    )

            return ClassificationResult(
                classification=TransactionClassification.EXPENSE_PERSONAL,
                confidence=0.3,
                is_income=False,
                is_expense=True,
                is_capital=False,
                is_vat_applicable=False,
                is_wht_applicable=False,
                is_taxable=False,
                suggested_category="personal",
                reasoning="No specific keyword matched; classified as personal expense",
            )

    def is_capital_vs_profit(self, description: str, amount: float) -> dict:
        desc_lower = description.lower()
        is_capital = any(kw in desc_lower for kw in CAPITAL_KEYWORDS)

        return {
            "is_capital": is_capital,
            "is_profit": not is_capital,
            "reasoning": (
                "Transaction appears to be capital (principal/deposit/loan)"
                if is_capital
                else "Transaction appears to be profit/income"
            ),
        }
