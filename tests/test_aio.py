import asyncio

import httpx

from ineedtosendafax import AsyncClient, NotFoundError


def test_async_flow():
    async def main():
        def handler(request):
            path = request.url.path
            if path.endswith("/v1/faxes"):
                return httpx.Response(202, json={"id": "a1", "status": "queued"})
            if path.endswith("/v1/me"):
                return httpx.Response(200, json={"balance_cents": 351, "max_pages": 25})
            if path.endswith("/v1/pricing"):
                return httpx.Response(200, json={"price_cents": 149})
            return httpx.Response(404, json={"error": {"code": "not_found", "message": "no"}})

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        async with AsyncClient(
            "ifx_live_test", base_url="https://api.test", http_client=http
        ) as client:
            fax = await client.send_fax("1555", [b"x"])
            assert fax.id == "a1"

            me = await client.me()
            assert me.balance_cents == 351 and me.max_pages == 25

            pricing = await client.pricing()
            assert pricing.price_cents == 149

            try:
                await client.get_fax("missing")
                raise AssertionError("expected NotFoundError")
            except NotFoundError:
                pass

    asyncio.run(main())


def test_async_retry():
    async def main():
        calls = {"n": 0}

        def handler(request):
            calls["n"] += 1
            if calls["n"] == 1:
                return httpx.Response(500, json={"error": {"code": "server_error", "message": "x"}})
            return httpx.Response(200, json={"id": "ok", "status": "queued"})

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AsyncClient(
            "k", base_url="https://api.test", http_client=http, max_retries=1
        )
        fax = await client.send_fax("1555", [b"x"])
        await client.aclose()
        assert calls["n"] == 2 and fax.id == "ok"

    asyncio.run(main())
