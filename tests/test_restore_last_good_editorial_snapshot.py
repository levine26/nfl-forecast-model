from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "restore_last_good_editorial_snapshot.py"
SPEC = importlib.util.spec_from_file_location("restore_last_good_editorial_snapshot", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _status(games: int) -> dict:
    return {
        "copilot_media": {"status": "healthy", "games_applied": games, "games_expected": games},
        "editorial_finalizer": {"status": "healthy", "games": games, "unique_headlines": games},
        "media_reporting": {
            "status": "healthy",
            "games": games,
            "games_with_display_reporting": games,
            "games_with_reporting": games,
            "games_with_substantive_reporting": games,
            "games_with_trusted_reporting": games,
        },
        "groq_provider_fallback": {
            "status": "degraded",
            "games": {
                "g2": {
                    "provider_result": "failed",
                    "requires_chatgpt_refresh": True,
                    "fallback_source": "missing",
                }
            },
        },
    }


def test_snapshot_requires_full_roster_coverage_and_launch_health() -> None:
    roster = {"g1", "g2"}
    previews = {"g1": {}, "g2": {}}
    media = {"games": {"g1": {}, "g2": {}}}
    evidence = {"g1": {}, "g2": {}}
    status = _status(2)

    assert MODULE.snapshot_covers(
        roster_ids=roster,
        previews=previews,
        media=media,
        evidence=evidence,
        status=status,
    )

    assert not MODULE.snapshot_covers(
        roster_ids=roster,
        previews={"g1": {}},
        media=media,
        evidence=evidence,
        status=status,
    )


def test_trim_snapshot_preserves_current_failure_targets() -> None:
    roster = ["g1", "g2"]
    historical_status = _status(3)
    historical_status["groq_provider_fallback"] = {
        "status": "healthy",
        "games": {},
    }
    current_status = _status(2)

    previews, media, evidence, status = MODULE.trim_snapshot(
        roster_ids=roster,
        previews={"g0": {}, "g1": {"p": 1}, "g2": {"p": 2}},
        media={"generated_utc": "old", "games": {"g0": {}, "g1": {"m": 1}, "g2": {"m": 2}}},
        evidence={"g0": {}, "g1": {"e": 1}, "g2": {"e": 2}},
        historical_status=historical_status,
        current_status=current_status,
        source_commit="abc123",
    )

    assert set(previews) == {"g1", "g2"}
    assert set(media["games"]) == {"g1", "g2"}
    assert set(evidence) == {"g1", "g2"}
    assert status["copilot_media"]["games_applied"] == 2
    assert status["editorial_finalizer"]["games"] == 2
    assert status["media_reporting"]["games_with_trusted_reporting"] == 2
    assert status["media_reporting"]["last_good_snapshot_reused"] is True
    assert status["media_reporting"]["last_good_snapshot_source_commit"] == "abc123"
    assert status["groq_provider_fallback"]["games"]["g2"]["requires_chatgpt_refresh"] is True
