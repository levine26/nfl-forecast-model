from __future__ import annotations

from email.message import Message
import importlib.util
from pathlib import Path
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_groq_media_prompt.py"
spec = importlib.util.spec_from_file_location("run_groq_media_prompt", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _http_429(**headers: str) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key.replace("_", "-")] = value
    return HTTPError("https://api.groq.com", 429, "Too Many Requests", message, None)


def test_rate_limit_delay_honors_retry_after_seconds():
    exc = _http_429(retry_after="17", x_ratelimit_remaining_tokens="0")
    assert module._rate_limit_delay(exc, 1) == 18.0


def test_rate_limit_delay_fails_closed_on_long_quota_window():
    exc = _http_429(retry_after="600", x_ratelimit_remaining_requests="0")
    assert module._rate_limit_delay(exc, 1) is None


def test_rate_limit_delay_uses_conservative_fallback_without_header():
    exc = _http_429()
    assert module._rate_limit_delay(exc, 1) == 15.0
    assert module._rate_limit_delay(exc, 2) == 30.0
    assert module._rate_limit_delay(exc, 3) == 60.0


def test_safe_rate_limit_headers_exposes_only_allowlisted_fields():
    exc = _http_429(
        retry_after="9",
        x_ratelimit_remaining_tokens="123",
        authorization="secret-value",
    )
    headers = module._safe_rate_limit_headers(exc)
    assert headers["retry-after"] == "9"
    assert headers["x-ratelimit-remaining-tokens"] == "123"
    assert "authorization" not in headers
