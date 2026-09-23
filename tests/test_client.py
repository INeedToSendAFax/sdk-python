import io
import json

import httpx
import pytest

from ineedtosendafax import (
    Client,
    InsufficientCreditsError,
    NotFoundError,
    RateLimitError,
)


def make_client(handler, **kwargs):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return Client("ifx_live_test", base_url="https://api.test", http_client=http, **kwargs)


def test_send_fax_builds_request_and_parses_response():
    seen = {}

    def handler(request):
        seen["auth"] = request.headers.get("authorization")
        seen["idem"] = request.headers.get("idempotency-key")
        seen["ctype"] = request.headers.get("content-type", "")
        seen["body"] = request.content
        return httpx.Response(
            202,
            json={"id": "abc", "status": "queued", "to": "15551234567",
                  "price_cents": 149, "pages": 1},
        )

    client = make_client(handler)
    fax = client.send_fax(
        "15551234567", [("invoice.pdf", b"%PDF-1.4 fake")], cover=True, cover_text="Hi"
    )

    assert fax.id == "abc"
    assert fax.status == "queued"
    assert fax.price_cents == 149
    assert seen["auth"] == "Bearer ifx_live_test"
    assert seen["idem"]
    assert seen["ctype"].startswith("multipart/form-data")
    assert b"15551234567" in seen["body"]
    assert b"invoice.pdf" in seen["body"]


def test_send_fax_accepts_various_file_inputs(tmp_path):
    path = tmp_path / "doc.pdf"
    path.write_bytes(b"%PDF-1.4 from-disk")

    def handler(request):
        return httpx.Response(202, json={"id": "x", "status": "queued"})

    client = make_client(handler)
    for files in (
        [str(path)],
        [path],
        [b"raw-bytes"],
        [("named.pdf", b"bytes")],
        [io.BytesIO(b"stream"),],
        [("f.pdf", io.BytesIO(b"stream"))],
    ):
        assert client.send_fax("1555", files).id == "x"


def test_send_fax_requires_files():
    client = make_client(lambda request: httpx.Response(202, json={}))
    with pytest.raises(ValueError):
        client.send_fax("1555", [])


def test_error_mapping():
    def handler(request):
        return httpx.Response(
            402,
            json={"error": {"code": "insufficient_credits", "message": "Not enough credit."}},
        )

    client = make_client(handler)
    with pytest.raises(InsufficientCreditsError) as exc:
        client.send_fax("1555", [b"x"])
    assert exc.value.status_code == 402
    assert exc.value.code == "insufficient_credits"
    assert "Not enough credit." in str(exc.value)


def test_not_found():
    def handler(request):
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "No."}})

    client = make_client(handler)
    with pytest.raises(NotFoundError):
        client.get_fax("missing")


def test_retry_on_server_error():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(500, json={"error": {"code": "server_error", "message": "boom"}})
        return httpx.Response(200, json={"id": "ok", "status": "queued"})

    client = make_client(handler, max_retries=1)
    fax = client.send_fax("1555", [b"x"])
    assert calls["n"] == 2
    assert fax.id == "ok"


def test_rate_limited_no_retry_config():
    def handler(request):
        return httpx.Response(
            429,
            headers={"Retry-After": "0"},
            json={"error": {"code": "rate_limited", "message": "slow down"}},
        )

    client = make_client(handler, max_retries=0)
    with pytest.raises(RateLimitError) as exc:
        client.send_fax("1555", [b"x"])
    assert exc.value.retry_after == 0.0


def test_list_me_pricing():
    def handler(request):
        path = request.url.path
        if path.endswith("/v1/faxes"):
            assert request.url.params.get("limit") == "5"
            return httpx.Response(200, json={"data": [{"id": "a", "status": "sent"}], "balance_cents": 351})
        if path.endswith("/v1/me"):
            return httpx.Response(200, json={"key_prefix": "ifx_live_ab", "balance_cents": 351, "max_pages": 25})
        if path.endswith("/v1/pricing"):
            return httpx.Response(200, json={"price_cents": 149, "currency": "usd", "countries": ["US", "CA"]})
        return httpx.Response(404, json={"error": {"code": "not_found", "message": "no"}})

    client = make_client(handler)
    lst = client.list_faxes(5)
    assert lst.balance_cents == 351 and lst.data[0].status == "sent"
    assert client.me().max_pages == 25
    assert client.pricing().price_cents == 149


def test_iso_timestamp_parsing():
    def handler(request):
        return httpx.Response(
            200,
            content=json.dumps({
                "id": "a", "status": "sent",
                "created_at": "2026-09-23T06:17:37.120109Z",
                "completed_at": "2026-09-23T06:18:37Z",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )

    client = make_client(handler)
    fax = client.get_fax("a")
    assert fax.created_at is not None and fax.created_at.year == 2026
    assert fax.completed_at is not None
