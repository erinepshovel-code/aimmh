"""Model registry management — add/remove developers and models."""

import math
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from db import db
from models.registry import VerificationResponse, VerifyModelRequest
from models.v1 import AddDeveloperRequest, AddModelRequest, RegistryResponse, DeveloperDef, ModelDef
from services.auth import get_current_user, get_user_id
from services.llm import (
    DEFAULT_REGISTRY,
    UNIVERSAL_DEVELOPER_IDS,
    model_default_payload,
    reconcile_registry_developers,
    universal_managed_model_ids,
)
from services.registry_verifier import verify_developer_models, verify_registry, verify_single_model

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])
HUB_INSTANCE_COLLECTION = "hub_instances"
HUB_RUN_COLLECTION = "hub_runs"
HUB_CHAT_PROMPT_COLLECTION = "hub_chat_prompts"
HUB_SYNTHESIS_BATCH_COLLECTION = "hub_synthesis_batches"


async def _get_or_seed_registry(user_id: str) -> dict:
    """Get user's registry doc, seeding from defaults if missing."""
    doc = await db.model_registry.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        developers, changed = reconcile_registry_developers(doc.get("developers", {}))
        if changed:
            doc["developers"] = developers
            doc["updated_at"] = datetime.now(timezone.utc).isoformat()
            await db.model_registry.update_one(
                {"user_id": user_id},
                {"$set": {"developers": developers, "updated_at": doc["updated_at"]}},
            )
        return doc
    # Seed from defaults
    seed = {
        "user_id": user_id,
        "developers": reconcile_registry_developers(DEFAULT_REGISTRY)[0],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.model_registry.insert_one(seed)
    seed.pop("_id", None)
    return seed


@router.get("", response_model=RegistryResponse)
async def get_registry(current_user: dict = Depends(get_current_user)):
    """Get the user's model registry."""
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    devs = doc.get("developers", {})

    result = []
    for dev_id, dev in devs.items():
        models = []
        for m in dev.get("models", []):
            if isinstance(m, dict):
                models.append(ModelDef(model_id=m["model_id"], display_name=m.get("display_name"), enabled=m.get("enabled", True)))
            else:
                models.append(ModelDef(model_id=m))
        result.append(DeveloperDef(
            developer_id=dev_id,
            name=dev.get("name", dev_id),
            auth_type=dev.get("auth_type", "emergent"),
            base_url=dev.get("base_url"),
            website=dev.get("website"),
            models=models,
        ))

    return RegistryResponse(developers=result)


@router.get("/defaults")
async def get_registry_model_defaults(current_user: dict = Depends(get_current_user)):
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    developers = doc.get("developers", {})
    result = {}
    for developer_id, developer in developers.items():
        models = developer.get("models", [])
        result[developer_id] = {
            "models": {
                model.get("model_id"): model_default_payload(developer_id, model.get("model_id"))
                for model in models
                if isinstance(model, dict) and model.get("model_id")
            }
        }
    return {"defaults": result}


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(str(text)) / 4))


@router.get("/usage")
async def get_registry_usage_totals(current_user: dict = Depends(get_current_user)):
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    developers = doc.get("developers", {})

    model_to_developer = {}
    usage = {}
    for developer_id, developer in developers.items():
        usage[developer_id] = {
            "developer_id": developer_id,
            "name": developer.get("name", developer_id),
            "total_tokens": 0,
            "models": {},
        }
        for model in developer.get("models", []):
            model_id = model.get("model_id") if isinstance(model, dict) else None
            if not model_id:
                continue
            model_to_developer[model_id] = developer_id
            usage[developer_id]["models"][model_id] = {
                "model_id": model_id,
                "display_name": model.get("display_name", model_id),
                "total_tokens": 0,
                "instances": {},
            }

    instance_docs = await db[HUB_INSTANCE_COLLECTION].find(
        {"user_id": uid},
        {"_id": 0, "instance_id": 1, "name": 1},
    ).to_list(5000)
    instance_name_map = {item.get("instance_id"): item.get("name") for item in instance_docs}

    def add_usage(model_id: str, instance_id: str | None, content: str):
        developer_id = model_to_developer.get(model_id)
        if not developer_id:
            return
        model_bucket = usage[developer_id]["models"].get(model_id)
        if not model_bucket:
            return
        tokens = _estimate_tokens(content)
        model_bucket["total_tokens"] += tokens
        usage[developer_id]["total_tokens"] += tokens
        if instance_id:
            if instance_id not in model_bucket["instances"]:
                model_bucket["instances"][instance_id] = {
                    "instance_id": instance_id,
                    "instance_name": instance_name_map.get(instance_id) or instance_id,
                    "tokens": 0,
                }
            model_bucket["instances"][instance_id]["tokens"] += tokens

    run_docs = await db[HUB_RUN_COLLECTION].find(
        {"user_id": uid},
        {"_id": 0, "results": 1},
    ).to_list(1000)
    for run in run_docs:
        for result in run.get("results", []):
            add_usage(result.get("model"), result.get("instance_id"), result.get("content", ""))

    prompt_docs = await db[HUB_CHAT_PROMPT_COLLECTION].find(
        {"user_id": uid},
        {"_id": 0, "responses": 1},
    ).to_list(1000)
    for prompt in prompt_docs:
        for response in prompt.get("responses", []):
            add_usage(response.get("model"), response.get("instance_id"), response.get("content", ""))

    synthesis_docs = await db[HUB_SYNTHESIS_BATCH_COLLECTION].find(
        {"user_id": uid},
        {"_id": 0, "outputs": 1},
    ).to_list(1000)
    for batch in synthesis_docs:
        for output in batch.get("outputs", []):
            add_usage(output.get("model"), output.get("synthesis_instance_id"), output.get("content", ""))

    developers_out = []
    grand_total = 0
    for developer_id, dev in usage.items():
        model_values = []
        for model in dev["models"].values():
            model["instances"] = sorted(model["instances"].values(), key=lambda x: x["tokens"], reverse=True)
            model_values.append(model)
        model_values.sort(key=lambda x: x["total_tokens"], reverse=True)
        dev["models"] = model_values
        grand_total += dev["total_tokens"]
        developers_out.append(dev)
    developers_out.sort(key=lambda x: x["total_tokens"], reverse=True)

    return {
        "grand_total_tokens": grand_total,
        "developers": developers_out,
    }


@router.post("/developer")
async def add_developer(
    request: AddDeveloperRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a new developer to the registry."""
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)

    if request.developer_id in doc.get("developers", {}):
        raise HTTPException(status_code=400, detail="Developer already exists")

    new_dev = {
        "name": request.name,
        "auth_type": request.auth_type,
        "base_url": request.base_url,
        "website": request.website,
        "models": [m.model_dump() for m in request.models],
    }

    await db.model_registry.update_one(
        {"user_id": uid},
        {
            "$set": {
                f"developers.{request.developer_id}": new_dev,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        },
    )
    return {"message": f"Developer {request.developer_id} added", "developer": new_dev}


@router.post("/developer/{developer_id}/model")
async def add_model(
    developer_id: str,
    request: AddModelRequest,
    current_user: dict = Depends(get_current_user),
):
    """Add a model to an existing developer."""
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)

    if developer_id not in doc.get("developers", {}):
        raise HTTPException(status_code=404, detail="Developer not found")

    developer = doc["developers"].get(developer_id, {})
    if developer.get("auth_type") == "emergent":
        allowed_model_ids = universal_managed_model_ids(developer_id)
        if request.model_id not in allowed_model_ids:
            raise HTTPException(status_code=400, detail="This universal-key registry is curated. Only supported universal-key models are allowed for this developer.")
        if any(model.get("model_id") == request.model_id for model in developer.get("models", []) if isinstance(model, dict)):
            raise HTTPException(status_code=400, detail="Model already exists")

    model_entry = {"model_id": request.model_id, "display_name": request.display_name, "enabled": True}

    await db.model_registry.update_one(
        {"user_id": uid},
        {
            "$push": {f"developers.{developer_id}.models": model_entry},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return {"message": f"Model {request.model_id} added to {developer_id}"}


@router.delete("/developer/{developer_id}/model/{model_id}")
async def remove_model(
    developer_id: str,
    model_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a model from a developer."""
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    developer = doc.get("developers", {}).get(developer_id, {})
    if developer_id in UNIVERSAL_DEVELOPER_IDS or developer.get("auth_type") == "emergent":
        raise HTTPException(status_code=400, detail="Universal-key-compatible registry models are managed automatically and cannot be removed.")
    await db.model_registry.update_one(
        {"user_id": uid},
        {
            "$pull": {f"developers.{developer_id}.models": {"model_id": model_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return {"message": f"Model {model_id} removed from {developer_id}"}


@router.delete("/developer/{developer_id}")
async def remove_developer(
    developer_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Remove a developer from the registry."""
    uid = get_user_id(current_user)
    if developer_id in UNIVERSAL_DEVELOPER_IDS:
        raise HTTPException(status_code=400, detail="Universal-key-compatible developers are managed automatically and cannot be removed.")
    await db.model_registry.update_one(
        {"user_id": uid},
        {
            "$unset": {f"developers.{developer_id}": ""},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return {"message": f"Developer {developer_id} removed"}


@router.post("/verify/model", response_model=VerificationResponse)
async def verify_registry_model(
    request: VerifyModelRequest,
    current_user: dict = Depends(get_current_user),
):
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    registry = doc.get("developers", {})
    result = await verify_single_model(current_user, registry, request.developer_id, request.model_id, mode=request.mode)
    return VerificationResponse(
        scope="model",
        verification_mode=request.mode,
        verified_count=1 if result.status in {"verified", "verified_via_provider"} else 0,
        total_count=1,
        results=[result],
    )


@router.post("/verify/developer/{developer_id}", response_model=VerificationResponse)
async def verify_registry_developer(
    developer_id: str,
    current_user: dict = Depends(get_current_user),
):
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    registry = doc.get("developers", {})
    return await verify_developer_models(current_user, registry, developer_id, mode="light")


@router.post("/verify/all", response_model=VerificationResponse)
async def verify_registry_all(current_user: dict = Depends(get_current_user)):
    uid = get_user_id(current_user)
    doc = await _get_or_seed_registry(uid)
    registry = doc.get("developers", {})
    return await verify_registry(current_user, registry, mode="light")
