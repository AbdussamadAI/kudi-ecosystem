"""
AI Tax Assistant Orchestrator
Combines RAG retrieval, tool calling, and prompt engineering
to deliver a hybrid AI tax assistant experience.

Flow:
  1. User sends a message
  2. Retrieve relevant tax law context via RAG
  3. Build prompt with system instructions + context + user profile + history
  4. Send to LLM with tool definitions
  5. If LLM calls tools, execute them and feed results back
  6. Return final response with disclaimer
"""

import json
from typing import AsyncGenerator

from openai import AsyncOpenAI

from app.config import get_settings
from app.ai.prompts import SYSTEM_PROMPT, CONTEXT_TEMPLATE, USER_PROFILE_TEMPLATE
from app.ai.tools import TOOL_DEFINITIONS, execute_tool


settings = get_settings()

MAX_TOOL_ITERATIONS = 5

PROVIDER_CONFIG = {
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": settings.OPENROUTER_API_KEY,
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key": settings.GROQ_API_KEY,
    },
}


class TaxAssistant:
    """
    Hybrid AI Tax Assistant that combines:
    - RAG for tax law knowledge retrieval
    - Tool calling for KudiCore engine computations
    - Prompt engineering for response quality
    """

    def __init__(self):
        provider = settings.LLM_PROVIDER
        config = PROVIDER_CONFIG.get(provider, PROVIDER_CONFIG["openrouter"])
        self.client = AsyncOpenAI(
            base_url=config["base_url"],
            api_key=config["api_key"],
        )
        self.model = settings.LLM_MODEL
        self.max_output_tokens = max(128, min(settings.ASSISTANT_MAX_OUTPUT_TOKENS, 2048))
        self.max_output_words = max(40, settings.ASSISTANT_MAX_OUTPUT_WORDS)
        self._rag_enabled = settings.ASSISTANT_ENABLE_RAG

    def enable_rag(self):
        self._rag_enabled = True

    def _build_messages(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        user_profile: dict | None = None,
        rag_context: str | None = None,
    ) -> list[dict]:
        messages = []

        system_content = (
            SYSTEM_PROMPT
            + f"\n\nResponse Budget:\n- Hard cap: {self.max_output_words} words\n"
            "- Be direct and straight to the point.\n"
            "- Only go beyond this if the user explicitly asks for detailed analysis."
        )

        if user_profile:
            system_content += "\n\n" + USER_PROFILE_TEMPLATE.format(
                name=user_profile.get("name", "User"),
                user_type=user_profile.get("user_type", "individual"),
                tier=user_profile.get("tier", "free"),
                state=user_profile.get("state", "Not specified"),
                additional_context=user_profile.get("additional_context", ""),
            )

        if rag_context:
            system_content += "\n\n" + CONTEXT_TEMPLATE.format(context=rag_context)

        messages.append({"role": "system", "content": system_content})

        if conversation_history:
            for msg in conversation_history[-20:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

        messages.append({"role": "user", "content": user_message})

        return messages

    def _truncate_response(self, content: str) -> str:
        words = content.split()
        if len(words) <= self.max_output_words:
            return content.strip()

        trimmed = " ".join(words[: self.max_output_words]).strip()
        sentence_end = max(trimmed.rfind(". "), trimmed.rfind("? "), trimmed.rfind("! "))
        if sentence_end > int(len(trimmed) * 0.6):
            trimmed = trimmed[: sentence_end + 1]

        return (
            f"{trimmed}\n\n"
            "(Response truncated for brevity. Ask for more detail if needed.)"
        )

    def _retrieve_rag_context(self, query: str) -> str | None:
        if not self._rag_enabled:
            return None

        try:
            from app.ai.embeddings import retrieve_context
            chunks = retrieve_context(query, top_k=5)
            if not chunks:
                return None

            context_parts = []
            for i, chunk in enumerate(chunks, 1):
                context_parts.append(f"[Section {i}] (relevance: {chunk['score']:.2f})\n{chunk['text']}")

            return "\n\n".join(context_parts)
        except Exception:
            return None

    async def chat(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        user_profile: dict | None = None,
    ) -> dict:
        rag_context = self._retrieve_rag_context(user_message)

        messages = self._build_messages(
            user_message=user_message,
            conversation_history=conversation_history,
            user_profile=user_profile,
            rag_context=rag_context,
        )

        tool_calls_made = []

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=self.max_output_tokens,
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.message.tool_calls
                    ],
                })

                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    result = execute_tool(tool_name, arguments)
                    tool_calls_made.append({
                        "tool": tool_name,
                        "arguments": arguments,
                        "result": json.loads(result) if isinstance(result, str) else result,
                    })

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                content = self._truncate_response(choice.message.content or "")
                # Disclaimer is handled by system prompt - don't append here
                return {
                    "response": content,
                    "tool_calls": tool_calls_made,
                    "rag_used": rag_context is not None,
                    "model": self.model,
                }

        content = self._truncate_response(
            response.choices[0].message.content
            or "I apologize, but I encountered an issue processing your request. Please try again."
        )
        # Disclaimer is handled by system prompt - don't append here

        return {
            "response": content,
            "tool_calls": tool_calls_made,
            "rag_used": rag_context is not None,
            "model": self.model,
        }

    async def chat_stream(
        self,
        user_message: str,
        conversation_history: list[dict] | None = None,
        user_profile: dict | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Streaming version of chat. Yields chunks of the response as they arrive.
        Tool calls are executed before streaming the final response.
        """
        rag_context = self._retrieve_rag_context(user_message)

        messages = self._build_messages(
            user_message=user_message,
            conversation_history=conversation_history,
            user_profile=user_profile,
            rag_context=rag_context,
        )

        for iteration in range(MAX_TOOL_ITERATIONS):
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3,
                max_tokens=self.max_output_tokens,
            )

            choice = response.choices[0]

            if choice.finish_reason == "tool_calls" and choice.message.tool_calls:
                messages.append({
                    "role": "assistant",
                    "content": choice.message.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in choice.message.tool_calls
                    ],
                })

                for tool_call in choice.message.tool_calls:
                    tool_name = tool_call.function.name
                    try:
                        arguments = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        arguments = {}

                    yield json.dumps({"type": "tool_call", "tool": tool_name, "status": "executing"}) + "\n"

                    result = execute_tool(tool_name, arguments)

                    yield json.dumps({"type": "tool_result", "tool": tool_name, "result": json.loads(result)}) + "\n"

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
            else:
                break

        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.3,
            max_tokens=self.max_output_tokens,
            stream=True,
        )

        emitted_text = ""
        generated_text = ""

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                generated_text += chunk.choices[0].delta.content
                bounded_text = self._truncate_response(generated_text)
                if len(bounded_text) > len(emitted_text):
                    delta_text = bounded_text[len(emitted_text):]
                    yield json.dumps({"type": "content", "text": delta_text}) + "\n"
                    emitted_text = bounded_text

                if len(generated_text.split()) > self.max_output_words:
                    break

        # Disclaimer is handled by system prompt - don't append here
        yield json.dumps({"type": "done"}) + "\n"
