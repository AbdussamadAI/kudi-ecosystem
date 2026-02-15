"""
Tax calculation API routes.
Exposes KudiCore tax calculators via REST endpoints.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends

from app.api.auth import get_current_user
from app.schemas.schemas import (
    PITCalculateRequest,
    CITCalculateRequest,
    VATCalculateRequest,
    WHTCalculateRequest,
    ScenarioRequest,
)
from app.core.tax_rules.pit import PITCalculator, Deductions
from app.core.tax_rules.cit import CITCalculator
from app.core.tax_rules.vat import VATCalculator
from app.core.tax_rules.wht import WHTCalculator, WHTPaymentType, RecipientType
from app.core.scenario import ScenarioModeler
from app.core.anomaly import AnomalyDetector

router = APIRouter()

pit_calc = PITCalculator()
cit_calc = CITCalculator()
vat_calc = VATCalculator()
wht_calc = WHTCalculator()
scenario_modeler = ScenarioModeler()
anomaly_detector = AnomalyDetector()


@router.post("/pit/calculate")
async def calculate_pit(data: PITCalculateRequest):
    """Calculate Personal Income Tax based on Nigeria Tax Act 2025."""
    try:
        deductions = Deductions(
            pension=data.pension,
            nhf=data.nhf,
            nhis=data.nhis,
            life_insurance=data.life_insurance,
            housing_loan_interest=data.housing_loan_interest,
            annual_rent_paid=data.annual_rent_paid,
        )
        result = pit_calc.calculate(
            gross_income=data.gross_income,
            deductions=deductions,
            is_minimum_wage_earner=data.is_minimum_wage,
        )
        return asdict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cit/calculate")
async def calculate_cit(data: CITCalculateRequest):
    """Calculate Company Income Tax based on Nigeria Tax Act 2025."""
    try:
        result = cit_calc.calculate(
            gross_profit=data.gross_profit,
            allowable_deductions=data.allowable_deductions,
            annual_turnover=data.annual_turnover,
            is_mne=data.is_mne,
        )
        return asdict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/vat/calculate")
async def calculate_vat(data: VATCalculateRequest):
    """Calculate Value Added Tax at 7.5%."""
    try:
        if data.is_inclusive:
            return vat_calc.extract_vat_from_inclusive(data.amount)
        return vat_calc.calculate_simple(data.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/wht/calculate")
async def calculate_wht(data: WHTCalculateRequest):
    """Calculate Withholding Tax."""
    try:
        result = wht_calc.calculate_single(
            gross_amount=data.gross_amount,
            payment_type=WHTPaymentType(data.payment_type),
            recipient_type=RecipientType(data.recipient_type),
        )
        return asdict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scenario")
async def run_scenario(data: ScenarioRequest):
    """Run a what-if tax scenario comparison."""
    try:
        if data.scenario_type == "income_change":
            result = scenario_modeler.compare_income_change(
                current_income=data.current_income,
                projected_income=data.projected_income or data.current_income,
            )
        elif data.scenario_type == "deduction_impact":
            current_ded = Deductions(**(data.current_deductions or {}))
            projected_ded = Deductions(**(data.projected_deductions or {}))
            result = scenario_modeler.compare_deduction_impact(
                gross_income=data.current_income,
                current_deductions=current_ded,
                projected_deductions=projected_ded,
            )
        elif data.scenario_type == "individual_vs_company":
            result = scenario_modeler.compare_individual_vs_company(
                gross_income=data.current_income,
                business_expenses=data.business_expenses,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Unknown scenario type: {data.scenario_type}")

        return asdict(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/alerts")
async def get_tax_alerts(current_user=Depends(get_current_user)):
    """Get anomaly detection alerts for the current user."""
    from app.api.auth import get_supabase
    supabase = get_supabase()

    try:
        user_data = supabase.table("users").select("user_type").eq(
            "supabase_id", str(current_user.id)
        ).single().execute()

        user_type = user_data.data.get("user_type", "individual") if user_data.data else "individual"

        alerts = anomaly_detector.check_filing_deadlines(
            user_type=user_type,
            filed_returns=[],
        )

        alerts.extend(anomaly_detector.check_missed_deductions(
            user_type=user_type,
            claimed_deductions=[],
            has_salary_income=user_type == "individual",
        ))

        return {
            "alerts": [asdict(a) for a in alerts],
            "total": len(alerts),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get alerts: {str(e)}")


@router.get("/paye/estimate")
async def estimate_paye(
    monthly_gross: float,
    pension: float = 0,
    nhf: float = 0,
    nhis: float = 0,
    current_user=Depends(get_current_user),
):
    """Estimate monthly PAYE deduction from salary."""
    try:
        deductions = Deductions(pension=pension * 12, nhf=nhf * 12, nhis=nhis * 12)
        result = pit_calc.estimate_monthly_paye(monthly_gross, deductions)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
