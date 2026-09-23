"""Official Python client for the INeedToSendAFax API.

Send faxes, track delivery, and verify webhook callbacks.

    from ineedtosendafax import Client

    client = Client("ifx_live_...")  # or set IFAX_API_KEY
    fax = client.send_fax("15551234567", ["invoice.pdf"])
    print(fax.id, fax.status)

An async client is available as :class:`AsyncClient`. See
https://api.ineedtosendafax.com/docs for the API reference.
"""

from __future__ import annotations

from ._core import VERSION as __version__
from .aio import AsyncClient
from .client import Client
from .errors import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    IFaxError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ServerError,
    SignatureVerificationError,
    ValidationError,
)
from .models import Account, Event, Fax, FaxList, Pricing
from .webhook import DEFAULT_TOLERANCE, parse_event, verify_webhook

__all__ = [
    "__version__",
    "Client",
    "AsyncClient",
    "IFaxError",
    "APIError",
    "AuthenticationError",
    "AuthorizationError",
    "InsufficientCreditsError",
    "NotFoundError",
    "RateLimitError",
    "ValidationError",
    "ServerError",
    "SignatureVerificationError",
    "Fax",
    "FaxList",
    "Account",
    "Pricing",
    "Event",
    "verify_webhook",
    "parse_event",
    "DEFAULT_TOLERANCE",
]
