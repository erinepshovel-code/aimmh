import os
import json
import uuid
import asyncio
import logging
import httpx
from typing import List
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


def _is_retryable_provider_error(error_text: str) -> bool:
    lowered = (error_text or "").lower()
    retry_markers = [
        "502",
        "503",
        "504",
        "badgateway",
        "gateway",
        "temporarily unavailable",
        "timeout",
        "rate limit",
        "429",
    ]
    return any(marker in lowered for marker in retry_markers)


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
    max_attempts = 3
    backoff_seconds = [0.8, 1.6, 2.4]

    async with httpx.AsyncClient() as client:
        for attempt in range(max_attempts):
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
                        error_text = (await response.aread()).decode(errors="ignore")
                        combined_error = f"API error {response.status_code}: {error_text}"

                        if attempt < max_attempts - 1 and _is_retryable_provider_error(combined_error):
                            await asyncio.sleep(backoff_seconds[attempt])
                            continue

                        yield f"[ERROR] {combined_error}"
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
                    return

            except Exception as e:
                error_msg = str(e)
                if attempt < max_attempts - 1 and _is_retryable_provider_error(error_msg):
                    await asyncio.sleep(backoff_seconds[attempt])
                    continue
                yield f"[ERROR] {error_msg}"
                return


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


async def stream_emergent_model(api_key: str, model: str, provider: str, messages: List[dict], conversation_id: str):
    """Stream from Emergent-supported models (GPT, Claude, Gemini)"""
    try:
        user_messages = [msg for msg in messages if msg["role"] == "user"]
        if not user_messages:
            yield "[ERROR] No user messages found"
            return

        conversation_history = ""
        if len(messages) > 1:
            prev_messages = messages[:-1]
            history_parts = []
            for msg in prev_messages[-10:]:
                if msg['role'] == 'user':
                    history_parts.append(f"User: {msg['content']}")
                elif msg['role'] == 'assistant':
                    history_parts.append(f"Assistant: {msg['content']}")
            if history_parts:
                conversation_history = "\n".join(history_parts)

        system_msg = "You are a helpful AI assistant."
        if conversation_history:
            system_msg = f"You are a helpful AI assistant. Continue this conversation naturally.\n\nPrevious conversation:\n{conversation_history}"

        session_id = f"{conversation_id}-{model}" if conversation_id else str(uuid.uuid4())

        max_attempts = 3
        backoff_seconds = [0.8, 1.6, 2.4]
        user_msg = UserMessage(text=user_messages[-1]["content"])

        for attempt in range(max_attempts):
            try:
                chat = LlmChat(
                    api_key=api_key,
                    session_id=f"{session_id}-try-{attempt + 1}",
                    system_message=system_msg
                ).with_model(provider, model)

                response = await chat.send_message(user_msg)
                words = response.split()
                for word in words:
                    yield word + " "
                    await asyncio.sleep(0.05)
                return
            except Exception as e:
                error_msg = str(e)
                is_retryable = _is_retryable_provider_error(error_msg)
                if attempt < max_attempts - 1 and is_retryable:
                    logger.warning(
                        "Retryable provider error for %s/%s (attempt %s/%s): %s",
                        provider,
                        model,
                        attempt + 1,
                        max_attempts,
                        error_msg,
                    )
                    await asyncio.sleep(backoff_seconds[attempt])
                    continue

                logger.error(f"Error streaming from {provider}/{model}: {error_msg}")
                if is_retryable:
                    yield f"[ERROR] Upstream provider is temporarily unavailable ({error_msg}). Please retry in a few seconds."
                else:
                    yield f"[ERROR] {error_msg}"
                return

    except Exception as e:
        logger.error(f"Error streaming from {provider}/{model}: {str(e)}")
        yield f"[ERROR] {str(e)}"
