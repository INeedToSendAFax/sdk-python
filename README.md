# INeedToSendAFax Python SDK

Official Python client for the [INeedToSendAFax API](https://api.ineedtosendafax.com/docs). Send faxes, track delivery, and verify webhook callbacks.

- Synchronous `Client` and `AsyncClient`
- Typed models and exceptions
- Automatic idempotency keys and retries
- Constant-time webhook signature verification

## Install

```bash
pip install ineedtosendafax
```

## Quick start

Grab an API key from [api.ineedtosendafax.com](https://api.ineedtosendafax.com/) and set it as `IFAX_API_KEY`, or pass it to the client.

```python
from ineedtosendafax import Client

client = Client()  # reads IFAX_API_KEY

fax = client.send_fax("15551234567", ["invoice.pdf"])
print(fax.id, fax.status)  # -> queued
```

### Async

```python
import asyncio
from ineedtosendafax import AsyncClient

async def main():
    async with AsyncClient("ifx_live_...") as client:
        fax = await client.send_fax("15551234567", ["invoice.pdf"])
        print(fax.id)

asyncio.run(main())
```

## Sending a fax

`send_fax` accepts PDF, Word (DOC/DOCX), PNG/JPEG, PostScript, and TIFF, up to 10 combined files and 32 MB each. Files can be paths, bytes, `(name, data)` tuples, or file objects.

```python
fax = client.send_fax(
    "15551234567",
    ["report.pdf", ("appendix.pdf", open("appendix.pdf", "rb"))],
    callback_url="https://example.com/fax-webhook",
    cover=True,
    cover_text="Confidential",
    sender_name="Acme Billing",
    recipient_name="Dr. Smith",
)
```

## Tracking status

```python
fax = client.get_fax("b1a2c3d4-...")
# fax.status is "queued", "sending", "sent", or "failed".

listing = client.list_faxes(limit=50)   # listing.data, listing.balance_cents
account = client.me()                   # account.balance_cents, account.max_pages, ...
price = client.pricing()                # price.price_cents, ...
```

## Verifying webhooks

When you set `callback_url`, we POST the final status with an `X-Fax-Signature` header. Verify it against the raw request body with your webhook signing secret.

```python
from ineedtosendafax import verify_webhook, SignatureVerificationError

def handle(request):
    try:
        event = verify_webhook(
            secret,
            request.headers["X-Fax-Signature"],
            request.get_data(),  # raw, unmodified bytes
        )
    except SignatureVerificationError:
        return "bad signature", 401
    print(event.id, event.status)
```

`verify_webhook` uses a 5 minute replay window by default and a constant-time comparison. Pass `tolerance=0` to disable the timeout check.

## Retries and idempotency

The client retries `429` and `5xx` responses and network errors with backoff, honoring `Retry-After`. `send_fax` always sends an `Idempotency-Key` (generated when you do not provide one), so a retried send never delivers a fax twice.

```python
client = Client("ifx_live_...", timeout=90, max_retries=3)
```

## Errors

All non-2xx responses raise a subclass of `APIError`:

```python
from ineedtosendafax import (
    AuthenticationError,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    ServerError,
)
```

Each carries `.status_code`, `.code`, `.message`, and `.retry_after`.

## License

MIT
