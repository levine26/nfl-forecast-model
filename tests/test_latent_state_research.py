from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from nfl_forecast.latent_state_research import (
    OFFSEASON_CARRY,
    build_game_latent_features,
    build_latent_team_state,
    latent_feature_columns,
)


def _team_games() -> pd.DataFrame:
    rows = []
    games = [
        (2023, 1, "2023_01_A_B", 0.40, -0.20),
        (2023, 2, "2023_02_A_B", 0.30, -0.10),
        (2023, 3, "2023_03_A_B", 0.20, 0.00),
        (2023, 4, "2023_04_A_B", 0.10, 0.05),
        (2024, 1, "2024_01_A_B", 0.25, -0.05),
        (2024, 2, "2024_02_A_B", 0.15, 0.00),
    ]
    for season, week, game_id, a_epa, b_epa in games:
        rows.extend(
            [
                {
                    "game_id": game_id,
                    "season": season,
                    "week": week,
                    "team": "A",
                    "home_team": "A",
                    "away_team": "B",
                    "neutral_epa": a_epa,
                },
                {
                    "game_id": game_id,
                    "season": season,
                    "week": week,
                    "team": "B",
                    "home_team": "A",
                    "away_team": "B",
                    "neutral_epa": b_epa,
                },
            ]
        )
    return pd.DataFrame(rows)


def test_week_state_is_frozen_before_same_week_observation():
    base = _team_games()
    changed = base.copy()
    # Mutate only one team's realized Week 3 observation. A common-mode shift to both
    # teams is intentionally removed by the pre-registered state-centering step.
    changed.loc[
        (changed.season.eq(2023)) & (changed.week.eq(3)) & changed.team.eq("A"),
        "neutral_epa",
    ] += 10.0

    original_state = build_latent_team_state(base).pregame_state
    changed_state = build_latent_team_state(changed).pregame_state

    week_three_original = original_state[(original_state.season.eq(2023)) & (original_state.week.eq(3))]
    week_three_changed = changed_state[(changed_state.season.eq(2023)) & (changed_state.week.eq(3))]
    pd.testing.assert_frame_equal(
        week_three_original.reset_index(drop=True),
        week_three_changed.reset_index(drop=True),
    )

    week_four_original = original_state[(original_state.season.eq(2023)) & (original_state.week.eq(4))]
    week_four_changed = changed_state[(changed_state.season.eq(2023)) & (changed_state.week.eq(4))]
    assert not np.allclose(
        week_four_original["latent_offense_state"].to_numpy(),
        week_four_changed["latent_offense_state"].to_numpy(),
    )


def test_row_order_and_within_week_order_are_invariant():
    base = _team_games()
    shuffled = base.sample(frac=1.0, random_state=20260910).reset_index(drop=True)
    left = build_latent_team_state(base).pregame_state
    right = build_latent_team_state(shuffled).pregame_state
    pd.testing.assert_frame_equal(left.reset_index(drop=True), right.reset_index(drop=True))


def test_offseason_carry_is_exactly_half_of_prior_terminal_state():
    built = build_latent_team_state(_team_games())
    terminal_2023 = built.terminal_state[built.terminal_state.season.eq(2023)].set_index("team")
    week1_2024 = built.pregame_state[
        built.pregame_state.season.eq(2024) & built.pregame_state.week.eq(1)
    ].set_index("team")
    for team in ["A", "B"]:
        assert np.isclose(
            week1_2024.loc[team, "latent_offense_state"],
            OFFSEASON_CARRY * terminal_2023.loc[team, "latent_offense_state"],
        )
        assert np.isclose(
            week1_2024.loc[team, "latent_defense_weakness_state"],
            OFFSEASON_CARRY * terminal_2023.loc[team, "latent_defense_weakness_state"],
        )
    assert built.audit["max_abs_post_center_mean"] < 1e-12


def test_game_feature_contract_is_exactly_two_features():
    built = build_latent_team_state(_team_games())
    games = pd.DataFrame(
        {
            "game_id": ["2023_03_A_B"],
            "home_team": ["A"],
            "away_team": ["B"],
        }
    )
    matchup = build_game_latent_features(games, built.pregame_state)
    features = latent_feature_columns(matchup)
    assert features == ["latent_diff_offense_state", "latent_home_defensive_advantage"]
    state = built.pregame_state[built.pregame_state.game_id.eq("2023_03_A_B")].set_index("team")
    assert np.isclose(
        matchup.iloc[0].latent_diff_offense_state,
        state.loc["A", "latent_offense_state"] - state.loc["B", "latent_offense_state"],
    )
    assert np.isclose(
        matchup.iloc[0].latent_home_defensive_advantage,
        state.loc["B", "latent_defense_weakness_state"] - state.loc["A", "latent_defense_weakness_state"],
    )


def test_f_ls_01_hard_rejects_2026_outcomes():
    frame = _team_games().iloc[:2].copy()
    frame["season"] = 2026
    with pytest.raises(ValueError, match="after 2025"):
        build_latent_team_state(frame)


def test_production_prediction_modules_do_not_import_latent_state_research():
    protected = [
        "src/nfl_forecast/pipeline.py",
        "src/nfl_forecast/models.py",
        "src/nfl_forecast/features.py",
        "src/nfl_forecast/publish.py",
        "scripts/run_week.py",
    ]
    forbidden = ("latent_state_research", "challenger_latent_state")
    for filename in protected:
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"), filename=filename)
        imports: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        assert not any(token in imported for imported in imports for token in forbidden)
