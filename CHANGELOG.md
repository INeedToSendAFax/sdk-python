# Changelog

## 1.0.0

Initial release.

- `Client` and `AsyncClient` with `send_fax`, `get_fax`, `list_faxes`, `me`, `pricing`
- Dataclass models (`Fax`, `FaxList`, `Account`, `Pricing`, `Event`)
- Typed exceptions (`AuthenticationError`, `InsufficientCreditsError`, `NotFoundError`, `RateLimitError`, `ValidationError`, `ServerError`)
- Automatic idempotency keys and retries with backoff
- `verify_webhook` and `parse_event` for signed callbacks
