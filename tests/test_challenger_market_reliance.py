from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.challenger_market_reliance import (
    prepare_frozen_historical_frame,
    select_forecast_horizons,
    walk_forward_weight_backtest,
)
from nfl_forecast.challenger_market_sources import (
    build_family_composites,
    devig_two_way,
    robust_logit_consensus,
)


def _historical() -> pd.DataFrame:
    rows = []
    for season in range(2019, 2026):
        for i in range(100):
            y = int(i % 2 == 0)
            market = 0.72 if y else 0.28
            pure = 0.60 if y else 0.40
            rows.append(
                {
                    "game_id": f"{season}_{(i % 18) + 1:02d}_A{i}_H{i}",
                    "season": season,
                    "home_win": y,
                    "market_prob": market,
                    "pure_prob": pure,
                }
            )
    return pd.DataFrame(rows)


def test_historical_research_refuses_2026_outcomes() -> None:
    frame = _historical()
    frame.loc[len(frame)] = {
        "game_id": "2026_01_A_H",
        "season": 2026,
        "home_win": 1,
        "market_prob": 0.6,
        "pure_prob": 0.55,
    }
    with pytest.raises(ValueError, match="2026"):
        prepare_frozen_historical_frame(frame)


def test_walk_forward_market_weights_use_only_prior_seasons() -> None:
    predictions, selections = walk_forward_weight_backtest(_historical(), pooling="logit")
    assert set(selections.season) == {2022, 2023, 2024, 2025}
    assert (selections.tuning_games >= 300).all()
    assert selections.selected_market_weight.isin([0.0, 0.25, 0.5, 0.75, 0.9, 1.0]).all()
    assert set(predictions.season.astype(int)) == {2022, 2023, 2024, 2025}


def test_horizon_selection_never_looks_past_target() -> None:
    snapshots = [
        ("2026-09-13T14:00:00Z", 0.54),
        ("2026-09-13T14:55:00Z", 0.55),
        ("2026-09-13T15:10:00Z", 0.56),
        ("2026-09-13T16:34:00Z", 0.58),
        ("2026-09-13T16:36:00Z", 0.59),
        ("2026-09-13T16:46:00Z", 0.60),
    ]
    rows = []
    for timestamp, probability in snapshots:
        rows.append(
            {
                "game_id": "2026_01_A_H",
                "season": 2026,
                "week": 1,
                "gameday": "2026-09-13",
                "gametime": "13:00",
                "away_team": "A",
                "home_team": "H",
                "prediction_timestamp_utc": timestamp,
                "snapshot_type": "MARKET",
                "prediction_id": timestamp,
                "final_home_prob": probability,
                "market_home_prob": probability + 0.01,
                "fst_pure_home_prob": 0.53,
                "final_probability_strategy": "F-ST-01-FROZEN-2026",
                "model_version": "test",
            }
        )
    grades = pd.DataFrame(
        [{"game_id": "2026_01_A_H", "actual_home_score": 24, "actual_away_score": 20}]
    )
    selected = select_forecast_horizons(pd.DataFrame(rows), grades)
    t25 = selected[selected.horizon.eq("T-25")].iloc[0]
    t15 = selected[selected.horizon.eq("T-15")].iloc[0]
    preweek = selected[selected.horizon.eq("PREWEEK")].iloc[0]
    assert t25.snapshot_timestamp_utc.startswith("2026-09-13T16:34:00")
    assert t15.snapshot_timestamp_utc.startswith("2026-09-13T16:36:00")
    assert preweek.snapshot_timestamp_utc.startswith("2026-09-13T14:00:00")
    assert bool(selected.no_lookahead.all())
    assert bool(selected.graded.all())


def test_multi_market_consensus_preserves_source_families() -> None:
    target = "2026-09-13T16:35:00Z"
    frame = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "source_name": "fanduel",
                "source_type": "sportsbook",
                "snapshot_timestamp_utc": "2026-09-13T16:34:00Z",
                "home_probability": 0.60,
            },
            {
                "game_id": "g1",
                "source_name": "draftkings",
                "source_type": "sportsbook",
                "snapshot_timestamp_utc": "2026-09-13T16:34:30Z",
                "home_probability": 0.62,
            },
            {
                "game_id": "g1",
                "source_name": "polymarket",
                "source_type": "prediction_exchange",
                "snapshot_timestamp_utc": "2026-09-13T16:34:20Z",
                "home_probability": 0.59,
            },
            {
                "game_id": "g1",
                "source_name": "future_book",
                "source_type": "sportsbook",
                "snapshot_timestamp_utc": "2026-09-13T16:36:00Z",
                "home_probability": 0.90,
            },
        ]
    )
    composites = build_family_composites(
        frame,
        target_timestamp_utc=target,
        min_sources=2,
    )
    assert "sportsbook_consensus" in set(composites.composite)
    sports = composites[composites.composite.eq("sportsbook_consensus")].iloc[0]
    assert sports.sources == 2
    assert "future_book" not in sports.source_names
    assert 0.60 < sports.home_probability < 0.62


def test_devig_and_logit_consensus_are_valid_probabilities() -> None:
    probability = devig_two_way(-120, 110)
    assert 0.5 < probability < 0.6
    pooled = robust_logit_consensus([0.55, 0.60, 0.65])
    assert np.isfinite(pooled)
    assert 0.55 <= pooled <= 0.65
