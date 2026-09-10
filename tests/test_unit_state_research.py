from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.unit_state_research import (
    attach_stable_snap_ids,
    build_game_unit_features,
    build_unit_state,
    v09c_feature_columns,
)


def _snap_rows() -> pd.DataFrame:
    rows = []
    for game_id, week, offense_id, defense_id in [
        ("2024_01_ARI_ATL", 1, "OffA00", "DefA00"),
        ("2024_02_ARI_BUF", 2, "OffA00", "DefA00"),
        # The current game's realized lineup is intentionally different. It must not
        # affect the pregame state attached to this game.
        ("2024_03_ARI_CAR", 3, "OffB00", "DefB00"),
    ]:
        rows.extend(
            [
                {
                    "game_id": game_id,
                    "season": 2024,
                    "week": week,
                    "team": "ARI",
                    "pfr_player_id": offense_id,
                    "position": "WR",
                    "offense_pct": 100.0,
                    "defense_pct": 0.0,
                },
                {
                    "game_id": game_id,
                    "season": 2024,
                    "week": week,
                    "team": "ARI",
                    "pfr_player_id": defense_id,
                    "position": "CB",
                    "offense_pct": 0.0,
                    "defense_pct": 100.0,
                },
            ]
        )
    return pd.DataFrame(rows)


def _players() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "pfr_id": ["OffA00", "DefA00", "OffB00", "DefB00"],
            "gsis_id": ["00-0000001", "00-0000002", "00-0000003", "00-0000004"],
        }
    )


def test_game_three_state_uses_only_games_one_and_two():
    built = build_unit_state(_snap_rows(), _players())
    game_three = built.team_pregame_state[built.team_pregame_state.game_id.eq("2024_03_ARI_CAR")].iloc[0]
    assert game_three.unit_state_missing == False  # noqa: E712
    assert game_three.offense_continuity == 1.0
    assert game_three.defense_continuity == 1.0
    assert game_three.skill_continuity == 1.0
    assert game_three.secondary_continuity == 1.0
    assert built.audit["current_game_snap_rows_used_for_current_game_features"] == 0


def test_first_two_games_are_explicitly_missing_not_backfilled_from_future():
    built = build_unit_state(_snap_rows(), _players())
    first_two = built.team_pregame_state[built.team_pregame_state.week.isin([1, 2])]
    assert first_two.unit_state_missing.all()
    assert first_two.offense_continuity.isna().all()
    assert first_two.defense_continuity.isna().all()


def test_ambiguous_pfr_crosswalk_fails_closed_into_unknown_weight():
    snaps = _snap_rows().iloc[:1].copy()
    players = pd.DataFrame(
        {
            "pfr_id": ["OffA00", "OffA00"],
            "gsis_id": ["00-0000001", "00-9999999"],
        }
    )
    attached, audit = attach_stable_snap_ids(snaps, players)
    assert audit["crosswalk_ambiguous_pfr_ids"] == 1
    assert attached.stable_id_known.sum() == 0
    assert audit["offense_unmapped_weight_rate"] == 1.0


def test_game_level_contract_is_exactly_eleven_features():
    state = pd.DataFrame(
        [
            {
                "game_id": "2024_03_ARI_CAR",
                "season": 2024,
                "week": 3,
                "team": team,
                "unit_state_missing": False,
                "offense_continuity": value,
                "defense_continuity": value,
                "ol_continuity": value,
                "skill_continuity": value,
                "front7_continuity": value,
                "secondary_continuity": value,
                "offense_concentration": value,
                "defense_concentration": value,
                "offense_unmapped_weight": 0.0,
                "defense_unmapped_weight": 0.0,
            }
            for team, value in [("ARI", 0.8), ("CAR", 0.6)]
        ]
    )
    schedules = pd.DataFrame(
        {
            "game_id": ["2024_03_ARI_CAR"],
            "season": [2024],
            "week": [3],
            "home_team": ["CAR"],
            "away_team": ["ARI"],
        }
    )
    games = build_game_unit_features(schedules, state)
    features = v09c_feature_columns(games)
    assert len(features) == 11
    assert np.isclose(games.iloc[0].v09c_diff_offense_continuity, -0.2)
    assert games.iloc[0].v09c_unit_state_missing_count == 0


def test_production_prediction_modules_do_not_import_v09c_unit_state():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden = ("challenger_v09c", "unit_state_research")
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(token in imported for imported in imports for token in forbidden)
