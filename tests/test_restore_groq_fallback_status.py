from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "restore_groq_fallback_status.py"
spec = importlib.util.spec_from_file_location("restore_groq_fallback_status", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _saved(run_id: str = "123") -> dict:
    return {
        "generated_utc": "old",
        "media_reporting": {"status": "old"},
        "groq_provider_fallback": {
            "run_id": run_id,
            "status": "degraded",
            "failed_games": ["g1"],
            "games": {
                "g1": {
                    "provider": "groq",
                    "provider_result": "failed",
                    "fallback_source": "last_validated_editorial",
                    "requires_chatgpt_refresh": True,
                }
            },
        },
    }


def _current() -> dict:
    return {
        "generated_utc": "new",
        "media_reporting": {"status": "healthy"},
        "injuries": {"status": "healthy"},
        "groq_provider_fallback": {
            "run_id": "older-main-run",
            "status": "healthy",
            "games": {},
        },
    }


def test_restores_only_fallback_section_and_preserves_latest_main_status() -> None:
    restored, changed = module.restore_fallback_status(
        _saved(),
        _current(),
        expected_run_id="123",
    )
    assert changed is True
    assert restored["generated_utc"] == "new"
    assert restored["media_reporting"] == {"status": "healthy"}
    assert restored["injuries"] == {"status": "healthy"}
    fallback = restored["groq_provider_fallback"]
    assert fallback["run_id"] == "123"
    assert fallback["games"]["g1"]["requires_chatgpt_refresh"] is True


def test_no_fallback_section_is_noop() -> None:
    current = _current()
    restored, changed = module.restore_fallback_status(
        {"generated_utc": "old"},
        current,
        expected_run_id="123",
    )
    assert changed is False
    assert restored == current


def test_wrong_run_id_fails_closed() -> None:
    with pytest.raises(ValueError, match="does not match current run"):
        module.restore_fallback_status(
            _saved("wrong"),
            _current(),
            expected_run_id="123",
        )


def test_malformed_game_receipt_fails_closed() -> None:
    saved = _saved()
    saved["groq_provider_fallback"]["games"]["g1"].pop("requires_chatgpt_refresh")
    with pytest.raises(ValueError, match="requires_chatgpt_refresh"):
        module.restore_fallback_status(saved, _current(), expected_run_id="123")


def test_non_failed_entry_cannot_be_smuggled_into_fallback_status() -> None:
    saved = _saved()
    saved["groq_provider_fallback"]["games"]["g1"]["provider_result"] = "success"
    with pytest.raises(ValueError, match="not a failed-provider receipt"):
        module.restore_fallback_status(saved, _current(), expected_run_id="123")
