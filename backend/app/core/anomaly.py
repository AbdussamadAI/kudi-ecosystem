"""
Anomaly Detection Engine
Monitors user transactions and tax data to flag potential issues.

Features:
  - Missed deduction detection
  - Filing deadline alerts
  - Unusual transaction patterns
  - Potential audit triggers
  - Income/expense ratio anomalies
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(str, Enum):
    MISSED_DEDUCTION = "missed_deduction"
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_OVERDUE = "deadline_overdue"
    UNUSUAL_TRANSACTION = "unusual_transaction"
    INCOME_SPIKE = "income_spike"
    UNCLASSIFIED_TRANSACTION = "unclassified_transaction"
    HIGH_EXPENSE_RATIO = "high_expense_ratio"
    MISSING_VAT_REMITTANCE = "missing_vat_remittance"
    WHT_CERTIFICATE_MISSING = "wht_certificate_missing"
    POTENTIAL_AUDIT_TRIGGER = "potential_audit_trigger"


@dataclass
class Alert:
    alert_type: AlertType
    severity: AlertSeverity
    title: str
    message: str
    recommendation: str
    data: dict = field(default_factory=dict)


FILING_DEADLINES = {
    "pit_annual": {"month": 3, "day": 31, "description": "Annual PIT return filing deadline"},
    "cit_annual": {"month": 6, "day": 30, "description": "Annual CIT return filing deadline (6 months after year-end)"},
    "vat_monthly": {"day": 21, "description": "Monthly VAT remittance deadline (21st of following month)"},
    "wht_monthly": {"day": 21, "description": "Monthly WHT remittance deadline (21st of following month)"},
    "development_levy": {"month": 6, "day": 30, "description": "Development levy payment deadline"},
}

COMMON_DEDUCTIONS = [
    {
        "type": "pension",
        "name": "Pension Contribution",
        "description": "Employee pension contribution under the Pension Reform Act",
        "applies_to": ["individual", "freelancer"],
    },
    {
        "type": "nhf",
        "name": "National Housing Fund",
        "description": "NHF contribution (2.5% of basic salary)",
        "applies_to": ["individual"],
    },
    {
        "type": "nhis",
        "name": "National Health Insurance",
        "description": "NHIS contribution",
        "applies_to": ["individual", "freelancer"],
    },
    {
        "type": "life_insurance",
        "name": "Life Insurance Premium",
        "description": "Annual life insurance premium (self or spouse)",
        "applies_to": ["individual", "freelancer", "sme"],
    },
    {
        "type": "rent_relief",
        "name": "Rent Relief",
        "description": "20% of annual rent paid (max ₦500,000)",
        "applies_to": ["individual", "freelancer"],
    },
]


class AnomalyDetector:
    """
    Detects anomalies and generates alerts for users based on their
    financial data and compliance obligations.
    """

    def check_missed_deductions(
        self,
        user_type: str,
        claimed_deductions: list[str],
        has_salary_income: bool = False,
    ) -> list[Alert]:
        alerts = []

        for deduction in COMMON_DEDUCTIONS:
            if user_type not in deduction["applies_to"]:
                continue
            if deduction["type"] in claimed_deductions:
                continue

            if deduction["type"] == "nhf" and not has_salary_income:
                continue

            alerts.append(Alert(
                alert_type=AlertType.MISSED_DEDUCTION,
                severity=AlertSeverity.WARNING,
                title=f"Potential missed deduction: {deduction['name']}",
                message=f"You haven't claimed {deduction['name']}. {deduction['description']}.",
                recommendation=f"If you make {deduction['name'].lower()} payments, add them as deductions to reduce your tax liability.",
                data={"deduction_type": deduction["type"]},
            ))

        return alerts

    def check_filing_deadlines(
        self,
        user_type: str,
        current_date: date | None = None,
        filed_returns: list[str] | None = None,
    ) -> list[Alert]:
        if current_date is None:
            current_date = date.today()
        if filed_returns is None:
            filed_returns = []

        alerts = []
        year = current_date.year

        relevant_deadlines = []
        if user_type in ["individual", "freelancer"]:
            relevant_deadlines.append(("pit_annual", FILING_DEADLINES["pit_annual"]))
        if user_type == "sme":
            relevant_deadlines.append(("cit_annual", FILING_DEADLINES["cit_annual"]))
            relevant_deadlines.append(("vat_monthly", FILING_DEADLINES["vat_monthly"]))
            relevant_deadlines.append(("wht_monthly", FILING_DEADLINES["wht_monthly"]))
            relevant_deadlines.append(("development_levy", FILING_DEADLINES["development_levy"]))

        for deadline_key, deadline_info in relevant_deadlines:
            if deadline_key in filed_returns:
                continue

            if "month" in deadline_info:
                deadline_date = date(year, deadline_info["month"], deadline_info["day"])
            else:
                next_month = current_date.month + 1 if current_date.month < 12 else 1
                next_year = year if current_date.month < 12 else year + 1
                deadline_date = date(next_year, next_month, deadline_info["day"])

            days_until = (deadline_date - current_date).days

            if days_until < 0:
                alerts.append(Alert(
                    alert_type=AlertType.DEADLINE_OVERDUE,
                    severity=AlertSeverity.CRITICAL,
                    title=f"OVERDUE: {deadline_info['description']}",
                    message=f"This deadline was {abs(days_until)} days ago ({deadline_date.isoformat()}). Late filing may attract penalties.",
                    recommendation="File your return immediately to minimize penalties and interest charges.",
                    data={"deadline_key": deadline_key, "deadline_date": deadline_date.isoformat(), "days_overdue": abs(days_until)},
                ))
            elif days_until <= 30:
                alerts.append(Alert(
                    alert_type=AlertType.DEADLINE_APPROACHING,
                    severity=AlertSeverity.WARNING if days_until > 7 else AlertSeverity.CRITICAL,
                    title=f"Upcoming: {deadline_info['description']}",
                    message=f"Due in {days_until} days ({deadline_date.isoformat()}).",
                    recommendation="Prepare your documents and file before the deadline to avoid penalties.",
                    data={"deadline_key": deadline_key, "deadline_date": deadline_date.isoformat(), "days_remaining": days_until},
                ))

        return alerts

    def check_transaction_anomalies(
        self,
        transactions: list[dict],
        average_monthly_income: float = 0.0,
    ) -> list[Alert]:
        alerts = []

        unclassified = [t for t in transactions if t.get("classification") == "unknown"]
        if unclassified:
            alerts.append(Alert(
                alert_type=AlertType.UNCLASSIFIED_TRANSACTION,
                severity=AlertSeverity.INFO,
                title=f"{len(unclassified)} unclassified transaction(s)",
                message="Some transactions haven't been classified. This may affect your tax calculations.",
                recommendation="Review and classify these transactions for accurate tax reporting.",
                data={"count": len(unclassified)},
            ))

        for txn in transactions:
            amount = txn.get("amount", 0)
            if average_monthly_income > 0 and amount > average_monthly_income * 3:
                alerts.append(Alert(
                    alert_type=AlertType.UNUSUAL_TRANSACTION,
                    severity=AlertSeverity.WARNING,
                    title=f"Large transaction detected: ₦{amount:,.2f}",
                    message=f"Transaction '{txn.get('description', 'N/A')}' is significantly larger than your average monthly income.",
                    recommendation="Ensure this transaction is correctly classified. Large unusual transactions may attract scrutiny.",
                    data={"transaction_id": txn.get("id"), "amount": amount},
                ))

        total_income = sum(t.get("amount", 0) for t in transactions if t.get("type") == "income")
        total_expense = sum(t.get("amount", 0) for t in transactions if t.get("type") == "expense")

        if total_income > 0 and total_expense / total_income > 0.9:
            alerts.append(Alert(
                alert_type=AlertType.HIGH_EXPENSE_RATIO,
                severity=AlertSeverity.WARNING,
                title="High expense-to-income ratio",
                message=f"Your expenses ({total_expense:,.2f}) are {total_expense/total_income*100:.0f}% of your income. This may trigger audit attention.",
                recommendation="Review your expense classifications. Ensure all business expenses are properly documented.",
                data={"expense_ratio": round(total_expense / total_income, 2)},
            ))

        return alerts

    def run_all_checks(
        self,
        user_type: str,
        claimed_deductions: list[str],
        has_salary_income: bool,
        filed_returns: list[str],
        transactions: list[dict],
        average_monthly_income: float,
        current_date: date | None = None,
    ) -> list[Alert]:
        all_alerts = []
        all_alerts.extend(self.check_missed_deductions(user_type, claimed_deductions, has_salary_income))
        all_alerts.extend(self.check_filing_deadlines(user_type, current_date, filed_returns))
        all_alerts.extend(self.check_transaction_anomalies(transactions, average_monthly_income))

        all_alerts.sort(key=lambda a: {"critical": 0, "warning": 1, "info": 2}[a.severity.value])
        return all_alerts
