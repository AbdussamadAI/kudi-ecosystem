"""
Shared API dependencies.
Provides reusable FastAPI dependencies for authentication and database access.
"""

from fastapi import HTTPException, Header, Depends
from supabase import create_client

from app.config import get_settings

settings = get_settings()


def get_supabase():
    """Get a Supabase client instance."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)


async def get_current_user(authorization: str = Header(...)):
    """
    Validate Supabase JWT token and return the authenticated user.
    Use as a FastAPI dependency: Depends(get_current_user)
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header")

    token = authorization.replace("Bearer ", "")
    supabase = get_supabase()

    try:
        user_response = supabase.auth.get_user(token)
        if not user_response or not user_response.user:
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        return user_response.user
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {str(e)}")


async def get_current_user_id(user=Depends(get_current_user)) -> str:
    """Extract the Supabase user ID string from the authenticated user."""
    return user.id
