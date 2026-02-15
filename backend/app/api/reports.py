"""
Reports API routes.
Generates tax summary reports and compliance checklists.
"""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, Depends

from app.api.auth import get_current_user, get_supabase_admin
from app.schemas.schemas import ReportRequest
from app.core.reports import ReportGenerator
from app.core.tax_rules.pit import PITCalculator, Deductions
from app.core.tax_rules.cit import CITCalculator

router = APIRouter()
report_gen = ReportGenerator()
pit_calc = PITCalculator()
cit_calc = CITCalculator()


@router.post("/generate")
async def generate_report(data: ReportRequest, current_user=Depends(get_current_user)):
    """Generate a tax summary report or compliance checklist."""
    supabase = get_supabase_admin()

    try:
        try:
            user_data = supabase.table("users").select("*").eq(
                "supabase_id", str(current_user.id)
            ).maybe_single().execute()
        except Exception:
            user_data = None

        if not user_data or not user_data.data:
            # Return a minimal report without user data
            user_name = getattr(current_user, 'email', 'User')
            user_type = "individual"
            user_uuid = None
        else:
            user_name = user_data.data.get("full_name", "User")
            user_type = user_data.data.get("user_type", "individual")
            user_uuid = user_data.data.get("id")

        if data.report_type == "tax_summary":
            transactions = []
            if user_uuid:
                txn_result = supabase.table("transactions").select("*").eq(
                    "user_id", user_uuid
                ).gte("transaction_date", f"{data.year}-01-01").lte(
                    "transaction_date", f"{data.year}-12-31"
                ).execute()
                transactions = txn_result.data or []

            income_data = []
            for t in transactions:
                if t["transaction_type"] == "income":
                    income_data.append({
                        "category": t.get("income_category") or "other",
                        "amount": t["amount_ngn"],
                    })

            deduction_data = []
            if user_uuid:
                deduction_result = supabase.table("tax_deductions").select("*").eq(
                    "user_id", user_uuid
                ).eq("year", data.year).execute()

                for d in (deduction_result.data or []):
                    deduction_data.append({
                        "type": d.get("deduction_type", "other"),
                        "amount": d["amount"],
                    })

            total_income = sum(i["amount"] for i in income_data)
            total_deductions = sum(d["amount"] for d in deduction_data)

            tax_results = {"pit": 0, "cit": 0, "vat": 0, "wht": 0, "development_levy": 0, "pit_breakdown": []}

            if user_type in ["individual", "freelancer"]:
                pit_result = pit_calc.calculate(total_income, Deductions())
                tax_results["pit"] = pit_result.tax_liability
                tax_results["pit_breakdown"] = [asdict(b) for b in pit_result.bracket_breakdown]
            elif user_type == "sme":
                cit_result = cit_calc.calculate(gross_profit=total_income, allowable_deductions=total_deductions)
                tax_results["cit"] = cit_result.cit_liability
                tax_results["development_levy"] = cit_result.development_levy

            report = report_gen.generate_tax_summary(
                user_name=user_name,
                user_type=user_type,
                year=data.year,
                income_data=income_data,
                deduction_data=deduction_data,
                tax_results=tax_results,
                period=data.period,
            )
            return asdict(report)

        elif data.report_type == "compliance_checklist":
            report = report_gen.generate_compliance_checklist(
                user_name=user_name,
                user_type=user_type,
                year=data.year,
                filed_returns=[],
            )
            return asdict(report)

        else:
            raise HTTPException(status_code=400, detail=f"Unknown report type: {data.report_type}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
