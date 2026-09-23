import hashlib
import hmac
import time

import pytest

from ineedtosendafax import (
    SignatureVerificationError,
    parse_event,
    verify_webhook,
)


def sign(secret, ts, body):
    raw = body if isinstance(body, bytes) else body.encode()
    mac = hmac.new(secret.encode(), (ts + ".").encode(), hashlib.sha256)
    mac.update(raw)
    return mac.hexdigest()


def test_verify_valid():
    body = b'{"id":"abc","status":"sent","pages":2}'
    ts = str(int(time.time()))
    header = f"t={ts},v1={sign('whsec', ts, body)}"
    event = verify_webhook("whsec", header, body)
    assert event.id == "abc" and event.status == "sent" and event.pages == 2


def test_wrong_secret():
    body = b'{"id":"abc"}'
    ts = str(int(time.time()))
    with pytest.raises(SignatureVerificationError):
        verify_webhook("wrong", f"t={ts},v1={sign('whsec', ts, body)}", body)


def test_stale_timestamp():
    body = b'{"id":"abc"}'
    ts = "1700000000"
    header = f"t={ts},v1={sign('whsec', ts, body)}"
    with pytest.raises(SignatureVerificationError):
        verify_webhook("whsec", header, body, tolerance=60)


def test_tolerance_disabled():
    body = b'{"id":"abc"}'
    ts = "1700000000"
    header = f"t={ts},v1={sign('whsec', ts, body)}"
    event = verify_webhook("whsec", header, body, tolerance=0)
    assert event.id == "abc"


def test_malformed_header():
    with pytest.raises(SignatureVerificationError):
        verify_webhook("whsec", "garbage", b"{}")


def test_tampered_body():
    ts = str(int(time.time()))
    signed = b'{"id":"abc"}'
    header = f"t={ts},v1={sign('whsec', ts, signed)}"
    with pytest.raises(SignatureVerificationError):
        verify_webhook("whsec", header, b'{"id":"evil"}')


def test_parse_event():
    event = parse_event(b'{"id":"x","status":"failed","error":"no answer","completed_at":"2026-09-23T06:17:37Z"}')
    assert event.status == "failed"
    assert event.error == "no answer"
    assert event.completed_at is not None
