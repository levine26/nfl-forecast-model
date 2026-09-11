from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from research.depth_chart_state_v1 import build_depth_state, build_team_game_state


def _schedule() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": "2025_01_ARI_LAC",
                "season": 2025,
                "week": 1,
                "home_team": "LAC",
                "away_team": "ARI",
                "kickoff_utc": "2025-09-07T20:00:00Z",
            },
            {
                "game_id": "2025_02_ARI_DAL",
                "season": 2025,
                "week": 2,
                "home_team": "DAL",
                "away_team": "ARI",
                "kickoff_utc": "2025-09-14T20:00:00Z",
            },
        ]
    )


def _row(dt: str, team: str, gsis: str | None, group: str, pos: str, slot: int, rank: int) -> dict:
    return {
        "dt": dt,
        "team": team,
        "gsis_id": gsis,
        "pos_grp": group,
        "pos_abb": pos,
        "pos_slot": slot,
        "pos_rank": rank,
    }


def _depth() -> pd.DataFrame:
    rows: list[dict] = []
    # ARI Week 1 valid snapshot (T-120 is 18:00Z).
    for record in [
        ("00-QB-A", "Offense", "QB", 1),
        ("00-LT-A", "Offense", "LT", 2),
        ("00-WR-A", "Offense", "WR", 3),
        ("00-CB-A", "Defense", "CB", 4),
    ]:
        rows.append(_row("2025-09-07T15:00:00Z", "ARI", record[0], record[1], record[2], record[3], 1))
    # A post-decision update must never enter Week 1 state.
    rows.append(_row("2025-09-07T18:30:00Z", "ARI", "00-QB-FUTURE", "Offense", "QB", 1, 1))

    # ARI Week 2: QB and LT change, WR and CB remain.
    for record in [
        ("00-QB-B", "Offense", "QB", 1),
        ("00-LT-B", "Offense", "LT", 2),
        ("00-WR-A", "Offense", "WR", 3),
        ("00-CB-A", "Defense", "CB", 4),
    ]:
        rows.append(_row("2025-09-14T15:00:00Z", "ARI", record[0], record[1], record[2], record[3], 1))

    # Opponent snapshots make the game-level merge complete.
    for dt, team, suffix in [
        ("2025-09-07T14:00:00Z", "LAC", "L"),
        ("2025-09-14T14:00:00Z", "DAL", "D"),
    ]:
        for record in [
            (f"00-QB-{suffix}", "Offense", "QB", 1),
            (f"00-LT-{suffix}", "Offense", "LT", 2),
            (f"00-WR-{suffix}", "Offense", "WR", 3),
            (f"00-CB-{suffix}", "Defense", "CB", 4),
        ]:
            rows.append(_row(dt, team, record[0], record[1], record[2], record[3], 1))
    return pd.DataFrame(rows)


def test_latest_snapshot_is_selected_only_if_known_by_t120() -> None:
    state, audit = build_team_game_state(_depth(), _schedule())
    ari_w1 = state[(state.game_id == "2025_01_ARI_LAC") & (state.team == "ARI")].iloc[0]
    assert ari_w1.snapshot_utc == pd.Timestamp("2025-09-07T15:00:00Z")
    assert ari_w1.qb1_id == "00-QB-A"
    assert ari_w1.snapshot_utc <= ari_w1.decision_utc
    assert audit["future_snapshot_violations"] == 0
    assert audit["completed_2026_outcomes_used"] == 0
    assert audit["injury_status_inferred"] is False


def test_depth_changes_are_measured_against_prior_game_t120_state() -> None:
    state, _ = build_team_game_state(_depth(), _schedule())
    ari_w2 = state[(state.game_id == "2025_02_ARI_DAL") & (state.team == "ARI")].iloc[0]
    assert ari_w2.qb1_id == "00-QB-B"
    assert ari_w2.qb1_changed == 1.0
    assert ari_w2.offense_rank1_new_count == 2.0
    assert ari_w2.ol_rank1_new_count == 1.0
    assert ari_w2.defense_rank1_new_count == 0.0
    assert np.isclose(ari_w2.offense_rank1_continuity, 1 / 3)
    assert ari_w2.defense_rank1_continuity == 1.0
    assert ari_w2.ol_rank1_continuity == 0.0


def test_game_features_remain_research_only_and_do_not_need_outcomes() -> None:
    built = build_depth_state(_depth(), _schedule())
    assert len(built.game_features) == 2
    assert "depth_qb_change_count" in built.game_features.columns
    assert "depth_ol_rank1_continuity_diff" in built.game_features.columns
    assert built.audit["probability_feature_authorized"] is False
    assert built.audit["production_authorized"] is False


def test_missing_pregame_snapshot_is_explicit_not_backfilled() -> None:
    depth = _depth()
    depth = depth[depth.team.ne("LAC")]
    state, audit = build_team_game_state(depth, _schedule())
    lac = state[(state.game_id == "2025_01_ARI_LAC") & (state.team == "LAC")].iloc[0]
    assert bool(lac.state_missing) is True
    assert pd.isna(lac.snapshot_utc)
    assert audit["team_games_with_state"] == 3


def test_malformed_timestamp_fails_closed() -> None:
    depth = _depth()
    depth.loc[0, "dt"] = "not-a-time"
    with pytest.raises(ValueError, match="timestamps"):
        build_team_game_state(depth, _schedule())


def test_season_scope_is_frozen_before_any_model_evaluation() -> None:
    schedule = _schedule()
    schedule.loc[0, "season"] = 2026
    with pytest.raises(ValueError, match="frozen to seasons"):
        build_team_game_state(_depth(), schedule)


def test_missing_gsis_is_audited_not_name_filled() -> None:
    depth = _depth()
    depth.loc[(depth.team == "ARI") & (depth.pos_abb == "WR") & (depth.dt == "2025-09-14T15:00:00Z"), "gsis_id"] = None
    state, audit = build_team_game_state(depth, _schedule())
    ari_w2 = state[(state.game_id == "2025_02_ARI_DAL") & (state.team == "ARI")].iloc[0]
    assert ari_w2.rank1_gsis_coverage < 1.0
    assert audit["raw_gsis_coverage"] < 1.0
