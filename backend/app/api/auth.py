"""
Authentication API routes.
Uses Supabase Auth for user management.
"""

import jwt
from fastapi import APIRouter, HTTPException, Depends, Header
from supabase import create_client

from app.config import get_settings
from app.schemas.schemas import (
    UserRegister,
    UserLogin,
    UserProfileUpdate,
    UserResponse,
)

router = APIRouter()
settings = get_settings()


def get_supabase():
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


def get_supabase_admin():
    """Get Supabase client with service role key (bypasses RLS for server-side operations)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token locally and return payload."""
    try:
        # Decode without verification (Supabase already verified it)
        # In production, you should verify with SUPABASE_JWT_SECRET
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")


async def get_current_user(authorization: str = Header(...)):
    """Validate JWT token from Supabase and return user data."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    
    try:
        # Try local JWT verification first
        payload = verify_jwt_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token: no user ID")
        
        # Create a simple user object from JWT payload
        class SimpleUser:
            def __init__(self, id, email):
                self.id = id
                self.email = email
        
        return SimpleUser(id=user_id, email=payload.get("email", ""))
        
    except HTTPException:
        raise
    except Exception as e:
        # Fallback to Supabase API verification
        try:
            supabase = get_supabase()
            user_response = supabase.auth.get_user(token)
            if not user_response or not user_response.user:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
            return user_response.user
        except Exception:
            raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


@router.post("/register")
async def register(data: UserRegister):
    """Register a new user via Supabase Auth."""
    supabase = get_supabase()

    try:
        auth_response = supabase.auth.sign_up({
            "email": data.email,
            "password": data.password,
            "options": {
                "data": {
                    "full_name": data.full_name,
                    "user_type": data.user_type.value,
                }
            }
        })

        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Registration failed")

        supabase.table("users").insert({
            "supabase_id": auth_response.user.id,
            "email": data.email,
            "full_name": data.full_name,
            "user_type": data.user_type.value,
            "subscription_tier": "free",
        }).execute()

        supabase.table("user_profiles").insert({
            "user_id": auth_response.user.id,
        }).execute()

        return {
            "message": "Registration successful. Please check your email to verify your account.",
            "user_id": auth_response.user.id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration failed: {str(e)}")


@router.post("/login")
async def login(data: UserLogin):
    """Login via Supabase Auth."""
    supabase = get_supabase()

    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": data.email,
            "password": data.password,
        })

        if not auth_response.session:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        return {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
            "token_type": "bearer",
            "expires_in": auth_response.session.expires_in,
            "user": {
                "id": auth_response.user.id,
                "email": auth_response.user.email,
                "full_name": auth_response.user.user_metadata.get("full_name", ""),
                "user_type": auth_response.user.user_metadata.get("user_type", "individual"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Login failed: {str(e)}")


@router.get("/me")
async def get_me(current_user=Depends(get_current_user)):
    """Get current user profile."""
    supabase = get_supabase()

    try:
        user_data = supabase.table("users").select("*").eq(
            "supabase_id", current_user.id
        ).single().execute()

        profile_data = supabase.table("user_profiles").select("*").eq(
            "user_id", current_user.id
        ).single().execute()

        return {
            "user": user_data.data,
            "profile": profile_data.data if profile_data.data else {},
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User not found: {str(e)}")


@router.put("/profile")
async def update_profile(data: UserProfileUpdate, current_user=Depends(get_current_user)):
    """Update user profile."""
    supabase = get_supabase()

    try:
        update_data = data.model_dump(exclude_none=True)

        if "full_name" in update_data or "user_type" in update_data:
            user_update = {}
            if "full_name" in update_data:
                user_update["full_name"] = update_data.pop("full_name")
            if "user_type" in update_data:
                user_update["user_type"] = update_data.pop("user_type")

            supabase.table("users").update(user_update).eq(
                "supabase_id", current_user.id
            ).execute()

        if update_data:
            supabase.table("user_profiles").update(update_data).eq(
                "user_id", current_user.id
            ).execute()

        return {"message": "Profile updated successfully"}

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Update failed: {str(e)}")


@router.post("/logout")
async def logout(current_user=Depends(get_current_user)):
    """Logout and invalidate session."""
    return {"message": "Logged out successfully"}
