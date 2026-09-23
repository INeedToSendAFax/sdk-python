"""Data models returned by the API."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value or not isinstance(value, str):
        return None
    v = value.replace("Z", "+00:00") if value.endswith("Z") else value
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        return None


@dataclass
class Fax:
    """A fax job."""

    id: str = ""
    status: str = ""
    to: str = ""
    pages: int = 0
    price_cents: int = 0
    bitrate: int = 0
    mode: str = ""
    error: str = ""
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Fax":
        return cls(
            id=d.get("id", ""),
            status=d.get("status", ""),
            to=d.get("to", ""),
            pages=d.get("pages") or 0,
            price_cents=d.get("price_cents") or 0,
            bitrate=d.get("bitrate") or 0,
            mode=d.get("mode", "") or "",
            error=d.get("error", "") or "",
            created_at=_parse_dt(d.get("created_at")),
            completed_at=_parse_dt(d.get("completed_at")),
        )


@dataclass
class FaxList:
    """A page of recent faxes plus the account balance."""

    data: List[Fax] = field(default_factory=list)
    balance_cents: int = 0

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "FaxList":
        return cls(
            data=[Fax.from_dict(x) for x in d.get("data", [])],
            balance_cents=d.get("balance_cents") or 0,
        )


@dataclass
class Account:
    """Response from ``GET /v1/me``."""

    key_prefix: str = ""
    email: str = ""
    balance_cents: int = 0
    price_cents: int = 0
    max_pages: int = 0
    rate_limit_per_min: int = 0
    daily_cap: int = 0
    faxes_last_24h: int = 0
    callback_secret_set: bool = False

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Account":
        return cls(
            key_prefix=d.get("key_prefix", ""),
            email=d.get("email", ""),
            balance_cents=d.get("balance_cents") or 0,
            price_cents=d.get("price_cents") or 0,
            max_pages=d.get("max_pages") or 0,
            rate_limit_per_min=d.get("rate_limit_per_min") or 0,
            daily_cap=d.get("daily_cap") or 0,
            faxes_last_24h=d.get("faxes_last_24h") or 0,
            callback_secret_set=bool(d.get("callback_secret_set")),
        )


@dataclass
class Pricing:
    """Response from ``GET /v1/pricing``."""

    price_cents: int = 0
    currency: str = "usd"
    max_pages: int = 0
    min_credit_cents: int = 0
    countries: List[str] = field(default_factory=list)
    cover_available: bool = False
    callbacks: bool = False
    idempotency_header: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Pricing":
        return cls(
            price_cents=d.get("price_cents") or 0,
            currency=d.get("currency", "usd"),
            max_pages=d.get("max_pages") or 0,
            min_credit_cents=d.get("min_credit_cents") or 0,
            countries=list(d.get("countries") or []),
            cover_available=bool(d.get("cover_available")),
            callbacks=bool(d.get("callbacks")),
            idempotency_header=d.get("idempotency_header", ""),
        )


@dataclass
class Event:
    """A fax status webhook callback."""

    id: str = ""
    status: str = ""
    to: str = ""
    pages: int = 0
    bitrate: int = 0
    mode: str = ""
    error: str = ""
    completed_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Event":
        return cls(
            id=d.get("id", ""),
            status=d.get("status", ""),
            to=d.get("to", ""),
            pages=d.get("pages") or 0,
            bitrate=d.get("bitrate") or 0,
            mode=d.get("mode", "") or "",
            error=d.get("error", "") or "",
            completed_at=_parse_dt(d.get("completed_at")),
        )
