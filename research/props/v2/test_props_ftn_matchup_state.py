import pandas as pd
import pytest

from research.props.v2.props_ftn_matchup_state import (
    FTNMatchupStateError,
    build_ftn_matchup_state,
    join_ftn_to_pbp,
)


def _ftn():
    return pd.DataFrame(
        [
            {
                "nflverse_game_id": "2025_01_ARI_LAR",
                "nflverse_play_id": 10,
                "season": 2025,
                "week": 1,
                "is_motion": True,
                "is_play_action": True,
                "is_screen_pass": False,
                "is_rpo": False,
                "is_no_huddle": False,
                "is_qb_out_of_pocket": False,
                "is_catchable_ball": True,
                "is_contested_ball": False,
                "is_created_reception": False,
                "is_drop": False,
                "qb_location": "S",
                "n_offense_backfield": 1,
                "n_defense_box": 6,
                "n_blitzers": 1,
                "n_pass_rushers": 5,
            },
            {
                "nflverse_game_id": "2025_02_ARI_SF",
                "nflverse_play_id": 20,
                "season": 2025,
                "week": 2,
                "is_motion": False,
                "is_play_action": False,
                "is_screen_pass": True,
                "is_rpo": True,
                "is_no_huddle": True,
                "is_qb_out_of_pocket": True,
                "is_catchable_ball": True,
                "is_contested_ball": True,
                "is_created_reception": True,
                "is_drop": True,
                "qb_location": "P",
                "n_offense_backfield": 2,
                "n_defense_box": 7,
                "n_blitzers": 0,
                "n_pass_rushers": 4,
            },
            {
                # Target week: must never enter state.
                "nflverse_game_id": "2025_03_ARI_SEA",
                "nflverse_play_id": 30,
                "season": 2025,
                "week": 3,
                "is_motion": True,
                "is_play_action": True,
                "n_defense_box": 11,
                "n_blitzers": 8,
                "n_pass_rushers": 8,
            },
        ]
    )


def _pbp():
    return pd.DataFrame(
        [
            {
                "game_id": "2025_01_ARI_LAR",
                "play_id": 10,
                "season": 2025,
                "week": 1,
                "posteam": "ARI",
                "defteam": "LAR",
            },
            {
                "game_id": "2025_02_ARI_SF",
                "play_id": 20,
                "season": 2025,
                "week": 2,
                "posteam": "ARI",
                "defteam": "SF",
            },
            {
                "game_id": "2025_03_ARI_SEA",
                "play_id": 30,
                "season": 2025,
                "week": 3,
                "posteam": "ARI",
                "defteam": "SEA",
            },
        ]
    )


def test_join_excludes_target_week_and_resolves_teams():
    joined, audit = join_ftn_to_pbp(_ftn(), _pbp(), season=2025, week=3)
    assert len(joined) == 2
    assert set(joined["posteam"]) == {"ARI"}
    assert set(joined["defteam"]) == {"LAR", "SF"}
    assert audit["target_week_rows_used"] == 0
    assert audit["matched_rows"] == 2
    assert audit["historical_exact_publication_timestamp_qualified"] is False


def test_state_builds_offense_and_defense_profiles_without_target_week():
    state, audit = build_ftn_matchup_state(
        _ftn(),
        _pbp(),
        season=2025,
        week=3,
        teams=["ARI", "LAR", "SF"],
    )
    by_team = state.set_index("team")
    assert by_team.loc["ARI", "ftn_off_games"] == 2
    assert by_team.loc["ARI", "ftn_latest_period"] == "2025-W2"
    assert 0.0 <= by_team.loc["ARI", "ftn_off_motion_rate"] <= 1.0
    assert by_team.loc["LAR", "ftn_def_games"] == 1
    assert by_team.loc["SF", "ftn_def_games"] == 1
    assert audit["target_week_rows_used"] == 0
    assert audit["postseason_participation_used"] is False
    assert audit["live_source_capable"] is True


def test_duplicate_ftn_play_identity_fails_closed():
    ftn = pd.concat([_ftn(), _ftn().iloc[[0]]], ignore_index=True)
    with pytest.raises(FTNMatchupStateError, match="duplicate canonical play keys"):
        join_ftn_to_pbp(ftn, _pbp(), season=2025, week=3)


def test_future_rows_do_not_affect_prior_state():
    base, _ = build_ftn_matchup_state(
        _ftn(),
        _pbp(),
        season=2025,
        week=3,
        teams=["ARI"],
    )
    future = _ftn().iloc[[2]].copy()
    future["week"] = 9
    future["nflverse_game_id"] = "2025_09_ARI_DAL"
    future["nflverse_play_id"] = 90
    future_pbp = _pbp().iloc[[2]].copy()
    future_pbp["week"] = 9
    future_pbp["game_id"] = "2025_09_ARI_DAL"
    future_pbp["play_id"] = 90
    augmented, _ = build_ftn_matchup_state(
        pd.concat([_ftn(), future], ignore_index=True),
        pd.concat([_pbp(), future_pbp], ignore_index=True),
        season=2025,
        week=3,
        teams=["ARI"],
    )
    pd.testing.assert_frame_equal(base.reset_index(drop=True), augmented.reset_index(drop=True))
