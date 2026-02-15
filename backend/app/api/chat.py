"""
Chat API routes.
Handles AI Tax Assistant conversations with streaming support.
"""

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.api.auth import get_current_user, get_supabase, get_supabase_admin
from app.schemas.schemas import ChatMessageCreate, ConversationResponse, ConversationListResponse
from app.ai.assistant import TaxAssistant

router = APIRouter()
settings = get_settings()
assistant = TaxAssistant()


@router.post("/send")
async def send_message(data: ChatMessageCreate, current_user=Depends(get_current_user)):
    """Send a message to the AI Tax Assistant and get a response."""
    supabase = get_supabase()

    try:
        user_data = supabase.table("users").select("*").eq(
            "supabase_id", str(current_user.id)
        ).single().execute()

        user_profile = None
        if user_data.data:
            profile_data = supabase.table("user_profiles").select("*").eq(
                "user_id", str(current_user.id)
            ).maybe_single().execute()

            user_profile = {
                "name": user_data.data.get("full_name", "User"),
                "user_type": user_data.data.get("user_type", "individual"),
                "tier": user_data.data.get("subscription_tier", "free"),
                "state": profile_data.data.get("state_of_residence", "Not specified") if profile_data.data else "Not specified",
                "additional_context": "",
            }

        conversation_id = data.conversation_id
        conversation_history = []

        if conversation_id:
            messages_result = supabase.table("chat_messages").select("*").eq(
                "conversation_id", str(conversation_id)
            ).order("created_at").execute()

            conversation_history = [
                {"role": m["role"], "content": m["content"]}
                for m in (messages_result.data or [])
            ]
        else:
            conv_result = supabase.table("chat_conversations").insert({
                "user_id": str(current_user.id),
                "title": data.message[:50] + ("..." if len(data.message) > 50 else ""),
            }).execute()

            if conv_result.data:
                conversation_id = conv_result.data[0]["id"]
            else:
                raise HTTPException(status_code=500, detail="Failed to create conversation")

        supabase.table("chat_messages").insert({
            "conversation_id": str(conversation_id),
            "role": "user",
            "content": data.message,
        }).execute()

        result = await assistant.chat(
            user_message=data.message,
            conversation_history=conversation_history,
            user_profile=user_profile,
        )

        supabase.table("chat_messages").insert({
            "conversation_id": str(conversation_id),
            "role": "assistant",
            "content": result["response"],
            "tool_calls": {"calls": result["tool_calls"]} if result["tool_calls"] else None,
        }).execute()

        return {
            "conversation_id": conversation_id,
            "response": result["response"],
            "tool_calls": result["tool_calls"],
            "rag_used": result["rag_used"],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.post("/stream")
async def stream_message(data: ChatMessageCreate, current_user=Depends(get_current_user)):
    """Stream a response from the AI Tax Assistant via Server-Sent Events."""
    supabase = get_supabase()

    try:
        # Try to get user data with admin client (bypasses RLS)
        admin_client = get_supabase_admin()
        try:
            user_data = admin_client.table("users").select("*").eq(
                "supabase_id", str(current_user.id)
            ).maybe_single().execute()
        except Exception:
            user_data = None

        user_profile = None
        if user_data and user_data.data:
            user_profile = {
                "name": user_data.data.get("full_name", "User"),
                "user_type": user_data.data.get("user_type", "individual"),
                "tier": user_data.data.get("subscription_tier", "free"),
                "state": "Not specified",
                "additional_context": "",
            }
        else:
            # Fallback: create minimal profile from JWT
            user_profile = {
                "name": getattr(current_user, 'email', 'User'),
                "user_type": "individual",
                "tier": "free",
                "state": "Not specified",
                "additional_context": "",
            }

        conversation_id = data.conversation_id
        conversation_history = []

        if conversation_id:
            messages_result = supabase.table("chat_messages").select("*").eq(
                "conversation_id", str(conversation_id)
            ).order("created_at").execute()

            conversation_history = [
                {"role": m["role"], "content": m["content"]}
                for m in (messages_result.data or [])
            ]
        else:
            # Try to create conversation, but continue even if DB fails
            try:
                user_lookup = supabase.table("users").select("id").eq(
                    "supabase_id", str(current_user.id)
                ).maybe_single().execute()
                
                user_uuid = user_lookup.data["id"] if user_lookup and user_lookup.data else None
                
                if user_uuid:
                    conv_result = supabase.table("chat_conversations").insert({
                        "user_id": user_uuid,
                        "title": data.message[:50] + ("..." if len(data.message) > 50 else ""),
                    }).execute()

                    if conv_result.data:
                        conversation_id = conv_result.data[0]["id"]
                        
                    # Store user message
                    supabase.table("chat_messages").insert({
                        "conversation_id": str(conversation_id),
                        "role": "user",
                        "content": data.message,
                    }).execute()
            except Exception:
                # Continue without DB persistence
                conversation_id = str(uuid4())
                pass

        async def event_generator():
            full_response = ""
            async for chunk in assistant.chat_stream(
                user_message=data.message,
                conversation_history=conversation_history,
                user_profile=user_profile,
            ):
                parsed = json.loads(chunk)
                if parsed.get("type") == "content":
                    full_response += parsed.get("text", "")
                yield f"data: {chunk}\n\n"

            if full_response and conversation_id:
                try:
                    supabase.table("chat_messages").insert({
                        "conversation_id": str(conversation_id),
                        "role": "assistant",
                        "content": full_response,
                    }).execute()
                except Exception:
                    pass  # Continue even if DB storage fails

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Conversation-Id": str(conversation_id),
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stream failed: {str(e)}")


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(current_user=Depends(get_current_user)):
    """List all conversations for the current user."""
    supabase = get_supabase()

    try:
        result = supabase.table("chat_conversations").select("*", count="exact").eq(
            "user_id", str(current_user.id)
        ).order("created_at", desc=True).execute()

        return ConversationListResponse(
            conversations=result.data or [],
            total=result.count or 0,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to list conversations: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: UUID, current_user=Depends(get_current_user)):
    """Get a conversation with all its messages."""
    supabase = get_supabase()

    try:
        conv_result = supabase.table("chat_conversations").select("*").eq(
            "id", str(conversation_id)
        ).eq("user_id", str(current_user.id)).single().execute()

        if not conv_result.data:
            raise HTTPException(status_code=404, detail="Conversation not found")

        messages_result = supabase.table("chat_messages").select("*").eq(
            "conversation_id", str(conversation_id)
        ).order("created_at").execute()

        return {
            "conversation": conv_result.data,
            "messages": messages_result.data or [],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get conversation: {str(e)}")


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: UUID, current_user=Depends(get_current_user)):
    """Delete a conversation and all its messages."""
    supabase = get_supabase()

    try:
        supabase.table("chat_messages").delete().eq(
            "conversation_id", str(conversation_id)
        ).execute()

        supabase.table("chat_conversations").delete().eq(
            "id", str(conversation_id)
        ).eq("user_id", str(current_user.id)).execute()

        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to delete conversation: {str(e)}")
