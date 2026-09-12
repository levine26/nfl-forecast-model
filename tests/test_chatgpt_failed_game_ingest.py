from __future__ import annotations

from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ingest_chatgpt_failed_games.py"
spec = importlib.util.spec_from_file_location("ingest_chatgpt_failed_games", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def _status() -> dict:
    return {
        "groq_provider_fallback": {
            "run_id": "42",
            "status": "degraded",
            "games": {
                "g1": {
                    "provider_result": "failed",
                    "fallback_source": "last_validated_editorial",
                    "requires_chatgpt_refresh": True,
                },
                "g2": {
                    "provider_result": "success",
                    "requires_chatgpt_refresh": False,
                },
            },
        }
    }


def _manifest(root: Path, game_ids: list[str], generated: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "producer": "chatgpt-consumer-session",
        "research_mode": "live-web-search",
        "forecast_path_identity": "F-ST-01-FROZEN-2026",
        "generated_utc": generated,
        "game_ids": game_ids,
    }))
    for gid in game_ids:
        (root / f"{gid}.json").write_text(json.dumps({"games": {gid: {"headline": gid}}}))


def test_manifest_may_target_only_failed_games_requiring_chatgpt(tmp_path: Path) -> None:
    root = tmp_path / "fallback"
    _manifest(root, ["g1"], "2026-09-12T15:30:00Z")
    targets = module.validate_fallback_manifest(
        root,
        ["g1", "g2"],
        _status(),
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )
    assert targets == ["g1"]


def test_manifest_cannot_overwrite_successful_groq_game(tmp_path: Path) -> None:
    root = tmp_path / "fallback"
    _manifest(root, ["g2"], "2026-09-12T15:30:00Z")
    try:
        module.validate_fallback_manifest(
            root,
            ["g1", "g2"],
            _status(),
            now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
        )
    except ValueError as exc:
        assert "only Groq-failed games" in str(exc)
    else:
        raise AssertionError("successful Groq game must not be replaceable by fallback")


def test_mixed_payload_replaces_only_target_game() -> None:
    base = {
        "games": {
            "g1": {
                "headline": "old failed game",
                "paragraph1": "old paragraph one",
                "paragraph2": "old paragraph two",
                "sources": [{"name": "A", "title": "A", "url": "https://www.nfl.com/news/a"}],
            },
            "g2": {
                "headline": "successful Groq game",
                "paragraph1": "successful Groq paragraph",
                "model_rationale": "Successful game keeps its matchup mechanism and remains untouched by a fallback aimed at the other matchup only.",
                "sources": [{"name": "B", "title": "B", "url": "https://www.espn.com/nfl/story/b"}],
            },
        }
    }
    chatgpt = {
        "g1": {
            "headline": "fresh ChatGPT failed-game replacement",
            "paragraph1": "fresh replacement paragraph",
            "model_rationale": "Fresh failed-game research supplies a new matchup mechanism without changing any numerical LevLine forecast input or output.",
            "sources": [{"name": "C", "title": "C", "url": "https://www.cbssports.com/nfl/c"}],
        }
    }
    mixed = module.build_mixed_raw_payload(
        canonical_game_ids=["g1", "g2"],
        base_artifact=base,
        chatgpt_entries=chatgpt,
    )
    assert mixed["games"]["g1"]["headline"].startswith("fresh ChatGPT")
    assert mixed["games"]["g2"]["headline"] == "successful Groq game"
    assert mixed["games"]["g2"]["paragraph1"] == "successful Groq paragraph"


def test_mark_recovered_clears_refresh_requirement_only_for_target() -> None:
    updated = module.mark_chatgpt_recovered(
        _status(),
        ["g1"],
        now=datetime(2026, 9, 12, 16, 0, tzinfo=timezone.utc),
    )
    section = updated["groq_provider_fallback"]
    assert section["games"]["g1"]["fallback_source"] == "chatgpt"
    assert section["games"]["g1"]["requires_chatgpt_refresh"] is False
    assert section["games"]["g2"]["requires_chatgpt_refresh"] is False
    assert section["status"] == "healthy"
