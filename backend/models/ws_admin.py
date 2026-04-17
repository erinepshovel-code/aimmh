# "lines of code":"18","lines of commented":"0"
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TierUpdateRequest(BaseModel):
    updates: Dict[str, Any] = Field(default_factory=dict)


class PricingPackageUpdateRequest(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = Field(default=None, ge=0)
    currency: Optional[str] = None
    billing_type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    grants_tier: Optional[str] = None
    stripe_price_id: Optional[str] = None
    stripe_product_id: Optional[str] = None
    features: Optional[List[str]] = None


class CliExecuteRequest(BaseModel):
    command: str

# "lines of code":"18","lines of commented":"0"
