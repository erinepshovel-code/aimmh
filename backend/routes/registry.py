"""Model registry management — add/remove developers and models."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException

from db import db
from models.v1 import AddDeveloperRequest, AddModelRequest, RegistryResponse, DeveloperDef, ModelDef
from services.auth import get_current_user, get_user_id
from services.llm import DEFAULT_REGISTRY

router = APIRouter(prefix="/api/v1/registry", tags=["registry"])


async def _get_or_seed_registry(user_id: str) -> dict:
    """Get user's registry doc, seeding from defaults if missing."""
    doc = await db.model_registry.find_one({"user_id": user_id}, {"_id": 0})
    if doc:
        return doc
    # Seed from defaults
    seed = {
        "user_id": user_id,
        "developers": DEFAULT_REGISTRY,
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
            models=models,
        ))

    return RegistryResponse(developers=result)


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
    await db.model_registry.update_one(
        {"user_id": uid},
        {
            "$unset": {f"developers.{developer_id}": ""},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()},
        },
    )
    return {"message": f"Developer {developer_id} removed"}
