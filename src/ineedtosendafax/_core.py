"""Shared internals for the sync and async clients."""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import httpx

from .errors import APIError, IFaxError, error_from_response

DEFAULT_BASE_URL = "https://api.ineedtosendafax.com"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
MAX_FILE_BYTES = 32 << 20
MAX_FILES = 10
RETRY_STATUS = {429, 500, 502, 503, 504}

VERSION = "1.0.0"
USER_AGENT = "ineedtosendafax-python/" + VERSION

# A file can be a path, raw bytes, a (name, data) tuple, or a file object.
FileInput = Union[str, "os.PathLike[str]", bytes, bytearray, Tuple[str, Any], Any]
ResolvedFile = Tuple[str, bytes, str]


def api_key_from_env() -> Optional[str]:
    return os.environ.get("IFAX_API_KEY")


def new_idempotency_key() -> str:
    return uuid.uuid4().hex


def _coerce_bytes(data: Any) -> bytes:
    if hasattr(data, "read"):
        data = data.read()
    if isinstance(data, str):
        data = data.encode("utf-8")
    if isinstance(data, bytearray):
        data = bytes(data)
    if not isinstance(data, bytes):
        raise TypeError(f"unsupported file data: {type(data)!r}")
    if len(data) > MAX_FILE_BYTES:
        raise ValueError(f"file exceeds {MAX_FILE_BYTES} bytes")
    return data


def _guess_content_type(name: str) -> str:
    lower = name.lower()
    if lower.endswith(".pdf"):
        return "application/pdf"
    if lower.endswith((".doc", ".docx")):
        return "application/msword"
    if lower.endswith((".png", ".jpg", ".jpeg", ".tif", ".tiff")):
        return "image/" + ("tiff" if lower.endswith((".tif", ".tiff")) else lower.rsplit(".", 1)[1])
    return "application/octet-stream"


def _resolve_one(f: FileInput) -> ResolvedFile:
    if isinstance(f, tuple):
        name, data = f
        name = Path(str(name)).name
        return name, _coerce_bytes(data), _guess_content_type(name)
    if isinstance(f, (str, os.PathLike)):
        path = Path(f)
        return path.name, _coerce_bytes(path.read_bytes()), _guess_content_type(path.name)
    if isinstance(f, (bytes, bytearray)):
        return "upload", _coerce_bytes(f), "application/octet-stream"
    if hasattr(f, "read"):
        name = getattr(f, "name", None)
        name = Path(name).name if name else "upload"
        return name, _coerce_bytes(f), _guess_content_type(name)
    raise TypeError(f"unsupported file input: {type(f)!r}")


def resolve_files(files: Iterable[FileInput]) -> List[ResolvedFile]:
    resolved = [_resolve_one(f) for f in files]
    if not resolved:
        raise ValueError("at least one file is required")
    if len(resolved) > MAX_FILES:
        raise ValueError(f"at most {MAX_FILES} files, got {len(resolved)}")
    return resolved


def build_form(
    to: str,
    callback_url: Optional[str] = None,
    cover: bool = False,
    cover_text: Optional[str] = None,
    recipient_name: Optional[str] = None,
    recipient_company: Optional[str] = None,
    sender_name: Optional[str] = None,
    sender_company: Optional[str] = None,
    sender_phone: Optional[str] = None,
) -> Dict[str, str]:
    if not to or not to.strip():
        raise ValueError("to is required")
    form: Dict[str, str] = {"to": to}
    optional = {
        "callback_url": callback_url,
        "cover_text": cover_text,
        "recipient_name": recipient_name,
        "recipient_company": recipient_company,
        "sender_name": sender_name,
        "sender_company": sender_company,
        "sender_phone": sender_phone,
    }
    for key, value in optional.items():
        if value:
            form[key] = value
    if cover:
        form["cover"] = "1"
    return form


def retry_delay(attempt: int, retry_after: Optional[float] = None) -> float:
    if retry_after and retry_after > 0:
        return float(retry_after)
    return min(0.5 * (2 ** (attempt - 1)), 8.0)


def parse_retry_after(response: httpx.Response) -> Optional[float]:
    raw = response.headers.get("Retry-After")
    if not raw:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def handle_response(response: httpx.Response) -> Dict[str, Any]:
    if response.status_code >= 400:
        code: Optional[str] = None
        message: Optional[str] = None
        try:
            payload = response.json()
            err = payload.get("error") if isinstance(payload, dict) else None
            if isinstance(err, dict):
                code = err.get("code")
                message = err.get("message")
        except Exception:
            pass
        if not message:
            message = response.text or f"HTTP {response.status_code}"
        raise error_from_response(
            response.status_code, code, message, parse_retry_after(response)
        )
    if not response.content:
        return {}
    try:
        data = response.json()
    except Exception as exc:
        raise IFaxError(f"invalid JSON response: {exc}") from exc
    if not isinstance(data, dict):
        raise IFaxError("invalid JSON response: expected an object")
    return data
