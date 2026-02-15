"""
Transaction API routes.
Handles CRUD operations for user financial transactions.
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query

from app.config import get_settings
from app.api.auth import get_current_user, get_supabase, get_supabase_admin
from app.schemas.schemas import TransactionCreate, TransactionResponse, TransactionListResponse
from app.core.currency import CurrencyEngine
from app.core.classifier import TransactionClassifier

router = APIRouter()
settings = get_settings()
currency_engine = CurrencyEngine()
classifier = TransactionClassifier()

def get_user_uuid(supabase, current_user) -> str:
    """Get the user's UUID from public.users table using supabase_id."""
    jwt_user_id = str(current_user.id)
    
    # Use admin client to bypass RLS for server-side lookup
    admin_client = get_supabase_admin()
    
    user_lookup = admin_client.table("users").select("id, supabase_id").eq(
        "supabase_id", jwt_user_id
    ).maybe_single().execute()
    
    if not user_lookup or not user_lookup.data:
        raise HTTPException(status_code=404, detail=f"User not found in database (jwt_id={jwt_user_id})")
    
    return user_lookup.data["id"]


@router.post("/", response_model=TransactionResponse)
async def create_transaction(data: TransactionCreate, current_user=Depends(get_current_user)):
    """Create a new transaction with automatic currency conversion and classification."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)

        conversion = currency_engine.convert_to_ngn(
            amount=data.amount,
            currency=data.currency.value,
            rate_date=data.transaction_date,
        )

        classification = classifier.classify(
            description=data.description,
            amount=data.amount,
            is_credit=data.transaction_type.value == "income",
        )

        income_category = data.income_category or (
            classification.suggested_category if data.transaction_type.value == "income" else None
        )
        expense_category = data.expense_category or (
            classification.suggested_category if data.transaction_type.value == "expense" else None
        )

        transaction_data = {
            "user_id": user_uuid,
            "transaction_type": data.transaction_type.value,
            "description": data.description,
            "amount": data.amount,
            "currency": data.currency.value,
            "amount_ngn": conversion.ngn_amount,
            "exchange_rate": conversion.exchange_rate,
            "transaction_date": data.transaction_date.isoformat(),
            "income_category": income_category,
            "expense_category": expense_category,
            "is_vat_applicable": data.is_vat_applicable or classification.is_vat_applicable,
            "is_wht_applicable": data.is_wht_applicable or classification.is_wht_applicable,
            "is_capital": data.is_capital or classification.is_capital,
            "source": "manual",
            "ai_classified": not (data.income_category or data.expense_category),
        }

        result = supabase.table("transactions").insert(transaction_data).execute()

        if not result.data:
            raise HTTPException(status_code=500, detail="Failed to create transaction")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create transaction: {str(e)}")


@router.get("/", response_model=TransactionListResponse)
async def list_transactions(
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    transaction_type: str | None = None,
    currency: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
):
    """List user transactions with filtering and pagination."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)
        query = supabase.table("transactions").select("*", count="exact").eq(
            "user_id", user_uuid
        )

        if transaction_type:
            query = query.eq("transaction_type", transaction_type)
        if currency:
            query = query.eq("currency", currency)
        if start_date:
            query = query.gte("transaction_date", start_date)
        if end_date:
            query = query.lte("transaction_date", end_date)

        offset = (page - 1) * page_size
        query = query.order("transaction_date", desc=True).range(offset, offset + page_size - 1)

        result = query.execute()

        return TransactionListResponse(
            transactions=result.data or [],
            total=result.count or 0,
            page=page,
            page_size=page_size,
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch transactions: {str(e)}")


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(transaction_id: UUID, current_user=Depends(get_current_user)):
    """Get a single transaction by ID."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)
        result = supabase.table("transactions").select("*").eq(
            "id", str(transaction_id)
        ).eq("user_id", user_uuid).single().execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch transaction: {str(e)}")


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: UUID,
    data: TransactionCreate,
    current_user=Depends(get_current_user),
):
    """Update an existing transaction."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)

        conversion = currency_engine.convert_to_ngn(
            amount=data.amount,
            currency=data.currency.value,
            rate_date=data.transaction_date,
        )

        update_data = {
            "transaction_type": data.transaction_type.value,
            "description": data.description,
            "amount": data.amount,
            "currency": data.currency.value,
            "amount_ngn": conversion.ngn_amount,
            "exchange_rate": conversion.exchange_rate,
            "transaction_date": data.transaction_date.isoformat(),
            "income_category": data.income_category,
            "expense_category": data.expense_category,
            "is_vat_applicable": data.is_vat_applicable,
            "is_wht_applicable": data.is_wht_applicable,
            "is_capital": data.is_capital,
        }

        result = supabase.table("transactions").update(update_data).eq(
            "id", str(transaction_id)
        ).eq("user_id", user_uuid).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return result.data[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update transaction: {str(e)}")


@router.delete("/{transaction_id}")
async def delete_transaction(transaction_id: UUID, current_user=Depends(get_current_user)):
    """Delete a transaction."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)
        result = supabase.table("transactions").delete().eq(
            "id", str(transaction_id)
        ).eq("user_id", user_uuid).execute()

        if not result.data:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return {"message": "Transaction deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete transaction: {str(e)}")


@router.get("/summary/overview")
async def get_transaction_summary(
    current_user=Depends(get_current_user),
    year: int | None = None,
):
    """Get a summary of all transactions for the user."""
    supabase = get_supabase_admin()

    try:
        user_uuid = get_user_uuid(supabase, current_user)
        query = supabase.table("transactions").select("*").eq(
            "user_id", user_uuid
        )

        if year:
            query = query.gte("transaction_date", f"{year}-01-01").lte("transaction_date", f"{year}-12-31")

        result = query.execute()
        transactions = result.data or []

        total_income = sum(t["amount_ngn"] for t in transactions if t["transaction_type"] == "income")
        total_expenses = sum(t["amount_ngn"] for t in transactions if t["transaction_type"] == "expense")

        income_by_category = {}
        expense_by_category = {}

        for t in transactions:
            if t["transaction_type"] == "income":
                cat = t.get("income_category") or "other"
                income_by_category[cat] = income_by_category.get(cat, 0) + t["amount_ngn"]
            else:
                cat = t.get("expense_category") or "other"
                expense_by_category[cat] = expense_by_category.get(cat, 0) + t["amount_ngn"]

        return {
            "total_income": round(total_income, 2),
            "total_expenses": round(total_expenses, 2),
            "net_income": round(total_income - total_expenses, 2),
            "transaction_count": len(transactions),
            "income_by_category": income_by_category,
            "expense_by_category": expense_by_category,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get summary: {str(e)}")
