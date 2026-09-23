"""Asynchronous client for the INeedToSendAFax API."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, Optional

import httpx

from . import _core
from ._core import FileInput
from .errors import IFaxError
from .models import Account, Fax, FaxList, Pricing


class AsyncClient:
    """An asynchronous INeedToSendAFax API client.

    Example:
        >>> import asyncio
        >>> from ineedtosendafax import AsyncClient
        >>>
        >>> async def main():
        ...     async with AsyncClient("ifx_live_...") as client:
        ...         fax = await client.send_fax("15551234567", ["invoice.pdf"])
        ...         print(fax.id)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        base_url: str = _core.DEFAULT_BASE_URL,
        timeout: float = _core.DEFAULT_TIMEOUT,
        max_retries: int = _core.DEFAULT_MAX_RETRIES,
        http_client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        self._api_key = api_key if api_key is not None else _core.api_key_from_env()
        self._base_url = base_url.rstrip("/")
        self._max_retries = max(0, int(max_retries))
        self._owns_client = http_client is None
        self._http = http_client or httpx.AsyncClient(timeout=timeout)
        self._closed = False

    def _headers(self) -> "dict[str, str]":
        headers = {"Accept": "application/json", "User-Agent": _core.USER_AGENT}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _request(
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
                response = await self._http.request(
                    method, url, data=data, files=files, headers=request_headers
                )
            except httpx.TransportError as exc:
                if attempt <= self._max_retries:
                    await asyncio.sleep(_core.retry_delay(attempt))
                    continue
                raise IFaxError(f"request failed: {exc}") from exc

            if response.status_code in _core.RETRY_STATUS and attempt <= self._max_retries:
                await asyncio.sleep(
                    _core.retry_delay(attempt, _core.parse_retry_after(response))
                )
                continue
            return _core.handle_response(response)

    async def send_fax(
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
        """Submit a fax and return it with status ``queued``."""
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
        data = await self._request(
            "POST", "/v1/faxes", data=form, files=multipart, headers=headers
        )
        return Fax.from_dict(data)

    async def get_fax(self, fax_id: str) -> Fax:
        """Return a single fax by id."""
        return Fax.from_dict(await self._request("GET", f"/v1/faxes/{fax_id}"))

    async def list_faxes(self, limit: int = 50) -> FaxList:
        """Return recent faxes and the account balance."""
        path = "/v1/faxes"
        if limit and limit > 0:
            path += f"?limit={int(limit)}"
        return FaxList.from_dict(await self._request("GET", path))

    async def me(self) -> Account:
        """Return the account balance, limits and recent usage."""
        return Account.from_dict(await self._request("GET", "/v1/me"))

    async def pricing(self) -> Pricing:
        """Return the current price and limits."""
        return Pricing.from_dict(await self._request("GET", "/v1/pricing"))

    async def aclose(self) -> None:
        if self._owns_client and not self._closed:
            await self._http.aclose()
        self._closed = True

    async def __aenter__(self) -> "AsyncClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()
