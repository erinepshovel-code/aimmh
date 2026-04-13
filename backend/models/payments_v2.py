# "lines of code":"65","lines of commented":"0"
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, HttpUrl

PaymentCategory = Literal["supporter", "pro", "team", "team_addon"]
BillingType = Literal["one_time", "monthly", "yearly"]


class CheckoutCreateRequestV2(BaseModel):
    package_id: str
    origin_url: str
    custom_amount: Optional[float] = Field(default=None, ge=1.0, le=10000.0)


class CheckoutCreateResponseV2(BaseModel):
    url: str
    session_id: str


class PaymentStatusResponseV2(BaseModel):
    session_id: str
    status: str
    payment_status: str
    amount_total: float
    currency: str
    package_id: Optional[str] = None


class CatalogPriceV2(BaseModel):
    package_id: str
    name: str
    amount: float
    currency: str
    billing_type: BillingType
    category: PaymentCategory
    description: str
    features: List[str] = Field(default_factory=list)
    stripe_price_id: Optional[str] = None
    grants_tier: Optional[str] = None


class CatalogResponseV2(BaseModel):
    prices: List[CatalogPriceV2]
    current_tier: str


class PaymentSummaryResponseV2(BaseModel):
    current_tier: str
    hide_emergent_badge: bool
    max_instances: Optional[int] = None
    max_runs_per_month: Optional[int] = None
    per_model_instance_cap: Optional[int] = None
    max_personas: Optional[int] = None
    hosted_requests_per_month: Optional[int] = None
    max_connected_keys: Optional[int] = None
    max_batch_size: Optional[int] = None
    daily_chats_per_24h: Optional[int] = None
    daily_batch_runs_per_24h: Optional[int] = None
    daily_roleplay_runs_per_24h: Optional[int] = None
    queue_priority: Optional[str] = None
    total_paid_usd: float
    total_supporter_usd: float
    total_pro_usd: float
    total_team_usd: float
    total_donation_usd: float
    team_seats: int = 1


class HallProfileUpdateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    link: Optional[HttpUrl] = None
    opt_in: bool = True


class HallMakerEntry(BaseModel):
    user_id: str
    display_name: str
    link: Optional[str] = None
    tier: str
    created_at: str


class HallOfMakersResponse(BaseModel):
    entries: List[HallMakerEntry] = Field(default_factory=list)
# "lines of code":"65","lines of commented":"0"
