"""Synchronous client for the INeedToSendAFax API."""

from __future__ import annotations

import time
from typing import Any, Iterable, Optional

import httpx

from . import _core
from ._core import FileInput
from .errors import IFaxError
from .models import Account, Fax, FaxList, Pricing


class Client:
    """A synchronous INeedToSendAFax API client.

    Example:
        >>> from ineedtosendafax import Client
        >>> client = Client("ifx_live_...")
        >>> fax = client.send_fax("15551234567", ["invoice.pdf"])
        >>> fax.status
        'queued'

    The client is thread-safe for independent requests. Use it as a context
    manager, or call :meth:`close`, to release the connection pool.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = _core.DEFAULT_BASE_URL,
        timeout: float = _core.DEFAULT_TIMEOUT,
        max_retries: int = _core.DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.Client] = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else _core.api_key_from_env()
        self._base_url = base_url.rstrip("/")
        self._max_retries = max(0, int(max_retries))
        self._owns_client = http_client is None
        self._http = http_client or httpx.Client(timeout=timeout)
        self._closed = False

    # -- transport -------------------------------------------------------

    def _headers(self) -> "dict[str, str]":
        headers = {"Accept": "application/json", "User-Agent": _core.USER_AGENT}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _request(
        self,
        method: str,
        path: str,
        *,
        data: Optional[dict] = None,
        files: Optional[list] = None,
        headers: Optional[dict] = None,
    ) -> "dict[str, Any]":
        if self._closed:
            raise IFaxError("client is closed")
        url = self._base_url + path
        request_headers = self._headers()
        if headers:
            request_headers.update(headers)

        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._http.request(
                    method, url, data=data, files=files, headers=request_headers
                )
            except httpx.TransportError as exc:
                if attempt <= self._max_retries:
                    time.sleep(_core.retry_delay(attempt))
                    continue
                raise IFaxError(f"request failed: {exc}") from exc

            if response.status_code in _core.RETRY_STATUS and attempt <= self._max_retries:
                time.sleep(_core.retry_delay(attempt, _core.parse_retry_after(response)))
                continue
            return _core.handle_response(response)

    # -- endpoints -------------------------------------------------------

    def send_fax(
        self,
        to: str,
        files: Iterable[FileInput],
        *,
        callback_url: Optional[str] = None,
        cover: bool = False,
        cover_text: Optional[str] = None,
        recipient_name: Optional[str] = None,
        recipient_company: Optional[str] = None,
        sender_name: Optional[str] = None,
        sender_company: Optional[str] = None,
        sender_phone: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Fax:
        """Submit a fax and return it with status ``queued``.

        ``files`` accepts paths, bytes, ``(name, data)`` tuples, or file
        objects, up to 10 combined documents. An idempotency key is generated
        when not supplied, so retries never deliver twice.
        """
        resolved = _core.resolve_files(files)
        form = _core.build_form(
            to,
            callback_url,
            cover,
            cover_text,
            recipient_name,
            recipient_company,
            sender_name,
            sender_company,
            sender_phone,
        )
        multipart = [("file", (name, blob, ctype)) for name, blob, ctype in resolved]
        headers = {"Idempotency-Key": idempotency_key or _core.new_idempotency_key()}
        data = self._request("POST", "/v1/faxes", data=form, files=multipart, headers=headers)
        return Fax.from_dict(data)

    def get_fax(self, fax_id: str) -> Fax:
        """Return a single fax by id."""
        return Fax.from_dict(self._request("GET", f"/v1/faxes/{fax_id}"))

    def list_faxes(self, limit: int = 50) -> FaxList:
        """Return recent faxes and the account balance."""
        path = "/v1/faxes"
        if limit and limit > 0:
            path += f"?limit={int(limit)}"
        return FaxList.from_dict(self._request("GET", path))

    def me(self) -> Account:
        """Return the account balance, limits and recent usage."""
        return Account.from_dict(self._request("GET", "/v1/me"))

    def pricing(self) -> Pricing:
        """Return the current price and limits."""
        return Pricing.from_dict(self._request("GET", "/v1/pricing"))

    # -- lifecycle -------------------------------------------------------

    def close(self) -> None:
        if self._owns_client and not self._closed:
            self._http.close()
        self._closed = True

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
