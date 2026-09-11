from __future__ import annotations

from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest

from research.ftn_process_v1 import (
    BASE_METRICS,
    bootstrap_brier_difference,
    build_matchup_features,
    evaluate_feature_set,
    join_ftn_to_pbp,
    matchup_feature_columns,
    preprocess_ftn_fold,
    run_preregistered_evaluation,
)


def _ftn_frame(rows: int, *, season: int = 2025) -> pd.DataFrame:
    values = []
    for i in range(rows):
        values.append(
            {
                "nflverse_game_id": f"2025_01_A_B_{i // 100}",
                "nflverse_play_id": i + 1,
                "season": season,
                "week": 1,
                "date_pulled": "2025-09-10T12:00:00Z",
                "n_defense_box": 6 + (i % 2),
                "is_motion": i % 2,
                "is_play_action": (i + 1) % 2,
                "is_screen_pass": i % 3 == 0,
                "is_rpo": i % 4 == 0,
                "is_qb_out_of_pocket": i % 5 == 0,
                "is_interception_worthy": i % 17 == 0,
                "n_blitzers": i % 4,
                "n_pass_rushers": 4 + (i % 2),
                "is_qb_fault_sack": i % 19 == 0,
            }
        )
    return pd.DataFrame(values)


def _pbp_for(ftn: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "game_id": ftn["nflverse_game_id"].astype(str),
            "play_id": ftn["nflverse_play_id"],
            "posteam": "AAA",
            "defteam": "BBB",
        }
    )


def test_identity_gate_is_exactly_995_and_fail_closed() -> None:
    ftn = _ftn_frame(200)
    pbp = _pbp_for(ftn)
    pbp.loc[199, "posteam"] = None
    pbp.loc[199, "defteam"] = None

    joined, audit = join_ftn_to_pbp(ftn, pbp)
    assert audit["identity_join_rate"] == pytest.approx(0.995)
    assert len(joined) == 199
    assert audit["completed_2026_outcomes_used"] == 0

    pbp.loc[198, "posteam"] = None
    pbp.loc[198, "defteam"] = None
    with pytest.raises(RuntimeError, match="identity join rate"):
        join_ftn_to_pbp(ftn, pbp)


def test_duplicate_game_play_identity_is_rejected() -> None:
    ftn = _ftn_frame(3)
    duplicate = pd.concat([ftn, ftn.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="FTN game/play identity is not unique"):
        join_ftn_to_pbp(duplicate, _pbp_for(duplicate.iloc[:3]))

    pbp = _pbp_for(ftn)
    pbp = pd.concat([pbp, pbp.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="PBP game/play identity is not unique"):
        join_ftn_to_pbp(ftn, pbp)


def _team_game(
    game_id: str,
    team: str,
    kickoff: datetime,
    available: datetime,
    value: float,
) -> dict[str, object]:
    row: dict[str, object] = {
        "game_id": game_id,
        "nflverse_game_id": game_id,
        "team": team,
        "source_game_kickoff_utc": kickoff,
        "available_at_utc": available,
    }
    for metric in BASE_METRICS:
        row[metric] = value
    return row


def test_point_in_time_rolling_state_excludes_future_and_same_game_rows() -> None:
    utc = timezone.utc
    history = []
    for i, value in enumerate((0.1, 0.2, 0.3), start=1):
        history.append(
            _team_game(
                f"H{i}",
                "HOM",
                datetime(2025, 9, i * 7, 17, tzinfo=utc),
                datetime(2025, 9, i * 7 + 1, 12, tzinfo=utc),
                value,
            )
        )
    for i, value in enumerate((0.05, 0.10, 0.15), start=1):
        history.append(
            _team_game(
                f"A{i}",
                "AWY",
                datetime(2025, 9, i * 7, 17, tzinfo=utc),
                datetime(2025, 9, i * 7 + 1, 12, tzinfo=utc),
                value,
            )
        )

    # Both rows would materially change the mean if leakage controls failed.
    history.append(
        _team_game(
            "LATE",
            "HOM",
            datetime(2025, 9, 25, 17, tzinfo=utc),
            datetime(2025, 10, 2, 12, tzinfo=utc),
            0.99,
        )
    )
    history.append(
        _team_game(
            "TARGET",
            "HOM",
            datetime(2025, 9, 26, 17, tzinfo=utc),
            datetime(2025, 9, 27, 12, tzinfo=utc),
            0.99,
        )
    )

    games = pd.DataFrame(
        [
            {
                "game_id": "TARGET",
                "season": 2025,
                "week": 5,
                "gameday": "2025-10-01",
                "gametime": "20:00",
                "home_team": "HOM",
                "away_team": "AWY",
                "home_score": 24,
                "away_score": 20,
                "market_home_prob": 0.60,
            }
        ]
    )
    features = build_matchup_features(games, pd.DataFrame(history)).iloc[0]

    assert features["ftn_prior_game_count_home"] == 3
    assert features["ftn_prior_game_count_away"] == 3
    assert features["ftn_motion_rate_w3_diff"] == pytest.approx(0.10)
    assert features["ftn_motion_rate_w6_diff"] == pytest.approx(0.10)
    assert features["ftn_motion_rate_change_diff"] == pytest.approx(0.0)


def test_preprocessing_uses_training_only_median_and_missing_indicator() -> None:
    column = "ftn_motion_rate_w3_diff"
    train = pd.DataFrame({column: [1.0, np.nan, 3.0]})
    test = pd.DataFrame({column: [100.0, np.nan]})

    x_train, x_test, prep, names = preprocess_ftn_fold(train, test, [column])

    assert prep.medians[column] == 2.0
    assert names == [column, f"{column}__missing"]
    assert x_train.shape == (3, 2)
    assert x_test.shape == (2, 2)
    assert x_train[1, 1] == 1.0
    assert x_test[1, 1] == 1.0
    assert x_test[1, 0] == pytest.approx(0.0)


def _synthetic_evaluation_frame(rows_per_season: int = 24) -> pd.DataFrame:
    rng = np.random.default_rng(20260911)
    feature_cols = matchup_feature_columns()
    rows = []
    for season in (2022, 2023, 2024, 2025):
        for i in range(rows_per_season):
            outcome = float(i % 2)
            market = 0.40 + 0.20 * outcome + rng.normal(0.0, 0.035)
            row: dict[str, object] = {
                "game_id": f"{season}-G{i:02d}",
                "season": season,
                "home_win": outcome,
                "market_home_prob": float(np.clip(market, 0.05, 0.95)),
            }
            signed = 1.0 if outcome else -1.0
            for j, feature in enumerate(feature_cols):
                row[feature] = signed * (0.08 + (j % 5) * 0.01) + rng.normal(0.0, 0.25)
            if i % 11 == 0:
                row[feature_cols[0]] = np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def test_season_forward_evaluation_never_trains_on_test_or_future_season() -> None:
    frame = _synthetic_evaluation_frame()
    feature = matchup_feature_columns()[0]
    result = evaluate_feature_set(frame, [feature])

    expected = {
        2023: [2022],
        2024: [2022, 2023],
        2025: [2022, 2023, 2024],
    }
    for fold in result["fold_metrics"]:
        assert fold["training_seasons"] == expected[fold["test_season"]]
    assert set(result["predictions"]["season"]) == {2023, 2024, 2025}


def test_bootstrap_is_deterministic_and_stratified_by_season() -> None:
    predictions = pd.DataFrame(
        {
            "season": [2023] * 4 + [2024] * 4 + [2025] * 4,
            "home_win": [0, 1, 0, 1] * 3,
            "baseline_probability": [0.4, 0.6, 0.45, 0.55] * 3,
            "candidate_probability": [0.35, 0.65, 0.4, 0.6] * 3,
        }
    )
    first = bootstrap_brier_difference(predictions, replicates=100, seed=17)
    second = bootstrap_brier_difference(predictions, replicates=100, seed=17)

    assert first == second
    assert first["replicates"] == 100
    assert first["seed"] == 17


def test_2026_rows_are_rejected_before_historical_evaluation() -> None:
    ftn = _ftn_frame(2, season=2026)
    with pytest.raises(ValueError, match="2026-or-later FTN rows"):
        join_ftn_to_pbp(ftn, _pbp_for(ftn))

    frame = _synthetic_evaluation_frame()
    contaminated = frame.iloc[[0]].copy()
    contaminated["game_id"] = "2026-G00"
    contaminated["season"] = 2026
    frame = pd.concat([frame, contaminated], ignore_index=True)
    with pytest.raises(ValueError, match="2026-or-later rows"):
        evaluate_feature_set(frame, [matchup_feature_columns()[0]])


def test_full_preregistered_engine_is_research_only_and_has_no_rescue_path() -> None:
    report = run_preregistered_evaluation(
        _synthetic_evaluation_frame(rows_per_season=20),
        bootstrap_replicates=40,
    )

    assert report["experiment_id"] == "FTN-PROCESS-01"
    assert report["production_effect"] == "none"
    assert report["completed_2026_outcomes_used"] == 0
    assert report["qualification_decision"]["automatic_production_promotion"] is False
    assert set(report["ablations"]) == {
        "offense_process_removed",
        "defense_structure_removed",
        "change_features_removed",
        "quality_control_fields_removed",
    }
    assert "predictions" in report
