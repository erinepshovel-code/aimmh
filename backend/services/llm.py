import os
import json
import uuid
import asyncio
import logging
import httpx
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


def get_api_key(current_user: dict, provider: str) -> str:
    """Get API key for provider.

    For GPT/Claude/Gemini we default to the Emergent universal key unless the user
    explicitly disables it or provides their own key.
    """
    user_key = current_user.get("api_keys", {}).get(provider)

    universal_providers = {"gpt", "claude", "gemini"}
    if provider in universal_providers:
        if user_key == "DISABLED":
            return ""
        # Default ON
        if not user_key or user_key == "UNIVERSAL":
            return os.environ.get("EMERGENT_LLM_KEY", "")

    if user_key == "UNIVERSAL":
        return os.environ.get("EMERGENT_LLM_KEY", "")

    return user_key or ""


async def stream_openai_compatible(base_url: str, api_key: str, model: str, messages: List[dict]):
    """Stream from OpenAI-compatible APIs (Grok, DeepSeek, Perplexity)"""
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": messages,
                    "stream": True
                },
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[ERROR] API error: {response.status_code} - {error_text.decode()}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            content = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            yield f"[ERROR] {str(e)}"


async def validate_universal_key(provider: str = "openai", model: str = "gpt-4o-mini") -> dict:
    key = os.environ.get("EMERGENT_LLM_KEY", "")
    if not key:
        return {
            "status": "missing",
            "message": "EMERGENT_LLM_KEY is not configured",
            "provider": provider,
            "model": model
        }

    try:
        chat = LlmChat(
            api_key=key,
            session_id=str(uuid.uuid4()),
            system_message="You are a helpful AI assistant."
        ).with_model(provider, model)

        user_msg = UserMessage(text="ping")
        response = await asyncio.wait_for(chat.send_message(user_msg), timeout=12)

        if response:
            return {
                "status": "valid",
                "message": "Universal key is valid",
                "provider": provider,
                "model": model
            }

        return {
            "status": "error",
            "message": "No response received during validation",
            "provider": provider,
            "model": model
        }
    except Exception as e:
        msg = str(e)
        lower_msg = msg.lower()
        if "invalid" in lower_msg or "authentication" in lower_msg or "unauthorized" in lower_msg or "401" in lower_msg:
            status = "invalid"
        else:
            status = "error"
        return {
            "status": status,
            "message": msg,
            "provider": provider,
            "model": model
        }
