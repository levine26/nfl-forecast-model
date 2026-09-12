from __future__ import annotations

from email.message import Message
import importlib.util
import io
from pathlib import Path
from urllib.error import HTTPError


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run_groq_media_prompt.py"
spec = importlib.util.spec_from_file_location("run_groq_media_prompt", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _http_error(code: int, *, body: str = "", **headers: str) -> HTTPError:
    message = Message()
    for key, value in headers.items():
        message[key.replace("_", "-")] = value
    fp = io.BytesIO(body.encode("utf-8")) if body else None
    return HTTPError("https://api.groq.com", code, "Provider Error", message, fp)


def _http_429(*, body: str = "", **headers: str) -> HTTPError:
    return _http_error(429, body=body, **headers)


def test_compound_mini_is_default_provider():
    assert module.DEFAULT_MODEL == "groq/compound-mini"


def test_compound_mini_payload_uses_documented_minimal_surface():
    payload = module._build_payload("research this game", model=module.DEFAULT_MODEL)
    assert payload["model"] == "groq/compound-mini"
    assert payload["messages"] == [{"role": "user", "content": "research this game"}]
    assert payload["search_settings"]["include_domains"]
    assert set(payload) == {"model", "messages", "search_settings"}
    for optional in (
        "citation_options",
        "compound_custom",
        "max_completion_tokens",
        "reasoning_format",
        "response_format",
        "service_tier",
        "temperature",
    ):
        assert optional not in payload


def test_rate_limit_delay_honors_retry_after_seconds():
    exc = _http_429(retry_after="17", x_ratelimit_remaining_tokens="0")
    assert module._rate_limit_delay(exc, 1) == 18.0


def test_rate_limit_delay_fails_closed_on_long_quota_window():
    exc = _http_429(retry_after="600", x_ratelimit_remaining_requests="0")
    assert module._rate_limit_delay(exc, 1) is None


def test_rate_limit_delay_uses_minute_window_fallback_without_header():
    exc = _http_429()
    assert module._rate_limit_delay(exc, 1) == 20.0
    assert module._rate_limit_delay(exc, 2) == 40.0
    assert module._rate_limit_delay(exc, 3) == 75.0


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


def test_safe_rate_limit_reason_classifies_without_echoing_body():
    exc = _http_429(
        body='{"error":{"message":"Rate limit reached for model openai/gpt-oss-120b: tokens per minute exceeded; prompt secret-do-not-log"}}'
    )
    reason = module._safe_rate_limit_reason(exc)
    assert "tpm" in reason
    assert "model=openai/gpt-oss-120b" in reason
    assert "secret-do-not-log" not in reason


def test_safe_bad_request_reason_exposes_only_allowlisted_diagnostics():
    exc = _http_error(
        400,
        body='{"error":{"message":"Unsupported parameter response_format; prompt secret-do-not-log",'
        '"type":"invalid_request_error","code":"unsupported_parameter","param":"response_format.type"}}',
    )
    reason = module._safe_bad_request_reason(exc)
    assert "param=response_format" in reason
    assert "type=invalid_request_error" in reason
    assert "code=unsupported_parameter" in reason
    assert "response_format" in reason
    assert "secret-do-not-log" not in reason


def test_safe_bad_request_reason_does_not_echo_unknown_param_or_message():
    exc = _http_error(
        400,
        body='{"error":{"message":"bad secret-token-123", "param":"private_prompt", "type":"weird type"}}',
    )
    reason = module._safe_bad_request_reason(exc)
    assert reason == "bad_request"
    assert "private_prompt" not in reason
    assert "secret-token-123" not in reason
