from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from select_prop_market_horizons import select_horizons


def _row(minutes, stamp, line=60.5):
    return {
        "snapshot_id": f"s{stamp}",
        "source_workflow_run": "1",
        "source_head_sha": "a" * 40,
        "source_trigger_head_sha": "b" * 40,
        "source_market_provider": "the_odds_api",
        "source_market_credential_mode": "configured",
        "source_provenance_sha256": "c" * 64,
        "captured_at_utc": stamp,
        "kickoff_utc": "2026-09-20T20:00:00+00:00",
        "minutes_to_kickoff": float(minutes),
        "game_id": "g",
        "player_id": "p",
        "prop_type": "receiving_yards",
        "market_artifact_sha256": f"h{stamp}",
        "market_artifact": {
            "consensus_line": line,
            "consensus_no_vig_p_over": 0.51,
            "consensus_no_vig_p_under": 0.49,
            "sportsbook_count": 3,
            "sportsbooks": ["a","b","c"],
            "line_range": 1.0,
            "line_stddev": 0.4,
        },
        "research_only": True,
        "production_authorized": False,
    }


def test_selects_closest_capture_inside_frozen_window():
    rows=[
        _row(1550,"2026-09-19T18:10:00+00:00",61.5),
        _row(1460,"2026-09-19T19:40:00+00:00",62.5),
        _row(1300,"2026-09-19T22:20:00+00:00",63.5),
    ]
    selected=select_horizons(rows)
    t24=[row for row in selected if row["horizon"]=="T24H"]
    assert len(t24)==1
    assert t24[0]["actual_minutes_to_kickoff"]==1460
    assert t24[0]["consensus_line"]==62.5


def test_out_of_window_capture_does_not_fill_horizon():
    selected=select_horizons([_row(200,"2026-09-20T16:40:00+00:00")])
    names={row["horizon"] for row in selected}
    assert "EARLIEST_OBSERVED" in names
    assert "T90M" not in names
    assert "T30M" not in names


def test_near_close_requires_ten_minutes_or_less():
    rows=[
        _row(11,"2026-09-20T19:49:00+00:00",60.5),
        _row(7,"2026-09-20T19:53:00+00:00",61.5),
        _row(2,"2026-09-20T19:58:00+00:00",62.5),
    ]
    selected=select_horizons(rows)
    close=[row for row in selected if row["horizon"]=="NEAR_CLOSE_OBSERVED"]
    assert len(close)==1
    assert close[0]["actual_minutes_to_kickoff"]==2
    assert close[0]["consensus_line"]==62.5


def test_earliest_observed_is_not_labeled_open():
    selected=select_horizons([
        _row(3000,"2026-09-18T18:00:00+00:00"),
        _row(2900,"2026-09-18T19:40:00+00:00"),
    ])
    names={row["horizon"] for row in selected}
    assert "EARLIEST_OBSERVED" in names
    assert "OPEN" not in names


def test_legacy_pre_provenance_rows_are_preserved_but_not_selected():
    legacy=_row(1460,"2026-09-19T19:40:00+00:00",62.5)
    for key in (
        "source_trigger_head_sha",
        "source_market_provider",
        "source_market_credential_mode",
        "source_provenance_sha256",
    ):
        legacy.pop(key)
    assert select_horizons([legacy]) == []
