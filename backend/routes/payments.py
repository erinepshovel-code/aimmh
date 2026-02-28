from fastapi import APIRouter, Depends, HTTPException, Request
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
import logging
import os
import uuid

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

from db import db
from models.payments import (
    CheckoutCreateRequest,
    CheckoutCreateResponse,
    PaymentStatusResponse,
    CatalogResponse,
    CatalogPrice,
    PaymentSummaryResponse,
)
from services.auth import get_current_user, get_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["payments"])

FOUNDER_LIMIT = 53

PAYMENT_PACKAGES: Dict[str, Dict[str, Any]] = {
    "core_monthly": {
        "name": "$15 / month — Core Access",
        "amount": 15.00,
        "currency": "usd",
        "billing_type": "monthly",
        "category": "core",
        "description": "Full console access · EDCM instrumentation · Hourly heartbeat · BYO API keys · Cost telemetry",
        "features": [
            "Full console access",
            "EDCM instrumentation",
            "Hourly heartbeat",
            "BYO API keys",
            "Cost telemetry",
        ],
    },
    "support_one_time_1": {
        "name": "Optional Support +$1 (one-time)",
        "amount": 1.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "support",
        "description": "One-time support contribution",
        "features": ["One-time support"],
    },
    "support_one_time_2": {
        "name": "Optional Support +$2 (one-time)",
        "amount": 2.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "support",
        "description": "One-time support contribution",
        "features": ["One-time support"],
    },
    "support_one_time_5": {
        "name": "Optional Support +$5 (one-time)",
        "amount": 5.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "support",
        "description": "One-time support contribution",
        "features": ["One-time support"],
    },
    "support_monthly_1": {
        "name": "Optional Support +$1/month",
        "amount": 1.00,
        "currency": "usd",
        "billing_type": "monthly",
        "category": "support",
        "description": "Recurring monthly support",
        "features": ["Recurring support"],
    },
    "support_monthly_2": {
        "name": "Optional Support +$2/month",
        "amount": 2.00,
        "currency": "usd",
        "billing_type": "monthly",
        "category": "support",
        "description": "Recurring monthly support",
        "features": ["Recurring support"],
    },
    "support_monthly_5": {
        "name": "Optional Support +$5/month",
        "amount": 5.00,
        "currency": "usd",
        "billing_type": "monthly",
        "category": "support",
        "description": "Recurring monthly support",
        "features": ["Recurring support"],
    },
    "founder_one_time": {
        "name": "Founder — $153 one-time",
        "amount": 153.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "founder",
        "description": "Founder registry listing · Founder badge · Locked $15 base rate while active · Early refinement channel",
        "features": [
            "Founder registry listing",
            "Founder badge",
            "Locked $15 base rate while active",
            "Early refinement channel",
        ],
    },
    "credits_10": {
        "name": "Compute Credits $10",
        "amount": 10.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "credits",
        "description": "Compute credits block",
        "features": ["$10 compute credits"],
    },
    "credits_25": {
        "name": "Compute Credits $25",
        "amount": 25.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "credits",
        "description": "Compute credits block",
        "features": ["$25 compute credits"],
    },
    "credits_50": {
        "name": "Compute Credits $50",
        "amount": 50.00,
        "currency": "usd",
        "billing_type": "one_time",
        "category": "credits",
        "description": "Compute credits block",
        "features": ["$50 compute credits"],
    },
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stripe_key() -> str:
    return os.environ["STRIPE_API_KEY"]


def _build_stripe_checkout(request: Request) -> StripeCheckout:
    host_url = str(request.base_url).rstrip("/")
    webhook_url = f"{host_url}/api/webhook/stripe"
    return StripeCheckout(api_key=_stripe_key(), webhook_url=webhook_url)


def _create_product_and_price(package_id: str, package: Dict[str, Any]) -> Dict[str, str]:
    stripe.api_key = _stripe_key()

    product = stripe.Product.create(
        name=package["name"],
        description=package["description"],
        metadata={
            "package_id": package_id,
            "category": package["category"],
            "billing_type": package["billing_type"],
        },
    )

    price_payload: Dict[str, Any] = {
        "unit_amount": int(round(package["amount"] * 100)),
        "currency": package["currency"],
        "product": product["id"],
        "metadata": {
            "package_id": package_id,
            "category": package["category"],
            "billing_type": package["billing_type"],
        },
    }

    if package["billing_type"] == "monthly":
        price_payload["recurring"] = {"interval": "month"}

    price = stripe.Price.create(**price_payload)
    return {"product_id": product["id"], "price_id": price["id"]}


async def _ensure_catalog_seeded() -> None:
    for package_id, package in PAYMENT_PACKAGES.items():
        existing = await db.payment_catalog.find_one({"package_id": package_id}, {"_id": 0})
        if existing and existing.get("stripe_price_id"):
            continue

        created = await asyncio.to_thread(_create_product_and_price, package_id, package)
        await db.payment_catalog.update_one(
            {"package_id": package_id},
            {
                "$set": {
                    "package_id": package_id,
                    "stripe_product_id": created["product_id"],
                    "stripe_price_id": created["price_id"],
                    "updated_at": _iso_now(),
                },
                "$setOnInsert": {
                    "created_at": _iso_now(),
                },
            },
            upsert=True,
        )


async def _founder_slots_remaining() -> int:
    one_hour_ago = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    paid_count = await db.payment_transactions.count_documents({
        "package_id": "founder_one_time",
        "payment_status": "paid",
    })
    pending_count = await db.payment_transactions.count_documents({
        "package_id": "founder_one_time",
        "payment_status": {"$in": ["pending", "unpaid"]},
        "created_at": {"$gte": one_hour_ago},
    })
    used = min(FOUNDER_LIMIT, paid_count + pending_count)
    return max(0, FOUNDER_LIMIT - used)


async def _fulfill_transaction_once(session_id: str) -> None:
    tx = await db.payment_transactions.find_one({"session_id": session_id}, {"_id": 0})
    if not tx:
        return

    lock_result = await db.payment_transactions.update_one(
        {"session_id": session_id, "fulfilled": {"$ne": True}},
        {"$set": {"fulfilled": True, "fulfilled_at": _iso_now(), "updated_at": _iso_now()}},
    )
    if lock_result.modified_count == 0:
        return

    user_id = tx.get("user_id")
    if not user_id:
        return

    package_id = tx.get("package_id")
    package = PAYMENT_PACKAGES.get(package_id)
    if not package:
        return

    inc_fields: Dict[str, Any] = {"billing.total_paid_usd": float(package["amount"])}
    set_fields: Dict[str, Any] = {"billing.updated_at": _iso_now()}

    category = package["category"]
    if category == "core":
        set_fields["billing.core_access_active"] = True
        set_fields["billing.locked_core_rate_usd"] = 15.00
    elif category == "support":
        inc_fields["billing.total_support_usd"] = float(package["amount"])
        if package["billing_type"] == "monthly":
            set_fields["billing.support_subscription_active"] = True
    elif category == "founder":
        set_fields["billing.founder_badge"] = True
        set_fields["billing.locked_core_rate_usd"] = 15.00
    elif category == "credits":
        inc_fields["billing.compute_credit_balance_usd"] = float(package["amount"])

    await db.users.update_one(
        {"$or": [{"id": user_id}, {"user_id": user_id}]},
        {"$inc": inc_fields, "$set": set_fields},
    )

    if category == "founder":
        user_doc = await db.users.find_one(
            {"$or": [{"id": user_id}, {"user_id": user_id}]},
            {"_id": 0, "username": 1, "email": 1},
        )
        await db.founder_registry.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "username": user_doc.get("username") if user_doc else None,
                    "email": user_doc.get("email") if user_doc else None,
                    "session_id": session_id,
                    "updated_at": _iso_now(),
                },
                "$setOnInsert": {
                    "created_at": _iso_now(),
                },
            },
            upsert=True,
        )


@router.post("/payments/seed-products")
async def seed_products(current_user: dict = Depends(get_current_user)):
    _ = current_user
    await _ensure_catalog_seeded()
    return {"message": "Stripe catalog seeded"}


@router.get("/payments/catalog", response_model=CatalogResponse)
async def get_catalog(current_user: dict = Depends(get_current_user)):
    _ = current_user
    await _ensure_catalog_seeded()
    founder_remaining = await _founder_slots_remaining()

    catalog_rows = await db.payment_catalog.find({}, {"_id": 0}).to_list(200)
    stripe_price_map = {row["package_id"]: row.get("stripe_price_id") for row in catalog_rows}

    prices = []
    for package_id, package in PAYMENT_PACKAGES.items():
        prices.append(CatalogPrice(
            package_id=package_id,
            name=package["name"],
            amount=float(package["amount"]),
            currency=package["currency"],
            billing_type=package["billing_type"],
            category=package["category"],
            description=package["description"],
            features=package.get("features", []),
            stripe_price_id=stripe_price_map.get(package_id),
        ))

    return CatalogResponse(
        prices=prices,
        founder_slots_total=FOUNDER_LIMIT,
        founder_slots_remaining=founder_remaining,
    )


@router.post("/payments/checkout/session", response_model=CheckoutCreateResponse)
async def create_checkout_session(
    checkout_data: CheckoutCreateRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    package = PAYMENT_PACKAGES.get(checkout_data.package_id)
    if not package:
        raise HTTPException(status_code=400, detail="Invalid package")

    if not checkout_data.origin_url.startswith("http://") and not checkout_data.origin_url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Invalid origin URL")

    if checkout_data.package_id == "founder_one_time":
        remaining = await _founder_slots_remaining()
        if remaining <= 0:
            raise HTTPException(status_code=409, detail="Founder slots are sold out")

    await _ensure_catalog_seeded()
    price_doc = await db.payment_catalog.find_one({"package_id": checkout_data.package_id}, {"_id": 0})
    if not price_doc or not price_doc.get("stripe_price_id"):
        raise HTTPException(status_code=500, detail="Stripe catalog unavailable for selected package")

    user_id = get_user_id(current_user)
    user_email = current_user.get("email") or current_user.get("username") or ""
    base_url = checkout_data.origin_url.rstrip("/")
    success_url = f"{base_url}/pricing?session_id={{CHECKOUT_SESSION_ID}}&checkout=success"
    cancel_url = f"{base_url}/pricing?checkout=cancel"

    metadata = {
        "user_id": str(user_id),
        "email": str(user_email),
        "package_id": checkout_data.package_id,
        "billing_type": package["billing_type"],
        "category": package["category"],
    }

    stripe_checkout = _build_stripe_checkout(request)
    checkout_request = CheckoutSessionRequest(
        stripe_price_id=price_doc["stripe_price_id"],
        quantity=1,
        success_url=success_url,
        cancel_url=cancel_url,
        metadata=metadata,
    )

    session = await stripe_checkout.create_checkout_session(checkout_request)

    tx_doc = {
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "payment_id": None,
        "package_id": checkout_data.package_id,
        "user_id": user_id,
        "email": user_email,
        "amount": float(package["amount"]),
        "currency": package["currency"],
        "category": package["category"],
        "billing_type": package["billing_type"],
        "status": "initiated",
        "payment_status": "pending",
        "metadata": metadata,
        "stripe_price_id": price_doc["stripe_price_id"],
        "created_at": _iso_now(),
        "updated_at": _iso_now(),
        "fulfilled": False,
    }
    await db.payment_transactions.update_one(
        {"session_id": session.session_id},
        {"$set": tx_doc},
        upsert=True,
    )

    return CheckoutCreateResponse(url=session.url, session_id=session.session_id)


@router.get("/payments/checkout/status/{session_id}", response_model=PaymentStatusResponse)
async def get_checkout_status(
    session_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    _ = current_user
    stripe_checkout = _build_stripe_checkout(request)
    status = await stripe_checkout.get_checkout_status(session_id)

    amount_total = float(status.amount_total) / 100.0 if status.amount_total else 0.0
    metadata = status.metadata or {}
    package_id = metadata.get("package_id")

    await db.payment_transactions.update_one(
        {"session_id": session_id},
        {
            "$set": {
                "status": status.status,
                "payment_status": status.payment_status,
                "amount_total": amount_total,
                "currency": status.currency,
                "metadata": metadata,
                "updated_at": _iso_now(),
            }
        },
    )

    if status.payment_status == "paid":
        await _fulfill_transaction_once(session_id)

    return PaymentStatusResponse(
        session_id=session_id,
        status=status.status,
        payment_status=status.payment_status,
        amount_total=amount_total,
        currency=status.currency,
        package_id=package_id,
    )


@router.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    stripe_checkout = _build_stripe_checkout(request)
    body = await request.body()
    signature = request.headers.get("Stripe-Signature")

    webhook_response = await stripe_checkout.handle_webhook(body, signature)
    session_id = webhook_response.session_id

    if session_id:
        await db.payment_transactions.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "event_type": webhook_response.event_type,
                    "event_id": webhook_response.event_id,
                    "payment_status": webhook_response.payment_status or "pending",
                    "status": webhook_response.event_type,
                    "metadata": webhook_response.metadata or {},
                    "updated_at": _iso_now(),
                }
            },
        )

        if webhook_response.payment_status == "paid":
            await _fulfill_transaction_once(session_id)

    return {"ok": True}


@router.get("/payments/summary", response_model=PaymentSummaryResponse)
async def get_payments_summary(current_user: dict = Depends(get_current_user)):
    user_id = get_user_id(current_user)
    paid_transactions = await db.payment_transactions.find(
        {"user_id": user_id, "payment_status": "paid"},
        {"_id": 0, "amount": 1, "category": 1},
    ).to_list(5000)

    total_paid = 0.0
    total_support = 0.0
    total_founder = 0.0
    total_compute = 0.0
    total_core = 0.0
    for tx in paid_transactions:
        amount = float(tx.get("amount") or 0.0)
        category = tx.get("category")
        total_paid += amount
        if category == "support":
            total_support += amount
        elif category == "founder":
            total_founder += amount
        elif category == "credits":
            total_compute += amount
        elif category == "core":
            total_core += amount

    usage_rows = await db.messages.find(
        {"user_id": user_id, "role": "assistant"},
        {"_id": 0, "estimated_cost_usd": 1, "total_tokens_est": 1},
    ).to_list(10000)
    estimated_cost = round(sum(float(row.get("estimated_cost_usd") or 0.0) for row in usage_rows), 6)
    total_tokens = sum(int(row.get("total_tokens_est") or 0) for row in usage_rows)

    return PaymentSummaryResponse(
        total_paid_usd=round(total_paid, 2),
        total_support_usd=round(total_support, 2),
        total_founder_usd=round(total_founder, 2),
        total_compute_usd=round(total_compute, 2),
        total_core_usd=round(total_core, 2),
        estimated_usage_cost_usd=estimated_cost,
        total_estimated_tokens=total_tokens,
    )
