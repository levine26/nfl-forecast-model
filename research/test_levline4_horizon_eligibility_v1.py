from __future__ import annotations

import pandas as pd

from research.levline4_horizon_eligibility_v1 import (
    enforce_strict_cutoffs,
    horizon_completeness_audit,
)


def _row(game: str, horizon: str, timing: float, candidate: str = "L4-MKT-H-V1") -> dict:
    return {
        "game_id": game,
        "horizon": horizon,
        "candidate_id": candidate,
        "market_timing_error_minutes": timing,
    }


def test_positive_timing_error_is_ineligible_for_nominal_horizon() -> None:
    frame = pd.DataFrame(
        [
            _row("g1", "T-45m", -5.0),
            _row("g2", "T-45m", 0.0),
            _row("g3", "T-45m", 0.01),
            _row("g4", "T-45m", -8.0),
        ]
    )
    result = enforce_strict_cutoffs(frame)
    assert set(result.frame["game_id"]) == {"g1", "g2"}
    assert result.audit["excluded_post_cutoff_rows"] == 1
    assert result.audit["excluded_too_early_rows"] == 1
    assert result.audit["maximum_timing_error_minutes"] == 0.0


def test_missing_timing_provenance_fails_closed() -> None:
    frame = pd.DataFrame([{"game_id": "g1", "horizon": "T-45m"}])
    result = enforce_strict_cutoffs(frame)
    assert result.frame.empty
    assert result.audit["excluded_missing_timing_rows"] == 1


def test_completeness_audit_collapses_candidate_duplicates() -> None:
    rows = []
    for candidate in ("L4-MKT-H-V1", "L4-FST-H-V1"):
        for horizon in ("T-120m", "T-60m", "T-45m", "T-30m"):
            rows.append(_row("complete", horizon, -1.0, candidate))
    for horizon in ("T-120m", "T-60m", "T-45m"):
        rows.append(_row("partial", horizon, -1.0))

    audit = horizon_completeness_audit(pd.DataFrame(rows))
    assert audit["games_with_any_eligible_horizon"] == 2
    assert audit["games_with_all_four_eligible_horizons"] == 1
    assert audit["presence_patterns"] == {"1110": 1, "1111": 1}
    assert audit["horizon_presence_rate"]["T-30m"] == 0.5
