import pandas as pd
import pytest

from nfl_forecast.props_efficiency_td import (
    build_efficiency_td_parameters,
    simulator_contract_columns,
)


def _player(
    player_id: str,
    name: str,
    position: str,
    *,
    pass_attempts: float = 0,
    qb_rushes: float = 0,
    carries: float = 0,
    routes: float = 0,
    targets: float = 0,
    hist_pass: float = 0,
    hist_comp: float = 0,
    hist_pass_yards: float = 0,
    hist_qb_rush: float = 0,
    hist_qb_rush_yards: float = 0,
    hist_carries: float = 0,
    hist_rush_yards: float = 0,
    hist_targets: float = 0,
    hist_receptions: float = 0,
    hist_receiving_yards: float = 0,
    hist_rz_targets: float = 0,
    hist_ez_targets: float = 0,
    hist_goal_line: float = 0,
) -> dict:
    return {
        "game_id": "2026_03_A_B",
        "season": 2026,
        "week": 3,
        "team": "A",
        "opponent": "B",
        "player_id": player_id,
        "player_name": name,
        "position": position,
        "forecast_timestamp": "2026-09-17T18:00:00Z",
        "kickoff_timestamp": "2026-09-20T17:00:00Z",
        "feature_data_horizon": "2026-09-17T17:30:00Z",
        "source_status": "qualified",
        "prior_model_trained_through_season": 2025,
        "expected_pass_attempts": pass_attempts,
        "expected_qb_rush_attempts": qb_rushes,
        "expected_carries": carries,
        "expected_routes": routes,
        "expected_targets": targets,
        "hist_pass_attempts": hist_pass,
        "hist_completions": hist_comp,
        "hist_passing_yards": hist_pass_yards,
        "hist_qb_rush_attempts": hist_qb_rush,
        "hist_qb_rush_yards": hist_qb_rush_yards,
        "hist_carries": hist_carries,
        "hist_rushing_yards": hist_rush_yards,
        "hist_targets": hist_targets,
        "hist_receptions": hist_receptions,
        "hist_receiving_yards": hist_receiving_yards,
        "hist_red_zone_targets": hist_rz_targets,
        "hist_end_zone_targets": hist_ez_targets,
        "hist_goal_line_carries": hist_goal_line,
        "prior_completion_rate": 0.64,
        "prior_yards_per_completion_mean": 11.2,
        "prior_yards_per_completion_sd": 6.0,
        "prior_qb_rush_ypc_mean": 5.3,
        "prior_qb_rush_ypc_sd": 4.5,
        "prior_rush_ypc_mean": 4.3,
        "prior_rush_ypc_sd": 3.8,
        "prior_catch_rate": 0.68,
        "prior_receiving_ypr_mean": 10.5,
        "prior_receiving_ypr_sd": 6.0,
        "prior_red_zone_target_rate": 0.14,
        "prior_end_zone_target_rate": 0.07,
        "prior_goal_line_carry_rate": 0.08,
    }


def _team() -> dict:
    return {
        "game_id": "2026_03_A_B",
        "season": 2026,
        "week": 3,
        "team": "A",
        "opponent": "B",
        "forecast_timestamp": "2026-09-17T18:00:00Z",
        "kickoff_timestamp": "2026-09-20T17:00:00Z",
        "feature_data_horizon": "2026-09-17T17:30:00Z",
        "source_status": "qualified",
        "prior_model_trained_through_season": 2025,
        "expected_drives": 10.5,
        "expected_red_zone_trips": 3.4,
        "prior_red_zone_td_rate": 0.58,
        "prior_pass_td_fraction": 0.62,
        "expected_non_red_zone_pass_tds": 0.22,
        "expected_non_red_zone_rush_tds": 0.08,
    }


def _inputs() -> tuple[pd.DataFrame, pd.DataFrame]:
    players = [
        _player(
            "qb1", "Quarter Back", "QB", pass_attempts=34, qb_rushes=5,
            hist_pass=500, hist_comp=330, hist_pass_yards=3900,
            hist_qb_rush=70, hist_qb_rush_yards=360, hist_goal_line=4,
        ),
        _player(
            "rb1", "Running Back", "RB", carries=16, routes=22, targets=4,
            hist_carries=220, hist_rush_yards=990, hist_targets=55, hist_receptions=44,
            hist_receiving_yards=350, hist_rz_targets=9, hist_ez_targets=2,
            hist_goal_line=18,
        ),
        _player(
            "wr1", "Wide One", "WR", carries=1, routes=32, targets=9,
            hist_carries=8, hist_rush_yards=45, hist_targets=120, hist_receptions=78,
            hist_receiving_yards=1100, hist_rz_targets=20, hist_ez_targets=10,
        ),
        _player(
            "te1", "Tight End", "TE", routes=27, targets=6,
            hist_targets=80, hist_receptions=55, hist_receiving_yards=620,
            hist_rz_targets=18, hist_ez_targets=9,
        ),
    ]
    return pd.DataFrame(players), pd.DataFrame([_team()])


def test_td_allocations_reconcile_team_counts() -> None:
    players, teams = _inputs()
    build = build_efficiency_td_parameters(players, teams)
    diag = build.diagnostics.iloc[0]
    team = build.team_td_parameters.iloc[0]

    assert diag["reconciled"]
    assert diag["receiving_td_share_sum"] == pytest.approx(1.0)
    assert diag["rushing_td_share_sum"] == pytest.approx(1.0)
    assert diag["passing_td_share_sum"] == pytest.approx(1.0)
    assert build.player_parameters.expected_receiving_tds.sum() == pytest.approx(
        team.expected_passing_td_opportunities
    )
    assert build.player_parameters.expected_rushing_tds.sum() == pytest.approx(
        team.expected_rushing_td_opportunities
    )
    assert build.player_parameters.expected_passing_tds.sum() == pytest.approx(
        team.expected_passing_td_opportunities
    )


def test_small_sample_efficiency_is_shrunk_toward_prior() -> None:
    players, teams = _inputs()
    mask = players.player_id.eq("wr1")
    players.loc[
        mask,
        [
            "hist_targets", "hist_receptions", "hist_receiving_yards",
            "hist_red_zone_targets", "hist_end_zone_targets",
        ],
    ] = [2, 2, 40, 1, 1]
    build = build_efficiency_td_parameters(players, teams)
    wr = build.player_parameters.set_index("player_id").loc["wr1"]

    assert abs(wr.catch_rate_mean - 0.68) < abs(1.0 - 0.68)
    assert abs(wr.receiving_yards_per_reception_mean - 10.5) < abs(20.0 - 10.5)


def test_matchup_adjustment_requires_pre_2026_coefficients() -> None:
    players, teams = _inputs()
    players["explosive_pass_suppression_z"] = 0.0
    players.loc[players.player_id.eq("wr1"), "explosive_pass_suppression_z"] = 1.0
    coeff = pd.DataFrame([
        {
            "scope": "player",
            "metric": "receiving_ypr",
            "feature": "explosive_pass_suppression_z",
            "coefficient": -0.10,
            "trained_through_season": 2025,
            "model_id": "pre2026-v1",
            "position_scope": "WR",
        }
    ])

    neutral = build_efficiency_td_parameters(players, teams)
    adjusted = build_efficiency_td_parameters(players, teams, matchup_coefficients=coeff)
    n = neutral.player_parameters.set_index("player_id").loc[
        "wr1", "receiving_yards_per_reception_mean"
    ]
    a = adjusted.player_parameters.set_index("player_id").loc[
        "wr1", "receiving_yards_per_reception_mean"
    ]
    assert a < n

    coeff.loc[0, "trained_through_season"] = 2026
    with pytest.raises(ValueError, match="2026"):
        build_efficiency_td_parameters(players, teams, matchup_coefficients=coeff)


def test_anytime_td_includes_wr_rushing_td_expectation() -> None:
    players, teams = _inputs()
    build = build_efficiency_td_parameters(players, teams)
    wr = build.player_parameters.set_index("player_id").loc["wr1"]

    assert wr.expected_rushing_tds > 0
    assert wr.expected_anytime_tds == pytest.approx(
        wr.expected_rushing_tds + wr.expected_receiving_tds
    )


def test_matchup_coefficients_require_finite_training_provenance() -> None:
    players, teams = _inputs()
    players["explosive_pass_suppression_z"] = 0.0
    coeff = pd.DataFrame([
        {
            "scope": "player",
            "metric": "receiving_ypr",
            "feature": "explosive_pass_suppression_z",
            "coefficient": -0.10,
            "trained_through_season": None,
            "model_id": "missing-provenance",
            "position_scope": "WR",
        }
    ])

    with pytest.raises(ValueError, match="provenance"):
        build_efficiency_td_parameters(players, teams, matchup_coefficients=coeff)


def test_td_allocation_uncertainty_uses_dirichlet_share_sd() -> None:
    players, teams = _inputs()
    build = build_efficiency_td_parameters(players, teams)
    out = build.player_parameters.set_index("player_id")

    assert out.loc["qb1", "passing_td_share_sd"] == pytest.approx(0.0)
    assert out.loc["wr1", "receiving_td_share_sd"] > 0
    assert out.loc["wr1", "rushing_td_share_sd"] > 0
    assert out.loc["wr1", "td_allocation_uncertainty"] == pytest.approx(
        max(
            out.loc["wr1", "passing_td_share_sd"],
            out.loc["wr1", "receiving_td_share_sd"],
            out.loc["wr1", "rushing_td_share_sd"],
        )
    )
    assert (
        out.loc["wr1", "td_allocation_uncertainty_method"]
        == "max_dirichlet_marginal_share_sd"
    )


def test_rejects_team_red_zone_trips_above_drives() -> None:
    players, teams = _inputs()
    teams.loc[0, "expected_red_zone_trips"] = 11.0

    with pytest.raises(ValueError, match="cannot exceed expected_drives"):
        build_efficiency_td_parameters(players, teams)


def test_player_and_team_game_metadata_must_align() -> None:
    players, teams = _inputs()
    players.loc[players.player_id.eq("wr1"), "opponent"] = "C"

    with pytest.raises(ValueError, match="metadata mismatch"):
        build_efficiency_td_parameters(players, teams)


def test_timestamps_must_be_timezone_aware() -> None:
    players, teams = _inputs()
    players.loc[0, "forecast_timestamp"] = "2026-09-17T18:00:00"

    with pytest.raises(ValueError, match="timezone-aware"):
        build_efficiency_td_parameters(players, teams)


def test_rejects_postkickoff_and_retrospective_inputs() -> None:
    players, teams = _inputs()
    players.loc[0, "forecast_timestamp"] = "2026-09-20T18:00:00Z"
    with pytest.raises(ValueError, match="before kickoff"):
        build_efficiency_td_parameters(players, teams)

    players, teams = _inputs()
    players["actual_receiving_yards"] = 0
    with pytest.raises(ValueError, match="postgame"):
        build_efficiency_td_parameters(players, teams)


def test_simulator_contract_and_research_guardrail() -> None:
    players, teams = _inputs()
    build = build_efficiency_td_parameters(players, teams)
    contract = simulator_contract_columns()

    assert set(contract["player_parameters"]).issubset(build.player_parameters.columns)
    assert set(contract["team_td_parameters"]).issubset(build.team_td_parameters.columns)
    assert build.audit["completed_2026_outcomes_used_for_architecture_or_tuning"] == 0
    assert not build.player_parameters.winner_probability_feature_authorized.any()
