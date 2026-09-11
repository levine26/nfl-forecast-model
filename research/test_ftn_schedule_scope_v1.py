from __future__ import annotations

import pandas as pd
import pytest

from research.ftn_process_v1 import aggregate_ftn_team_games
from research.run_ftn_process_v1 import prepare_schedule_frames


def _schedule() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "2025_01_AAA_BBB",
                "season": 2025,
                "week": 1,
                "game_type": "REG",
                "gameday": "2025-09-07",
                "gametime": "13:00",
                "home_team": "BBB",
                "away_team": "AAA",
                "home_score": 24,
                "away_score": 20,
                "home_moneyline": -130,
                "away_moneyline": 110,
            },
            {
                "game_id": "2025_02_CCC_DDD",
                "season": 2025,
                "week": 2,
                "game_type": "REG",
                "gameday": "2025-09-14",
                "gametime": "13:00",
                "home_team": "DDD",
                "away_team": "CCC",
                "home_score": 17,
                "away_score": 21,
                "home_moneyline": None,
                "away_moneyline": None,
            },
            {
                "game_id": "2025_00_EEE_FFF",
                "season": 2025,
                "week": 0,
                "game_type": "PRE",
                "gameday": "2025-08-10",
                "gametime": "20:00",
                "home_team": "FFF",
                "away_team": "EEE",
                "home_score": 10,
                "away_score": 7,
                "home_moneyline": -120,
                "away_moneyline": 100,
            },
        ]
    )


def test_source_schedule_scope_does_not_require_market_benchmark_eligibility() -> None:
    schedule_scope, evaluation_games = prepare_schedule_frames(_schedule())

    assert set(schedule_scope["game_id"]) == {"2025_01_AAA_BBB", "2025_02_CCC_DDD"}
    assert set(evaluation_games["game_id"]) == {"2025_01_AAA_BBB"}
    assert "market_home_prob" not in schedule_scope.columns
    assert evaluation_games["market_home_prob"].notna().all()


def test_ftn_history_game_without_moneyline_still_has_chronology_identity() -> None:
    schedule_scope, evaluation_games = prepare_schedule_frames(_schedule())
    source_game = "2025_02_CCC_DDD"
    joined = pd.DataFrame(
        [
            {
                "nflverse_game_id": source_game,
                "posteam": "CCC",
                "defteam": "DDD",
                "date_pulled_utc": pd.Timestamp("2025-09-15T12:00:00Z"),
                "n_defense_box": 7.0,
                "is_motion": 1.0,
                "is_play_action": 1.0,
                "is_screen_pass": 0.0,
                "is_rpo": 0.0,
                "is_qb_out_of_pocket": 0.0,
                "is_interception_worthy": 0.0,
                "n_blitzers": 2.0,
                "n_pass_rushers": 4.0,
                "is_qb_fault_sack": 0.0,
            },
            {
                "nflverse_game_id": source_game,
                "posteam": "DDD",
                "defteam": "CCC",
                "date_pulled_utc": pd.Timestamp("2025-09-15T12:00:00Z"),
                "n_defense_box": 6.0,
                "is_motion": 0.0,
                "is_play_action": 0.0,
                "is_screen_pass": 1.0,
                "is_rpo": 0.0,
                "is_qb_out_of_pocket": 0.0,
                "is_interception_worthy": 0.0,
                "n_blitzers": 1.0,
                "n_pass_rushers": 4.0,
                "is_qb_fault_sack": 0.0,
            },
        ]
    )

    team_games = aggregate_ftn_team_games(joined, schedule_scope)
    assert len(team_games) == 2
    assert team_games["game_id"].eq(source_game).all()
    assert team_games["source_game_kickoff_utc"].notna().all()

    # This is the pre-fix bug: using the market-evaluation subset as the chronology
    # schedule would orphan an otherwise valid prior FTN source game.
    with pytest.raises(RuntimeError, match="missing schedule identity"):
        aggregate_ftn_team_games(joined, evaluation_games)
