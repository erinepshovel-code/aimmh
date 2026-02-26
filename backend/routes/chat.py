from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse
from datetime import datetime, timezone
from typing import List, Dict, Any
import json
import uuid
import time
import logging

from db import db
from models.chat import ChatRequest, MessageFeedback, ConversationResponse, CatchupRequest
from services.auth import get_current_user, get_user_id
from services.llm import get_api_key, stream_emergent_model, stream_openai_compatible

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])


def _normalize_attachments(attachments: List[Dict[str, Any]] | None) -> List[Dict[str, Any]]:
    normalized = []
    for item in attachments or []:
        if not isinstance(item, dict):
            continue

        target_mode = item.get("target_mode", "all")
        if target_mode not in {"all", "selected"}:
            target_mode = "all"

        target_models = item.get("target_models") or []
        if not isinstance(target_models, list):
            target_models = []

        normalized.append({
            "id": item.get("id") or str(uuid.uuid4()),
            "name": item.get("name") or "attachment",
            "mime_type": item.get("mime_type") or "application/octet-stream",
            "kind": item.get("kind") or "file",
            "size": item.get("size") or 0,
            "content": (item.get("content") or "")[:12000],
            "target_mode": target_mode,
            "target_models": [m for m in target_models if isinstance(m, str)],
        })

    return normalized


def _attachment_matches_model(attachment: Dict[str, Any], model: str) -> bool:
    if attachment.get("target_mode") == "all":
        return True
    return model in (attachment.get("target_models") or [])


def _build_attachment_context(attachments: List[Dict[str, Any]], model: str) -> str:
    chunks = []
    for att in attachments:
        if not _attachment_matches_model(att, model):
            continue

        name = att.get("name", "attachment")
        kind = att.get("kind", "file")
        mime_type = att.get("mime_type", "application/octet-stream")
        size = att.get("size", 0)
        content = (att.get("content") or "").strip()
        snippet = content[:3000]

        if snippet:
            chunks.append(
                f"- {name} ({kind}, {mime_type}, {size} bytes)\n"
                f"  Content excerpt:\n{snippet}"
            )
        else:
            chunks.append(f"- {name} ({kind}, {mime_type}, {size} bytes)")

    return "\n\n".join(chunks)


def _normalize_shared_pairs(shared_pairs: Dict[str, List[str]] | None, models: List[str]) -> Dict[str, List[str]]:
    normalized: Dict[str, List[str]] = {model: [] for model in models}
    if not isinstance(shared_pairs, dict):
        return normalized

    valid_models = set(models)
    for model, peers in shared_pairs.items():
        if model not in valid_models or not isinstance(peers, list):
            continue
        normalized[model] = [peer for peer in peers if isinstance(peer, str) and peer in valid_models and peer != model]
    return normalized


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user)
):
    """Stream responses from multiple AI models"""

    async def event_generator():
        conversation_id = request.conversation_id or str(uuid.uuid4())
        normalized_attachments = _normalize_attachments(request.attachments)
        shared_pairs = _normalize_shared_pairs(request.shared_pairs, request.models)

        # Persist the *base* user message once (per prompt) unless caller disables it.
        if request.persist_user_message:
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
            if normalized_attachments:
                user_msg["attachments"] = normalized_attachments
            await db.messages.insert_one(user_msg)

        # Pull a bit more history; we filter per-model later depending on context_mode.
        history_limit = request.history_limit if request.history_limit is not None else 30
        history = []
        if history_limit > 0:
            history = await db.messages.find(
                {"conversation_id": conversation_id, "user_id": get_user_id(current_user)},
                {"_id": 0}
            ).sort("timestamp", 1).limit(history_limit).to_list(history_limit)

        for model_spec in request.models:
            try:
                model_lower = model_spec.lower()
                message_id = str(uuid.uuid4())
                t_start = time.time()

                # Build per-model context (compartmented vs shared-room)
                per_model_prompt = (request.per_model_messages or {}).get(model_spec) or request.message
                attachment_context = _build_attachment_context(normalized_attachments, model_spec)
                if attachment_context:
                    per_model_prompt = f"{per_model_prompt}\n\n[ATTACHMENTS]\n{attachment_context}"

                messages_context = []
                # include user messages always; assistant messages depend on context_mode
                for msg in history[-30:]:
                    if msg["role"] == "assistant":
                        if request.context_mode == "compartmented" and msg.get("model") != model_spec:
                            continue
                        if request.context_mode == "shared":
                            if request.shared_room_mode == "parallel_paired":
                                allowed_models = set(shared_pairs.get(model_spec, []))
                                allowed_models.add(model_spec)
                                if msg.get("model") not in allowed_models:
                                    continue
                            messages_context.append({
                                "role": "assistant",
                                "content": f"[{msg.get('model', 'unknown')}] {msg.get('content', '')}"
                            })
                        else:
                            messages_context.append({
                                "role": "assistant",
                                "content": msg.get("content", "")
                            })
                    elif msg["role"] == "user":
                        messages_context.append({
                            "role": "user",
                            "content": msg.get("content", "")
                        })

                # If we did persist a base user message, replace the last user turn with the model-specific prompt.
                if request.persist_user_message:
                    if messages_context and messages_context[-1]["role"] == "user":
                        messages_context[-1] = {"role": "user", "content": per_model_prompt}
                    else:
                        messages_context.append({"role": "user", "content": per_model_prompt})
                # If we did NOT persist, append the prompt just for this call.
                if not request.persist_user_message:
                    messages_context.append({"role": "user", "content": per_model_prompt})

                yield {
                    "event": "start",
                    "data": json.dumps({"model": model_spec, "message_id": message_id})
                }

                full_response = ""

                if "gpt" in model_lower or model_lower.startswith("o"):
                    api_key = get_api_key(current_user, "gpt")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_emergent_model(api_key, model_spec, "openai", messages_context, conversation_id):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "claude" in model_lower:
                    api_key = get_api_key(current_user, "claude")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_emergent_model(api_key, model_spec, "anthropic", messages_context, conversation_id):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "gemini" in model_lower:
                    api_key = get_api_key(current_user, "gemini")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_emergent_model(api_key, model_spec, "gemini", messages_context, conversation_id):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "grok" in model_lower:
                    api_key = get_api_key(current_user, "grok")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_openai_compatible("https://api.x.ai/v1", api_key, model_spec, messages_context):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "deepseek" in model_lower:
                    api_key = get_api_key(current_user, "deepseek")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_openai_compatible("https://api.deepseek.com", api_key, model_spec, messages_context):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                elif "perplexity" in model_lower or "sonar" in model_lower:
                    api_key = get_api_key(current_user, "perplexity")
                    if not api_key:
                        err = "No API key configured"
                        yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {err}"})}
                        full_response = f"[ERROR] {err}"
                    else:
                        async for chunk in stream_openai_compatible("https://api.perplexity.ai", api_key, model_spec, messages_context):
                            if chunk:
                                full_response += chunk
                                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": chunk})}

                response_time_ms = int((time.time() - t_start) * 1000)
                assistant_msg = {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": full_response,
                    "model": model_spec,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": get_user_id(current_user),
                    "feedback": None,
                    "response_time_ms": response_time_ms
                }
                await db.messages.insert_one(assistant_msg)

                yield {"event": "complete", "data": json.dumps({"model": model_spec, "message_id": message_id, "response_time_ms": response_time_ms})}

            except Exception as e:
                logger.error(f"Error streaming from {model_spec}: {str(e)}")
                yield {"event": "chunk", "data": json.dumps({"model": model_spec, "message_id": message_id, "content": f"[ERROR] {str(e)}"})}

                response_time_ms = int((time.time() - t_start) * 1000)
                assistant_msg = {
                    "id": message_id,
                    "conversation_id": conversation_id,
                    "role": "assistant",
                    "content": f"[ERROR] {str(e)}",
                    "model": model_spec,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user_id": get_user_id(current_user),
                    "feedback": None,
                    "response_time_ms": response_time_ms
                }
                await db.messages.insert_one(assistant_msg)

                yield {"event": "complete", "data": json.dumps({"model": model_spec, "message_id": message_id, "response_time_ms": response_time_ms})}

        update_fields = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "title": request.message[:50],
            "context_mode": request.context_mode,
            "shared_room_mode": request.shared_room_mode
        }
        if request.shared_pairs is not None:
            update_fields["shared_pairs"] = shared_pairs
        if request.global_context is not None:
            update_fields["global_context"] = request.global_context
        if request.model_roles is not None:
            update_fields["model_roles"] = request.model_roles

        await db.conversations.update_one(
            {"id": conversation_id},
            {
                "$set": update_fields,
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
