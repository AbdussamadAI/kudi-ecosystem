"""
Report Generator
Generates tax summary reports and compliance checklists as structured data.
PDF rendering is handled separately via weasyprint.

Report Types:
  - Tax Summary Report (annual/quarterly)
  - Compliance Checklist
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class TaxSummaryLine:
    label: str
    amount: float
    note: str = ""


@dataclass
class TaxSummaryReport:
    user_name: str
    user_type: str
    report_period: str
    year: int
    generated_at: str
    total_income: float
    income_breakdown: list[TaxSummaryLine] = field(default_factory=list)
    total_deductions: float = 0.0
    deduction_breakdown: list[TaxSummaryLine] = field(default_factory=list)
    taxable_income: float = 0.0
    pit_liability: float = 0.0
    cit_liability: float = 0.0
    vat_liability: float = 0.0
    wht_deducted: float = 0.0
    development_levy: float = 0.0
    total_tax_liability: float = 0.0
    effective_rate: float = 0.0
    pit_breakdown: list[dict] = field(default_factory=list)
    disclaimer: str = (
        "DISCLAIMER: This report is generated for educational and informational purposes only. "
        "It does not constitute professional tax advice. Please consult a qualified tax professional "
        "for advice specific to your situation. KudiWise is not liable for any decisions made based "
        "on this report."
    )


@dataclass
class ComplianceChecklistItem:
    title: str
    description: str
    due_date: str | None
    status: str
    tax_type: str
    action_required: str


@dataclass
class ComplianceChecklist:
    user_name: str
    user_type: str
    year: int
    generated_at: str
    items: list[ComplianceChecklistItem] = field(default_factory=list)
    summary: str = ""
    disclaimer: str = (
        "DISCLAIMER: This checklist is generated for educational and informational purposes only. "
        "Filing deadlines and requirements may change. Always verify with FIRS or a qualified "
        "tax professional."
    )


class ReportGenerator:
    """
    Generates structured report data from user financial information.
    The structured data can then be rendered as PDF or displayed in the dashboard.
    """

    def generate_tax_summary(
        self,
        user_name: str,
        user_type: str,
        year: int,
        income_data: list[dict],
        deduction_data: list[dict],
        tax_results: dict,
        period: str = "annual",
    ) -> TaxSummaryReport:
        income_breakdown = []
        total_income = 0.0
        for item in income_data:
            amount = item.get("amount", 0.0)
            total_income += amount
            income_breakdown.append(TaxSummaryLine(
                label=item.get("category", "Other"),
                amount=amount,
                note=item.get("note", ""),
            ))

        deduction_breakdown = []
        total_deductions = 0.0
        for item in deduction_data:
            amount = item.get("amount", 0.0)
            total_deductions += amount
            deduction_breakdown.append(TaxSummaryLine(
                label=item.get("type", "Other"),
                amount=amount,
                note=item.get("note", ""),
            ))

        taxable_income = max(total_income - total_deductions, 0.0)

        pit_liability = tax_results.get("pit", 0.0)
        cit_liability = tax_results.get("cit", 0.0)
        vat_liability = tax_results.get("vat", 0.0)
        wht_deducted = tax_results.get("wht", 0.0)
        development_levy = tax_results.get("development_levy", 0.0)

        total_tax = pit_liability + cit_liability + vat_liability + development_levy
        effective_rate = (total_tax / total_income * 100) if total_income > 0 else 0.0

        return TaxSummaryReport(
            user_name=user_name,
            user_type=user_type,
            report_period=period,
            year=year,
            generated_at=datetime.now().isoformat(),
            total_income=round(total_income, 2),
            income_breakdown=income_breakdown,
            total_deductions=round(total_deductions, 2),
            deduction_breakdown=deduction_breakdown,
            taxable_income=round(taxable_income, 2),
            pit_liability=round(pit_liability, 2),
            cit_liability=round(cit_liability, 2),
            vat_liability=round(vat_liability, 2),
            wht_deducted=round(wht_deducted, 2),
            development_levy=round(development_levy, 2),
            total_tax_liability=round(total_tax, 2),
            effective_rate=round(effective_rate, 2),
            pit_breakdown=tax_results.get("pit_breakdown", []),
        )

    def generate_compliance_checklist(
        self,
        user_name: str,
        user_type: str,
        year: int,
        filed_returns: list[str] | None = None,
        current_date: date | None = None,
    ) -> ComplianceChecklist:
        if filed_returns is None:
            filed_returns = []
        if current_date is None:
            current_date = date.today()

        items = []

        if user_type in ["individual", "freelancer"]:
            pit_deadline = date(year + 1, 3, 31)
            pit_status = "completed" if "pit_annual" in filed_returns else (
                "overdue" if current_date > pit_deadline else "pending"
            )
            items.append(ComplianceChecklistItem(
                title="Annual Personal Income Tax Return",
                description=f"File your {year} PIT return with the relevant State Internal Revenue Service.",
                due_date=pit_deadline.isoformat(),
                status=pit_status,
                tax_type="PIT",
                action_required="File Form A (Self-Assessment) with your state tax authority" if pit_status != "completed" else "None — already filed",
            ))

            items.append(ComplianceChecklistItem(
                title="Tax Clearance Certificate",
                description="Obtain TCC showing taxes paid for the past 3 years.",
                due_date=None,
                status="pending" if "tcc" not in filed_returns else "completed",
                tax_type="PIT",
                action_required="Apply for TCC from your state tax authority after filing returns",
            ))

        if user_type == "sme":
            cit_deadline = date(year + 1, 6, 30)
            cit_status = "completed" if "cit_annual" in filed_returns else (
                "overdue" if current_date > cit_deadline else "pending"
            )
            items.append(ComplianceChecklistItem(
                title="Annual Company Income Tax Return",
                description=f"File your {year} CIT return with FIRS.",
                due_date=cit_deadline.isoformat(),
                status=cit_status,
                tax_type="CIT",
                action_required="File via FIRS TaxPro Max portal" if cit_status != "completed" else "None — already filed",
            ))

            items.append(ComplianceChecklistItem(
                title="Monthly VAT Returns",
                description="File and remit VAT collected on taxable supplies by the 21st of the following month.",
                due_date=f"{year}-XX-21 (monthly)",
                status="pending",
                tax_type="VAT",
                action_required="File monthly VAT returns via FIRS TaxPro Max",
            ))

            items.append(ComplianceChecklistItem(
                title="Monthly WHT Remittance",
                description="Remit withholding tax deducted at source by the 21st of the following month.",
                due_date=f"{year}-XX-21 (monthly)",
                status="pending",
                tax_type="WHT",
                action_required="Remit WHT and file returns via FIRS TaxPro Max",
            ))

            items.append(ComplianceChecklistItem(
                title="Development Levy",
                description="4% development levy on assessable profits (non-small companies).",
                due_date=date(year + 1, 6, 30).isoformat(),
                status="pending" if "development_levy" not in filed_returns else "completed",
                tax_type="Development Levy",
                action_required="Paid alongside CIT return",
            ))

        completed = sum(1 for i in items if i.status == "completed")
        total = len(items)
        summary = f"{completed}/{total} compliance items completed for {year}."

        return ComplianceChecklist(
            user_name=user_name,
            user_type=user_type,
            year=year,
            generated_at=datetime.now().isoformat(),
            items=items,
            summary=summary,
        )
