"""Webhook signature verification."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from typing import Optional, Union

from .errors import SignatureVerificationError
from .models import Event

DEFAULT_TOLERANCE = 300

Body = Union[str, bytes, bytearray]


def _as_bytes(body: Body) -> bytes:
    if isinstance(body, bytes):
        return body
    if isinstance(body, bytearray):
        return bytes(body)
    return body.encode("utf-8")


def _parse_header(header: str) -> "tuple[str, str]":
    ts = sig = None
    for part in (header or "").split(","):
        part = part.strip()
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        if key == "t":
            ts = value
        elif key == "v1":
            sig = value
    if not ts or not sig:
        raise SignatureVerificationError("malformed X-Fax-Signature header")
    return ts, sig


def verify_webhook(
    secret: str,
    signature_header: str,
    body: Body,
    tolerance: Optional[float] = DEFAULT_TOLERANCE,
) -> Event:
    """Verify and decode a signed webhook.

    Args:
        secret: Your webhook signing secret.
        signature_header: The ``X-Fax-Signature`` header value, verbatim.
        body: The raw request body, unmodified.
        tolerance: Maximum accepted age in seconds (default 300). Pass ``0`` or
            ``None`` to skip the replay check.

    Returns:
        The parsed :class:`Event`.

    Raises:
        SignatureVerificationError: if the header is malformed, the timestamp is
            outside the tolerance window, or the signature does not match.
    """
    if not secret:
        raise SignatureVerificationError("empty webhook secret")

    ts, sig = _parse_header(signature_header)

    if tolerance and tolerance > 0:
        try:
            timestamp = int(ts)
        except ValueError as exc:
            raise SignatureVerificationError("malformed timestamp") from exc
        if abs(time.time() - timestamp) > tolerance:
            raise SignatureVerificationError("timestamp outside tolerance")

    raw = _as_bytes(body)
    mac = hmac.new(secret.encode("utf-8"), (ts + ".").encode("utf-8"), hashlib.sha256)
    mac.update(raw)
    if not hmac.compare_digest(mac.hexdigest(), sig):
        raise SignatureVerificationError("signature mismatch")

    return parse_event(raw)


def parse_event(body: Body) -> Event:
    """Decode a callback body without verifying it."""
    raw = _as_bytes(body)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid webhook JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("invalid webhook JSON: expected an object")
    return Event.from_dict(data)
