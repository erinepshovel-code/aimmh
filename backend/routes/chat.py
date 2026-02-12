from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from datetime import datetime, timezone
from typing import List
import json
import uuid
import logging

from db import db
from models.chat import ChatRequest, MessageFeedback, ConversationResponse, CatchupRequest
from services.auth import get_current_user, get_user_id
from services.llm import get_api_key, stream_emergent_model, stream_openai_compatible

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stream responses from multiple AI models"""

    async def event_generator():
        conversation_id = request.conversation_id or str(uuid.uuid4())

        user_message_id = str(uuid.uuid4())
        user_msg = {
            "id": user_message_id,
            "conversation_id": conversation_id,
            "role": "user",
            "content": request.message,
            "model": "user",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": get_user_id(current_user)
        }
        await db.messages.insert_one(user_msg)

        history = await db.messages.find(
            {"conversation_id": conversation_id, "user_id": get_user_id(current_user)},
            {"_id": 0}
        ).sort("timestamp", 1).limit(10).to_list(10)

        messages_context = []
        for msg in history:
            messages_context.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        for model_spec in request.models:
            try:
                model_lower = model_spec.lower()
                message_id = str(uuid.uuid4())

                yield {
                    "event": "start",
                    "data": json.dumps({"model": model_spec, "message_id": message_id})
                }

                full_response = ""

                if "gpt" in model_lower or model_lower.startswith("o"):
                    api_key = get_api_key(current_user, "gpt")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_emergent_model(api_key, model_spec, "openai", messages_context, conversation_id):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "claude" in model_lower:
                    api_key = get_api_key(current_user, "claude")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_emergent_model(api_key, model_spec, "anthropic", messages_context, conversation_id):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "gemini" in model_lower:
                    api_key = get_api_key(current_user, "gemini")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_emergent_model(api_key, model_spec, "gemini", messages_context, conversation_id):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "grok" in model_lower:
                    api_key = get_api_key(current_user, "grok")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_openai_compatible("https://api.x.ai/v1", api_key, model_spec, messages_context):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "deepseek" in model_lower:
                    api_key = get_api_key(current_user, "deepseek")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_openai_compatible("https://api.deepseek.com", api_key, model_spec, messages_context):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "perplexity" in model_lower or "sonar" in model_lower:
                    api_key = get_api_key(current_user, "perplexity")
                    if not api_key:
                        yield {"event": "error", "data": json.dumps({"model": model_spec, "error": "No API key configured"})}
                        continue
                    async for chunk in stream_openai_compatible("https://api.perplexity.ai", api_key, model_spec, messages_context):
                        if chunk:
                            full_response += chunk
                            yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                assistant_msg = {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": full_response,
                    "model": model_spec,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": get_user_id(current_user),
                    "feedback": None
                }
                await db.messages.insert_one(assistant_msg)

                yield {"event": "complete", "data": json.dumps({"model": model_spec, "message_id": message_id})}

            except Exception as e:
                logger.error(f"Error streaming from {model_spec}: {str(e)}")
                yield {"event": "error", "data": json.dumps({"model": model_spec, "error": str(e)})}

        await db.conversations.update_one(
            {"id": conversation_id},
            {
                "$set": {
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "title": request.message[:50]
                },
                "$setOnInsert": {
                    "id": conversation_id,
                    "user_id": get_user_id(current_user),
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
            },
            upsert=True
        )

    return EventSourceResponse(event_generator())


@router.post("/chat/feedback")
async def submit_feedback(
    feedback: MessageFeedback,
    current_user: dict = Depends(get_current_user)
):
    """Submit thumbs up/down feedback for a message"""
    result = await db.messages.update_one(
        {"id": feedback.message_id, "user_id": get_user_id(current_user)},
        {"$set": {"feedback": feedback.feedback}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Feedback submitted"}


@router.get("/conversations", response_model=List[ConversationResponse])
async def get_conversations(current_user: dict = Depends(get_current_user)):
    """Get user's conversation history"""
    conversations = await db.conversations.find(
        {"user_id": get_user_id(current_user)},
        {"_id": 0}
    ).sort("updated_at", -1).limit(50).to_list(50)

    return [
        ConversationResponse(
            id=conv["id"],
            user_id=conv["user_id"],
            title=conv.get("title", "New Conversation"),
            created_at=datetime.fromisoformat(conv["created_at"]),
            updated_at=datetime.fromisoformat(conv["updated_at"])
        )
        for conv in conversations
    ]


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get messages from a conversation"""
    messages = await db.messages.find(
        {"conversation_id": conversation_id, "user_id": get_user_id(current_user)},
        {"_id": 0}
    ).sort("timestamp", 1).to_list(1000)
    return messages


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a conversation and its messages"""
    await db.conversations.delete_one({"id": conversation_id, "user_id": get_user_id(current_user)})
    await db.messages.delete_many({"conversation_id": conversation_id, "user_id": get_user_id(current_user)})
    return {"message": "Conversation deleted"}


@router.post("/chat/catchup")
async def catchup_models(
    request: CatchupRequest,
    current_user: dict = Depends(get_current_user)
):
    """Catch up new models with conversation history"""
    if request.message_ids:
        messages = []
        for msg_id in request.message_ids:
            msg = await db.messages.find_one(
                {"id": msg_id, "user_id": get_user_id(current_user)},
                {"_id": 0}
            )
            if msg:
                messages.append(msg)
        messages.sort(key=lambda x: x['timestamp'])
    else:
        messages = await db.messages.find(
            {"conversation_id": request.conversation_id, "user_id": get_user_id(current_user)},
            {"_id": 0}
        ).sort("timestamp", 1).to_list(1000)

    if not messages:
        raise HTTPException(status_code=404, detail="No messages found")

    catchup_parts = ["Here is the conversation history to catch you up:\n"]
    for msg in messages:
        if msg['role'] == 'user':
            catchup_parts.append(f"User: {msg['content']}")
        elif msg['role'] == 'assistant':
            catchup_parts.append(f"{msg['model']}: {msg['content']}")
    catchup_parts.append("\nYou are now caught up. Please acknowledge that you understand the conversation context.")

    return {
        "message": "Catchup initiated",
        "models": request.new_models,
        "message_count": len(messages)
    }
