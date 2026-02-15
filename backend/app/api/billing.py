"""
Billing API routes.
Handles freemium subscription management via Paystack (NGN) and Stripe (international).
"""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Request

from app.config import get_settings
from app.api.auth import get_current_user, get_supabase_admin
from app.schemas.schemas import SubscriptionCreateRequest

router = APIRouter()
settings = get_settings()

PLAN_CODES = {
    "pro": {
        "paystack": "PLN_pro_monthly",
        "stripe": "price_pro_monthly",
        "amount_ngn": 2500,
        "amount_usd": 5,
    },
    "business": {
        "paystack": "PLN_business_monthly",
        "stripe": "price_business_monthly",
        "amount_ngn": 10000,
        "amount_usd": 15,
    },
}


def is_valid_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except (ValueError, TypeError):
        return False


def get_user_record_by_supabase_id(supabase, supabase_id: str) -> dict | None:
    user_data = supabase.table("users").select("*").eq(
        "supabase_id", supabase_id
    ).maybe_single().execute()
    return user_data.data if user_data and user_data.data else None


@router.get("/plans")
async def get_plans():
    """Get available subscription plans."""
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price_ngn": 0,
                "price_usd": 0,
                "features": [
                    "10 AI chats per day",
                    "PIT calculation only",
                    "50 transactions per month",
                    "Basic tax summary",
                    "3 scenarios per month",
                ],
            },
            {
                "id": "pro",
                "name": "Pro",
                "price_ngn": 2500,
                "price_usd": 5,
                "features": [
                    "Unlimited AI chats",
                    "PIT + CIT + VAT + WHT",
                    "500 transactions per month",
                    "Full PDF reports",
                    "Unlimited scenarios",
                    "Multi-currency support",
                    "CSV & PDF statement upload",
                ],
            },
            {
                "id": "business",
                "name": "Business",
                "price_ngn": 10000,
                "price_usd": 15,
                "features": [
                    "Everything in Pro",
                    "Unlimited transactions",
                    "Priority support",
                    "Advanced anomaly alerts",
                    "Up to 5 team members",
                    "Open Banking integration",
                ],
            },
        ]
    }


@router.post("/subscribe")
async def create_subscription(data: SubscriptionCreateRequest, current_user=Depends(get_current_user)):
    """Initialize a subscription via Paystack or Stripe."""
    if data.plan.value == "free":
        raise HTTPException(status_code=400, detail="Cannot subscribe to free plan — it's the default")

    plan_info = PLAN_CODES.get(data.plan.value)
    if not plan_info:
        raise HTTPException(status_code=400, detail=f"Unknown plan: {data.plan.value}")

    supabase = get_supabase_admin()
    user_record = get_user_record_by_supabase_id(supabase, str(current_user.id))
    user_uuid = user_record["id"] if user_record else None

    if data.provider == "paystack":
        try:
            import httpx

            response = httpx.post(
                "https://api.paystack.co/transaction/initialize",
                headers={
                    "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "email": current_user.email,
                    "amount": plan_info["amount_ngn"] * 100,
                    "plan": plan_info["paystack"],
                    "metadata": {
                        "supabase_id": str(current_user.id),
                        "user_id": user_uuid,
                        "plan": data.plan.value,
                    },
                },
            )

            result = response.json()
            if not result.get("status"):
                raise HTTPException(status_code=400, detail="Paystack initialization failed")

            return {
                "provider": "paystack",
                "authorization_url": result["data"]["authorization_url"],
                "reference": result["data"]["reference"],
            }

        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Payment initialization failed: {str(e)}")

    elif data.provider == "stripe":
        try:
            import stripe
            stripe.api_key = settings.STRIPE_SECRET_KEY

            session = stripe.checkout.Session.create(
                customer_email=current_user.email,
                payment_method_types=["card"],
                line_items=[{
                    "price": plan_info["stripe"],
                    "quantity": 1,
                }],
                mode="subscription",
                success_url="https://kudwise.com/billing/success?session_id={CHECKOUT_SESSION_ID}",
                cancel_url="https://kudwise.com/billing/cancel",
                metadata={
                    "supabase_id": str(current_user.id),
                    "user_id": user_uuid,
                    "plan": data.plan.value,
                },
            )

            return {
                "provider": "stripe",
                "checkout_url": session.url,
                "session_id": session.id,
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Stripe initialization failed: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {data.provider}")


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request):
    """Handle Paystack webhook events."""
    import hashlib
    import hmac

    body = await request.body()
    signature = request.headers.get("x-paystack-signature", "")

    expected = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        body,
        hashlib.sha512,
    ).hexdigest()

    if signature != expected:
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    event = payload.get("event")

    supabase = get_supabase_admin()

    if event == "subscription.create":
        data = payload.get("data", {})
        metadata = data.get("metadata", {})
        user_id = metadata.get("user_id")
        supabase_id = metadata.get("supabase_id")
        plan = metadata.get("plan", "pro")

        # Backward compatibility: older payloads may put Supabase ID in user_id.
        if user_id and not is_valid_uuid(user_id) and not supabase_id:
            supabase_id = user_id
            user_id = None

        if not user_id and supabase_id:
            user_record = get_user_record_by_supabase_id(supabase, supabase_id)
            user_id = user_record["id"] if user_record else None

        if user_id:
            supabase.table("users").update({
                "subscription_tier": plan,
            }).eq("id", user_id).execute()

            supabase.table("subscriptions").upsert({
                "user_id": user_id,
                "provider": "paystack",
                "provider_subscription_id": str(data.get("subscription_code", "")),
                "provider_customer_id": str(data.get("customer", {}).get("customer_code", "")),
                "plan_code": plan,
                "is_active": True,
            }).execute()

    elif event == "subscription.disable":
        data = payload.get("data", {})
        sub_code = data.get("subscription_code")

        if sub_code:
            supabase.table("subscriptions").update({
                "is_active": False,
            }).eq("provider_subscription_id", sub_code).execute()

    return {"status": "ok"}


@router.get("/subscription")
async def get_subscription(current_user=Depends(get_current_user)):
    """Get current user's subscription status."""
    supabase = get_supabase_admin()

    try:
        user_record = get_user_record_by_supabase_id(supabase, str(current_user.id))
        if not user_record:
            return {"tier": "free", "subscription": None}

        sub_data = supabase.table("subscriptions").select("*").eq(
            "user_id", user_record["id"]
        ).maybe_single().execute()

        return {
            "tier": user_record.get("subscription_tier", "free"),
            "subscription": sub_data.data if sub_data.data else None,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get subscription: {str(e)}")
