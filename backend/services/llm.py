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

        chat = LlmChat(
            api_key=api_key,
            session_id=session_id,
            system_message=system_msg
        ).with_model(provider, model)

        user_msg = UserMessage(text=user_messages[-1]["content"])
        response = await chat.send_message(user_msg)

        words = response.split()
        for word in words:
            yield word + " "
            await asyncio.sleep(0.05)

    except Exception as e:
        logger.error(f"Error streaming from {provider}/{model}: {str(e)}")
        yield f"[ERROR] {str(e)}"
