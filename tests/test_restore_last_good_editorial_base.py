from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "restore_last_good_editorial_base.py"
SPEC = importlib.util.spec_from_file_location("restore_last_good_editorial_base", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


ROSTER = ["2026_02_A_B", "2026_02_C_D"]


def _packet():
    media = {
        "generated_utc": "2026-09-20T00:00:00+00:00",
        "games": {
            "2026_02_A_B": {"headline": "A", "paragraph1": "A", "sources": [{"name": "N", "title": "T", "url": "https://example.com/a"}]},
            "2026_02_C_D": {"headline": "C", "paragraph1": "C", "sources": [{"name": "N", "title": "T", "url": "https://example.com/c"}]},
            "2026_02_THU_X": {"headline": "X"},
        },
    }
    previews = {gid: {"game_id": gid} for gid in [*ROSTER, "2026_02_THU_X"]}
    evidence = {gid: {"game_id": gid} for gid in [*ROSTER, "2026_02_THU_X"]}
    status = {
        "editorial_finalizer": {"status": "healthy", "games": 3, "unique_headlines": 3},
        "copilot_media": {"status": "healthy", "games_applied": 3},
        "media_reporting": {
            "status": "healthy",
            "games": 3,
            "games_with_reporting": 3,
            "games_with_trusted_reporting": 3,
            "games_with_display_reporting": 3,
            "games_with_substantive_reporting": 2,
        },
    }
    return media, previews, evidence, status


def test_launch_grade_requires_full_roster_coverage():
    media, previews, evidence, status = _packet()
    assert MODULE.packet_is_launch_grade(
        roster_ids=ROSTER,
        media=media,
        previews=previews,
        evidence=evidence,
        status=status,
    )

    media["games"].pop("2026_02_C_D")
    assert not MODULE.packet_is_launch_grade(
        roster_ids=ROSTER,
        media=media,
        previews=previews,
        evidence=evidence,
        status=status,
    )


def test_prune_packet_excludes_non_roster_games_and_normalizes_reporting_counts():
    media, previews, evidence, status = _packet()
    pruned_media, pruned_previews, pruned_evidence, snapshot = MODULE.prune_packet(
        roster_ids=ROSTER,
        media=media,
        previews=previews,
        evidence=evidence,
        status=status,
        source_commit="abc123",
    )

    assert list(pruned_media["games"]) == ROSTER
    assert list(pruned_previews) == ROSTER
    assert list(pruned_evidence) == ROSTER
    reporting = snapshot["media_reporting"]
    assert snapshot["games"] == 2
    assert snapshot["source_commit"] == "abc123"
    assert reporting["games_with_trusted_reporting"] == 2
    assert reporting["games_with_display_reporting"] == 2
    assert reporting["last_good_ancestor_reused"] == "abc123"
