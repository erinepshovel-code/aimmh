# "lines of code":"103","lines of commented":"0"
from __future__ import annotations

import subprocess
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.routing import APIRoute

from db import db
from models.ws_admin import CliExecuteRequest, PricingPackageUpdateRequest, TierUpdateRequest
from routes import payments_v2 as payments_routes
from services.auth import get_current_user, get_user_id
from services.billing_tiers import TIER_LIMITS, derive_billing_profile, update_tier_limits
from services.registry import collect_dynamic_registry

router = APIRouter(prefix="/api/v1/ws-admin", tags=["ws_admin"])


def _is_ws_admin(current_user: dict) -> bool:
    profile = derive_billing_profile(current_user)
    return bool(profile.get("is_ws_admin"))


async def require_ws_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if not _is_ws_admin(current_user):
        raise HTTPException(status_code=403, detail="WS-Admin access required")
    return current_user


@router.get("/billing-tiers")
async def get_billing_tiers(_: dict = Depends(require_ws_admin)):
    return {"tiers": TIER_LIMITS}


@router.put("/billing-tiers/{tier}")
async def put_billing_tier(tier: str, payload: TierUpdateRequest, current_user: dict = Depends(require_ws_admin)):
    result = await update_tier_limits(tier, payload.updates)
    return {"ok": True, "actor": get_user_id(current_user), **result}


@router.get("/pricing-packages")
async def get_pricing_packages(_: dict = Depends(require_ws_admin)):
    await payments_routes._ensure_catalog_seeded()  # type: ignore[attr-defined]
    docs = await db.payment_catalog.find({}, {"_id": 0}).to_list(500)
    docs.sort(key=lambda row: row.get("package_id", ""))
    return {"packages": docs}


@router.put("/pricing-packages/{package_id}")
async def put_pricing_package(package_id: str, payload: PricingPackageUpdateRequest, current_user: dict = Depends(require_ws_admin)):
    await payments_routes._ensure_catalog_seeded()  # type: ignore[attr-defined]
    updates = payload.model_dump(exclude_none=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No package fields provided")

    await db.payment_catalog.update_one(
        {"package_id": package_id},
        {"$set": {**updates, "package_id": package_id, "updated_at": payments_routes.iso_now()}},  # type: ignore[attr-defined]
        upsert=True,
    )
    if package_id in payments_routes.PACKAGES:  # type: ignore[attr-defined]
        payments_routes.PACKAGES[package_id].update(updates)  # type: ignore[attr-defined]

    doc = await db.payment_catalog.find_one({"package_id": package_id}, {"_id": 0})
    return {"ok": True, "actor": get_user_id(current_user), "package": doc}


@router.get("/endpoints")
async def get_endpoints(request: Request, _: dict = Depends(require_ws_admin)):
    endpoints: List[Dict[str, Any]] = []
    for route in request.app.routes:
        if not isinstance(route, APIRoute):
            continue
        endpoints.append(
            {
                "path": route.path,
                "methods": sorted([m for m in route.methods if m not in {"HEAD", "OPTIONS"}]),
                "name": route.name,
            }
        )
    endpoints.sort(key=lambda row: row["path"])
    return {"endpoints": endpoints}


@router.get("/analytics")
async def get_analytics(_: dict = Depends(require_ws_admin)):
    return {
        "users_total": await db.users.count_documents({}),
        "instances_total": await db.hub_instances.count_documents({}),
        "groups_total": await db.hub_groups.count_documents({}),
        "runs_total": await db.hub_runs.count_documents({}),
        "chat_prompts_total": await db.hub_chat_prompts.count_documents({}),
        "synthesis_batches_total": await db.hub_synthesis_batches.count_documents({}),
        "payments_total": await db.payment_transactions.count_documents({}),
    }


def _run_shell(args: List[str]) -> dict:
    proc = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    return {
        "exit_code": proc.returncode,
        "stdout": proc.stdout[-8000:],
        "stderr": proc.stderr[-8000:],
    }


@router.post("/cli/execute")
async def execute_cli(payload: CliExecuteRequest, _: dict = Depends(require_ws_admin)):
    cmd = payload.command.strip().lower()
    if cmd == "health_check":
        try:
            await db.command("ping")
            return {"command": cmd, "exit_code": 0, "stdout": '{"status":"ok"}', "stderr": ""}
        except Exception as exc:  # pragma: no cover - defensive
            return {"command": cmd, "exit_code": 1, "stdout": "", "stderr": str(exc)}
    if cmd == "ready_check":
        try:
            await db.command("ping")
            return {"command": cmd, "exit_code": 0, "stdout": '{"status":"ready"}', "stderr": ""}
        except Exception as exc:  # pragma: no cover - defensive
            return {"command": cmd, "exit_code": 1, "stdout": "", "stderr": str(exc)}
    if cmd == "line_rules":
        return {"command": cmd, **_run_shell(["python", "/app/scripts/check_max_lines.py"])}
    if cmd == "tail_backend_logs":
        return {"command": cmd, **_run_shell(["tail", "-n", "120", "/var/log/supervisor/backend.err.log"])}
    if cmd == "sync_readme_registry":
        result = collect_dynamic_registry(sync_markers=True)
        return {"command": cmd, "result": {"module_count": result["module_count"], "violations": len(result["violations"])}}
    raise HTTPException(status_code=400, detail="Unsupported CLI command")

# "lines of code":"103","lines of commented":"0"
