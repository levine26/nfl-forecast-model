from __future__ import annotations

import json

import pytest

from scripts import run_groq_read_writer as writer


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "", headers: dict | None = None):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


def test_payload_keeps_browser_research_and_deterministic_schema_boundary():
    payload = writer.build_payload("write it")
    assert payload["model"] == "openai/gpt-oss-120b"
    assert payload["messages"] == [{"role": "user", "content": "write it"}]
    assert payload["tools"] == [{"type": "browser_search"}]
    assert payload["tool_choice"] == "required"
    assert payload["citation_options"] == "disabled"
    assert "response_format" not in payload


def test_isolate_final_json_drops_browser_search_preamble():
    raw = 'research snippet {not the answer}\nFinal answer:\n{\n  "games": {"G": {"headline": "x"}}\n}\ntrailing note'
    isolated = writer.isolate_final_json(raw)
    assert json.loads(isolated) == {"games": {"G": {"headline": "x"}}}


def test_generate_returns_model_content(monkeypatch):
    seen = {}

    def fake_post(url, *, headers, json, timeout):
        seen.update(url=url, headers=headers, payload=json, timeout=timeout)
        return FakeResponse(200, {"choices": [{"message": {"content": '{"games":{}}'}}]})

    monkeypatch.setattr(writer.requests, "post", fake_post)
    result = writer.generate("prompt", api_key="secret", attempts=1)
    assert result == '{"games":{}}'
    assert seen["url"] == writer.API_URL
    assert seen["headers"]["Authorization"] == "Bearer secret"
    assert seen["payload"]["tools"] == [{"type": "browser_search"}]


def test_generate_retries_rate_limit(monkeypatch):
    responses = [
        FakeResponse(429, text="rate limited", headers={"Retry-After": "0"}),
        FakeResponse(200, {"choices": [{"message": {"content": '{"games":{"ok":{}}}'}}]}),
    ]
    sleeps = []

    def fake_post(*args, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(writer.requests, "post", fake_post)
    monkeypatch.setattr(writer.time, "sleep", sleeps.append)
    result = writer.generate("prompt", api_key="secret", attempts=2)
    assert json.loads(result)["games"] == {"ok": {}}
    assert sleeps == [0.0]


def test_generate_fails_closed_without_key():
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        writer.generate("prompt", api_key="")


def test_generate_fails_closed_on_bad_success_payload(monkeypatch):
    monkeypatch.setattr(
        writer.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(200, {"choices": []}),
    )
    with pytest.raises(RuntimeError, match="invalid completion payload"):
        writer.generate("prompt", api_key="secret", attempts=1)
