from __future__ import annotations

import pandas as pd
import pytest

from research.levline4_market_devig_v1 import (
    consensus_from_book_rows,
    two_way_devig,
)


def test_symmetric_two_way_market_is_half_under_all_methods() -> None:
    result = two_way_devig(-110, -110)
    assert result.proportional_first == pytest.approx(0.5)
    assert result.shin_additive_first == pytest.approx(0.5)
    assert result.power_first == pytest.approx(0.5)
    assert result.shin_additive_first + result.shin_additive_second == pytest.approx(1.0)
    assert result.power_first + result.power_second == pytest.approx(1.0)
    assert result.power_exponent > 1.0


def test_two_way_shin_is_additive_not_proportional_by_assumption() -> None:
    result = two_way_devig(-170, +145)
    additive_first = result.first_raw_implied - result.overround / 2.0
    assert result.shin_additive_first == pytest.approx(additive_first)
    assert result.shin_additive_first + result.shin_additive_second == pytest.approx(1.0)
    assert result.proportional_first + result.proportional_second == pytest.approx(1.0)
    assert result.power_first + result.power_second == pytest.approx(1.0)
    assert 0.0 < result.power_first < 1.0


def test_consensus_requires_one_capture_batch_and_unique_books() -> None:
    rows = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "horizon": "T-45m",
                "request_timestamp_utc": "2026-09-13T19:15:00+00:00",
                "sportsbook_key": "a",
                "home_moneyline": -150,
                "away_moneyline": 130,
            },
            {
                "game_id": "g1",
                "horizon": "T-45m",
                "request_timestamp_utc": "2026-09-13T19:15:00+00:00",
                "sportsbook_key": "b",
                "home_moneyline": -145,
                "away_moneyline": 125,
            },
        ]
    )
    result = consensus_from_book_rows(rows)
    assert result["source_count"] == 2
    assert result["completed_2026_outcomes_used"] == 0
    assert result["production_authorized"] is False
    assert result["shin_two_way_note"] == "algebraically_equivalent_to_additive_for_two_outcomes"
    for key in ("proportional_home_prob", "shin_two_way_home_prob", "power_home_prob"):
        assert 0.0 < result[key] < 1.0

    mixed = rows.copy()
    mixed.loc[1, "request_timestamp_utc"] = "2026-09-13T19:16:00+00:00"
    with pytest.raises(ValueError, match="one game/horizon/request batch"):
        consensus_from_book_rows(mixed)

    duplicated = rows.copy()
    duplicated.loc[1, "sportsbook_key"] = "a"
    with pytest.raises(ValueError, match="unique"):
        consensus_from_book_rows(duplicated)
