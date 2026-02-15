"""
Scenario Modeler ("What-If" Engine)
Allows users to model different financial scenarios and see the tax impact.

Examples:
  - "What if I earn ₦5M more next year?"
  - "What if I register as a company instead of filing as an individual?"
  - "What if I claim all my deductions?"
  - "What if I add a new income stream?"
"""

from dataclasses import dataclass, field

from app.core.tax_rules.pit import PITCalculator, Deductions
from app.core.tax_rules.cit import CITCalculator, CompanySize


@dataclass
class ScenarioComparison:
    label: str
    current_tax: float
    projected_tax: float
    difference: float
    percentage_change: float
    current_effective_rate: float
    projected_effective_rate: float
    insights: list[str] = field(default_factory=list)


@dataclass
class ScenarioInput:
    scenario_type: str
    current_gross_income: float
    current_deductions: Deductions | None = None
    projected_gross_income: float | None = None
    projected_deductions: Deductions | None = None
    company_turnover: float | None = None
    company_profit: float | None = None
    is_minimum_wage: bool = False


class ScenarioModeler:
    """
    Models different financial scenarios and compares tax outcomes.
    Uses KudiCore tax calculators for all computations.
    """

    def __init__(self):
        self.pit_calc = PITCalculator()
        self.cit_calc = CITCalculator()

    def compare_income_change(
        self,
        current_income: float,
        projected_income: float,
        deductions: Deductions | None = None,
    ) -> ScenarioComparison:
        current = self.pit_calc.calculate(current_income, deductions)
        projected = self.pit_calc.calculate(projected_income, deductions)

        difference = projected.tax_liability - current.tax_liability
        pct_change = (
            (difference / current.tax_liability * 100) if current.tax_liability > 0 else 0.0
        )

        insights = []
        if difference > 0:
            insights.append(
                f"Increasing your income by ₦{projected_income - current_income:,.2f} "
                f"would increase your tax by ₦{difference:,.2f}."
            )
        elif difference < 0:
            insights.append(
                f"Decreasing your income by ₦{current_income - projected_income:,.2f} "
                f"would save you ₦{abs(difference):,.2f} in taxes."
            )

        if projected.effective_rate > current.effective_rate:
            insights.append(
                f"Your effective tax rate would increase from {current.effective_rate}% "
                f"to {projected.effective_rate}%."
            )

        marginal_tax = difference
        marginal_income = projected_income - current_income
        if marginal_income > 0:
            marginal_rate = marginal_tax / marginal_income * 100
            insights.append(
                f"The marginal tax rate on the additional ₦{marginal_income:,.2f} "
                f"is {marginal_rate:.1f}%."
            )

        return ScenarioComparison(
            label="Income Change Scenario",
            current_tax=current.tax_liability,
            projected_tax=projected.tax_liability,
            difference=round(difference, 2),
            percentage_change=round(pct_change, 2),
            current_effective_rate=current.effective_rate,
            projected_effective_rate=projected.effective_rate,
            insights=insights,
        )

    def compare_deduction_impact(
        self,
        gross_income: float,
        current_deductions: Deductions,
        projected_deductions: Deductions,
    ) -> ScenarioComparison:
        current = self.pit_calc.calculate(gross_income, current_deductions)
        projected = self.pit_calc.calculate(gross_income, projected_deductions)

        difference = projected.tax_liability - current.tax_liability
        pct_change = (
            (difference / current.tax_liability * 100) if current.tax_liability > 0 else 0.0
        )

        insights = []
        additional_deductions = projected_deductions.total - current_deductions.total
        if additional_deductions > 0 and difference < 0:
            insights.append(
                f"Claiming an additional ₦{additional_deductions:,.2f} in deductions "
                f"would save you ₦{abs(difference):,.2f} in taxes."
            )

        if current_deductions.annual_rent_paid == 0 and projected_deductions.annual_rent_paid > 0:
            insights.append(
                f"Adding rent relief (₦{projected_deductions.rent_relief:,.2f}) "
                f"contributes to your tax savings."
            )

        if current_deductions.pension == 0 and projected_deductions.pension > 0:
            insights.append(
                f"Pension contributions of ₦{projected_deductions.pension:,.2f} "
                f"are tax-deductible and reduce your liability."
            )

        return ScenarioComparison(
            label="Deduction Impact Scenario",
            current_tax=current.tax_liability,
            projected_tax=projected.tax_liability,
            difference=round(difference, 2),
            percentage_change=round(pct_change, 2),
            current_effective_rate=current.effective_rate,
            projected_effective_rate=projected.effective_rate,
            insights=insights,
        )

    def compare_individual_vs_company(
        self,
        gross_income: float,
        deductions: Deductions | None = None,
        business_expenses: float = 0.0,
    ) -> ScenarioComparison:
        pit_result = self.pit_calc.calculate(gross_income, deductions)

        company_profit = gross_income - business_expenses
        cit_result = self.cit_calc.calculate(
            gross_profit=company_profit,
            annual_turnover=gross_income,
        )

        difference = cit_result.total_tax_liability - pit_result.tax_liability
        pct_change = (
            (difference / pit_result.tax_liability * 100) if pit_result.tax_liability > 0 else 0.0
        )

        insights = []
        if cit_result.company_size == CompanySize.SMALL:
            insights.append(
                f"As a small company (turnover ≤ ₦25M), your CIT rate would be 0%. "
                f"You'd save ₦{abs(difference):,.2f} compared to individual filing."
            )
        elif difference < 0:
            insights.append(
                f"Registering as a company could save you ₦{abs(difference):,.2f} in taxes."
            )
        else:
            insights.append(
                f"Filing as an individual is currently more tax-efficient, "
                f"saving you ₦{difference:,.2f} compared to company filing."
            )

        insights.append(
            f"Individual effective rate: {pit_result.effective_rate}% | "
            f"Company effective rate: {cit_result.effective_rate}%"
        )

        if business_expenses > 0:
            insights.append(
                f"Note: Company calculation accounts for ₦{business_expenses:,.2f} "
                f"in business expenses, reducing assessable profit to ₦{company_profit:,.2f}."
            )

        return ScenarioComparison(
            label="Individual vs Company Scenario",
            current_tax=pit_result.tax_liability,
            projected_tax=cit_result.total_tax_liability,
            difference=round(difference, 2),
            percentage_change=round(pct_change, 2),
            current_effective_rate=pit_result.effective_rate,
            projected_effective_rate=cit_result.effective_rate,
            insights=insights,
        )

    def run_scenario(self, scenario_input: ScenarioInput) -> ScenarioComparison:
        if scenario_input.scenario_type == "income_change":
            return self.compare_income_change(
                current_income=scenario_input.current_gross_income,
                projected_income=scenario_input.projected_gross_income or scenario_input.current_gross_income,
                deductions=scenario_input.current_deductions,
            )
        elif scenario_input.scenario_type == "deduction_impact":
            return self.compare_deduction_impact(
                gross_income=scenario_input.current_gross_income,
                current_deductions=scenario_input.current_deductions or Deductions(),
                projected_deductions=scenario_input.projected_deductions or Deductions(),
            )
        elif scenario_input.scenario_type == "individual_vs_company":
            return self.compare_individual_vs_company(
                gross_income=scenario_input.current_gross_income,
                deductions=scenario_input.current_deductions,
            )
        else:
            raise ValueError(f"Unknown scenario type: {scenario_input.scenario_type}")
