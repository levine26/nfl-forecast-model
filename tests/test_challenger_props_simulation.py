from __future__ import annotations

import numpy as np
import pytest

from nfl_forecast.challenger_props_simulation import (
    GameSimulationInput,
    MarketQuote,
    PlayerSimulationInput,
    SimulationInputError,
    TeamSimulationInput,
    build_forecasts,
    build_game_input_from_upstream,
    evaluate_distribution,
    simulate_game,
)


def _game() -> GameSimulationInput:
    ari = TeamSimulationInput(
        team="ARI", opponent="LAR", mean_offensive_plays=64.0, offensive_plays_sd=5.5,
        neutral_pass_rate=0.56, pass_rate_sd=0.025,
        pass_rate_game_script_sensitivity=0.045, expected_passing_tds=1.8,
        expected_rushing_tds=1.0, residual_catch_rate=0.63,
        residual_yards_per_reception=10.0, residual_yards_per_carry=4.1,
    )
    lar = TeamSimulationInput(
        team="LAR", opponent="ARI", mean_offensive_plays=62.0, offensive_plays_sd=5.0,
        neutral_pass_rate=0.59, pass_rate_sd=0.025,
        pass_rate_game_script_sensitivity=0.05, expected_passing_tds=1.6,
        expected_rushing_tds=0.9, residual_catch_rate=0.64,
        residual_yards_per_reception=10.5, residual_yards_per_carry=4.0,
    )
    players = (
        PlayerSimulationInput(
            player_id="qb-ari", player="ARI QB", position="QB", team="ARI", opponent="LAR",
            availability_probability=1.0, pass_attempt_share=1.0, target_share=0.0,
            catch_rate=0.0, receiving_yards_per_reception=0.0, carry_share=0.14,
            rushing_yards_per_carry=5.2, receiving_td_share=0.0, rushing_td_share=0.18,
            data_quality_state="mock_complete",
        ),
        PlayerSimulationInput(
            player_id="rb-ari", player="ARI RB", position="RB", team="ARI", opponent="LAR",
            availability_probability=1.0, pass_attempt_share=0.0, target_share=0.16,
            catch_rate=0.78, receiving_yards_per_reception=7.8, carry_share=0.60,
            rushing_yards_per_carry=4.5, receiving_td_share=0.10, rushing_td_share=0.58,
            data_quality_state="mock_complete",
        ),
        PlayerSimulationInput(
            player_id="wr-ari", player="ARI WR", position="WR", team="ARI", opponent="LAR",
            availability_probability=1.0, pass_attempt_share=0.0, target_share=0.28,
            catch_rate=0.66, receiving_yards_per_reception=13.2, carry_share=0.02,
            rushing_yards_per_carry=6.0, receiving_td_share=0.36, rushing_td_share=0.03,
            data_quality_state="mock_complete",
        ),
        PlayerSimulationInput(
            player_id="qb-lar", player="LAR QB", position="QB", team="LAR", opponent="ARI",
            availability_probability=1.0, pass_attempt_share=1.0, target_share=0.0,
            catch_rate=0.0, receiving_yards_per_reception=0.0, carry_share=0.08,
            rushing_yards_per_carry=4.0, receiving_td_share=0.0, rushing_td_share=0.08,
            data_quality_state="mock_complete",
        ),
        PlayerSimulationInput(
            player_id="rb-lar", player="LAR RB", position="RB", team="LAR", opponent="ARI",
            availability_probability=1.0, pass_attempt_share=0.0, target_share=0.14,
            catch_rate=0.76, receiving_yards_per_reception=7.0, carry_share=0.64,
            rushing_yards_per_carry=4.3, receiving_td_share=0.08, rushing_td_share=0.62,
            data_quality_state="mock_complete",
        ),
        PlayerSimulationInput(
            player_id="te-lar", player="LAR TE", position="TE", team="LAR", opponent="ARI",
            availability_probability=1.0, pass_attempt_share=0.0, target_share=0.20,
            catch_rate=0.70, receiving_yards_per_reception=10.5, carry_share=0.0,
            rushing_yards_per_carry=0.0, receiving_td_share=0.26, rushing_td_share=0.0,
            data_quality_state="mock_complete",
        ),
    )
    return GameSimulationInput(
        game_id="2026_03_ARI_LAR", home_team="ARI", away_team="LAR",
        data_horizon="2026-09-17T15:00:00-07:00", teams=(ari, lar), players=players,
        shared_pace_correlation=0.35, shared_scoring_log_sd=0.12,
    )


def _posterior_game() -> GameSimulationInput:
    game = _game()
    teams = tuple(
        TeamSimulationInput(
            **{
                **team.__dict__,
                "offensive_plays_gamma_shape": 640.0 if team.team == "ARI" else 620.0,
                "offensive_plays_gamma_rate": 10.0,
                "dropback_rate_alpha": 60.0 if team.team == "ARI" else 62.0,
                "dropback_rate_beta": 40.0 if team.team == "ARI" else 38.0,
                "pass_attempt_outcome_alpha": 90.0,
                "sack_outcome_alpha": 7.0,
                "scramble_outcome_alpha": 3.0,
                "targetable_attempt_alpha": 92.0,
                "targetable_attempt_beta": 8.0,
            }
        )
        for team in game.teams
    )
    players = []
    for player in game.players:
        target_concentration = player.target_share * 60.0 if player.target_share > 0 else None
        carry_concentration = player.carry_share * 60.0 if player.carry_share > 0 else None
        receiving_td_alpha = (
            player.receiving_td_share * 40.0 if player.receiving_td_share > 0 else None
        )
        rushing_td_alpha = (
            player.rushing_td_share * 40.0 if player.rushing_td_share > 0 else None
        )
        route_alpha = 18.0 if player.target_share > 0 else None
        route_beta = 6.0 if player.target_share > 0 else None
        catch_alpha = player.catch_rate * 30.0 if player.target_share > 0 else None
        catch_beta = (1.0 - player.catch_rate) * 30.0 if player.target_share > 0 else None
        players.append(
            PlayerSimulationInput(
                **{
                    **player.__dict__,
                    "is_primary_qb": player.position == "QB",
                    "route_participation": 0.75 if player.target_share > 0 else 0.0,
                    "route_participation_alpha": route_alpha,
                    "route_participation_beta": route_beta,
                    "designed_carry_share_alpha": carry_concentration,
                    "target_share_alpha": target_concentration,
                    "catch_alpha": catch_alpha,
                    "catch_beta": catch_beta,
                    "receiving_yards_per_reception_event_sd": (
                        8.0 if player.target_share > 0 else None
                    ),
                    "receiving_yards_per_reception_mean_se": (
                        0.6 if player.target_share > 0 else 0.0
                    ),
                    "rushing_yards_per_carry_event_sd": (
                        3.0 if player.carry_share > 0 else None
                    ),
                    "rushing_yards_per_carry_mean_se": (
                        0.3 if player.carry_share > 0 else 0.0
                    ),
                    "passing_td_share": (
                        1.0 if player.position == "QB" else 0.0
                    ),
                    "passing_td_allocation_alpha": (
                        30.0 if player.position == "QB" else None
                    ),
                    "receiving_td_allocation_alpha": receiving_td_alpha,
                    "rushing_td_allocation_alpha": rushing_td_alpha,
                }
            )
        )
    return GameSimulationInput(
        **{
            **game.__dict__,
            "teams": teams,
            "players": tuple(players),
        }
    )



def _upstream_payloads() -> tuple[list[dict], list[dict], list[dict], dict]:
    game = _posterior_game()
    projections: list[dict] = []
    efficiency_rows: list[dict] = []
    team_td_rows: list[dict] = []
    residuals: dict[str, dict[str, float]] = {}

    for team in game.teams:
        roster = [player for player in game.players if player.team == team.team]
        carry_players = [player for player in roster if player.carry_share > 0.0]
        target_players = [player for player in roster if player.target_share > 0.0]
        projections.append(
            {
                "metadata": {
                    "game_id": game.game_id,
                    "team": team.team,
                    "opponent": team.opponent,
                    "data_horizon": game.data_horizon,
                },
                "hierarchy": {
                    "team_offensive_plays": {
                        "mean": team.mean_offensive_plays,
                        "sd": team.offensive_plays_sd,
                        "gamma_shape": team.offensive_plays_gamma_shape,
                        "gamma_rate": team.offensive_plays_gamma_rate,
                    },
                    "dropback_rate_given_team_plays": {
                        "mean": team.neutral_pass_rate,
                        "sd": team.pass_rate_sd,
                        "alpha": team.dropback_rate_alpha,
                        "beta": team.dropback_rate_beta,
                    },
                    "dropback_outcome_given_dropback": {
                        "concentration": {
                            "pass_attempts": team.pass_attempt_outcome_alpha,
                            "sacks": team.sack_outcome_alpha,
                            "qb_scrambles": team.scramble_outcome_alpha,
                        }
                    },
                    "designed_carry_share_given_designed_rush": {
                        "mean_share": {
                            player.player_id: player.carry_share for player in carry_players
                        },
                        "concentration": {
                            player.player_id: player.designed_carry_share_alpha
                            for player in carry_players
                        },
                    },
                    "route_participation_given_dropback": {
                        player.player_id: {
                            "mean": player.route_participation,
                            "alpha": player.route_participation_alpha,
                            "beta": player.route_participation_beta,
                        }
                        for player in target_players
                    },
                    "targetable_attempt_rate_given_pass_attempt": {
                        "mean": 0.92,
                        "alpha": team.targetable_attempt_alpha,
                        "beta": team.targetable_attempt_beta,
                    },
                    "target_share_given_team_target": {
                        "mean_share": {
                            player.player_id: player.target_share for player in target_players
                        },
                        "concentration": {
                            player.player_id: player.target_share_alpha
                            for player in target_players
                        },
                    },
                    "reception_probability_given_target": {
                        player.player_id: {
                            "mean": player.catch_rate,
                            "alpha": player.catch_alpha,
                            "beta": player.catch_beta,
                        }
                        for player in target_players
                    },
                },
                "players": [
                    {
                        "player_id": player.player_id,
                        "player_name": player.player,
                        "position": player.position,
                        "availability_probability": player.availability_probability,
                        "is_primary_qb": player.is_primary_qb,
                    }
                    for player in roster
                ],
                "audit": {"data_quality": "mock_contract"},
            }
        )
        team_td_rows.append(
            {
                "game_id": game.game_id,
                "team": team.team,
                "expected_passing_td_opportunities": team.expected_passing_tds,
                "expected_rushing_td_opportunities": team.expected_rushing_tds,
            }
        )
        residuals[team.team] = {
            "catch_rate": team.residual_catch_rate,
            "receiving_yards_per_reception": team.residual_yards_per_reception,
            "rushing_yards_per_carry": team.residual_yards_per_carry,
        }
        for player in roster:
            efficiency_rows.append(
                {
                    "game_id": game.game_id,
                    "player_id": player.player_id,
                    "player_name": player.player,
                    "catch_alpha": player.catch_alpha,
                    "catch_beta": player.catch_beta,
                    "catch_rate_mean": player.catch_rate,
                    "receiving_yards_per_reception_mean": player.receiving_yards_per_reception,
                    "receiving_yards_per_reception_event_sd": (
                        player.receiving_yards_per_reception_event_sd
                    ),
                    "receiving_yards_per_reception_mean_se": (
                        player.receiving_yards_per_reception_mean_se
                    ),
                    "rushing_yards_per_attempt_mean": player.rushing_yards_per_carry,
                    "rushing_yards_per_attempt_event_sd": player.rushing_yards_per_carry_event_sd,
                    "rushing_yards_per_attempt_mean_se": player.rushing_yards_per_carry_mean_se,
                    "passing_td_share_mean": player.passing_td_share,
                    "receiving_td_share_mean": player.receiving_td_share,
                    "rushing_td_share_mean": player.rushing_td_share,
                    "passing_td_allocation_alpha": player.passing_td_allocation_alpha,
                    "receiving_td_allocation_alpha": player.receiving_td_allocation_alpha,
                    "rushing_td_allocation_alpha": player.rushing_td_allocation_alpha,
                    "confidence_state": "mock_contract",
                }
            )
    return projections, efficiency_rows, team_td_rows, residuals


def test_upstream_handoff_adapter_builds_simulation_ready_game() -> None:
    projections, efficiency_rows, team_td_rows, residuals = _upstream_payloads()
    game = build_game_input_from_upstream(
        home_team="ARI",
        away_team="LAR",
        opportunity_projections=projections,
        efficiency_player_parameters=efficiency_rows,
        team_td_parameters=team_td_rows,
        residual_efficiency_by_team=residuals,
        shared_pace_correlation=0.25,
        shared_scoring_log_sd=0.10,
        pass_rate_game_script_sensitivity=0.03,
    )
    assert game.game_id == "2026_03_ARI_LAR"
    assert game.teams[0].offensive_plays_gamma_shape == 640.0
    assert game.teams[0].targetable_attempt_alpha == 92.0
    assert next(p for p in game.players if p.player_id == "wr-ari").catch_alpha is not None
    result = simulate_game(game, simulations=2500, seed=901)
    for stats in result.player_stats.values():
        assert np.all(stats["targets"] <= stats["routes"])
        assert np.all(stats["receptions"] <= stats["targets"])


def test_upstream_handoff_requires_explicit_residual_efficiency() -> None:
    projections, efficiency_rows, team_td_rows, residuals = _upstream_payloads()
    residuals.pop("ARI")
    with pytest.raises(SimulationInputError, match="residual efficiency prior"):
        build_game_input_from_upstream(
            home_team="ARI",
            away_team="LAR",
            opportunity_projections=projections,
            efficiency_player_parameters=efficiency_rows,
            team_td_parameters=team_td_rows,
            residual_efficiency_by_team=residuals,
        )

def test_deterministic_execution() -> None:
    a = simulate_game(_posterior_game(), simulations=2500, seed=26)
    b = simulate_game(_posterior_game(), simulations=2500, seed=26)
    for pid in a.player_stats:
        for stat in a.player_stats[pid]:
            np.testing.assert_array_equal(a.player_stats[pid][stat], b.player_stats[pid][stat])


def test_opportunity_and_yardage_accounting_identities() -> None:
    result = simulate_game(_game(), simulations=3000, seed=8)
    for team in result.team_stats.values():
        np.testing.assert_array_equal(
            team["pass_attempts"] + team["sacks"] + team["rush_attempts"],
            team["offensive_plays"],
        )
        np.testing.assert_array_equal(
            team["modeled_qb_pass_attempts"] + team["residual_qb_pass_attempts"],
            team["pass_attempts"],
        )
        np.testing.assert_array_equal(
            team["targets"] + team["residual_targets"], team["team_targets"]
        )
        assert np.all(team["team_targets"] <= team["pass_attempts"])
        np.testing.assert_array_equal(
            team["modeled_receptions"] + team["residual_receptions"], team["completions"]
        )
        np.testing.assert_array_equal(
            team["modeled_receiving_yards"] + team["residual_receiving_yards"],
            team["passing_yards"],
        )
        np.testing.assert_array_equal(
            team["modeled_carries"] + team["residual_carries"], team["rush_attempts"]
        )
    for stats in result.player_stats.values():
        assert np.all(stats["targets"] <= stats["routes"])
        assert np.all(stats["receptions"] <= stats["targets"])
        assert np.all(stats["completions"] <= stats["pass_attempts"])


def test_posterior_hierarchy_reconciles_dropbacks_scrambles_routes_and_targets() -> None:
    result = simulate_game(_posterior_game(), simulations=6000, seed=118)
    for team_name, team in result.team_stats.items():
        np.testing.assert_array_equal(
            team["pass_attempts"] + team["sacks"] + team["scrambles"],
            team["dropbacks"],
        )
        np.testing.assert_array_equal(
            team["dropbacks"] + team["designed_rush_attempts"],
            team["offensive_plays"],
        )
        np.testing.assert_array_equal(
            team["designed_rush_attempts"] + team["scrambles"],
            team["rush_attempts"],
        )
        assert np.any(team["sacks"] > 0)
        assert np.any(team["scrambles"] > 0)
        assert np.all(team["team_targets"] <= team["pass_attempts"])
        np.testing.assert_array_equal(
            team["targets"] + team["residual_targets"],
            team["team_targets"],
        )
        qb_id = "qb-ari" if team_name == "ARI" else "qb-lar"
        assert np.all(result.player_stats[qb_id]["carries"] >= team["scrambles"])
    for stats in result.player_stats.values():
        assert np.all(stats["targets"] <= stats["routes"])
        assert np.all(stats["receptions"] <= stats["targets"])


def test_qb_passing_yards_reconcile_to_receiving_yards() -> None:
    result = simulate_game(_game(), simulations=3000, seed=9)
    np.testing.assert_array_equal(
        result.player_stats["qb-ari"]["passing_yards"],
        result.team_stats["ARI"]["passing_yards"],
    )
    np.testing.assert_array_equal(
        result.player_stats["qb-lar"]["passing_yards"],
        result.team_stats["LAR"]["passing_yards"],
    )


def test_td_reconciliation_is_exact() -> None:
    result = simulate_game(_game(), simulations=5000, seed=19)
    for team in result.team_stats.values():
        np.testing.assert_array_equal(
            team["modeled_receiving_tds"] + team["residual_receiving_tds"],
            team["passing_tds"],
        )
        np.testing.assert_array_equal(
            team["modeled_qb_passing_tds"] + team["residual_qb_passing_tds"],
            team["passing_tds"],
        )
        np.testing.assert_array_equal(
            team["modeled_rushing_tds"] + team["residual_rushing_tds"], team["rushing_tds"]
        )


def test_probability_bounds_sums_quantiles_and_push() -> None:
    samples = np.array([0, 1, 1, 1, 2, 2], dtype=float)
    summary = evaluate_distribution(samples, market_line=1.0, discrete=True)
    assert summary.p_over == pytest.approx(2 / 6)
    assert summary.p_under == pytest.approx(1 / 6)
    assert summary.p_push == pytest.approx(3 / 6)
    assert summary.p_over + summary.p_under + summary.p_push == pytest.approx(1.0)
    assert 0.0 <= summary.p_over <= 1.0
    assert summary.prediction_interval_lower <= summary.model_median <= summary.prediction_interval_upper
    assert summary.levline_fair_line == 1.0


def test_half_line_has_no_push() -> None:
    samples = np.array([0, 1, 1, 2, 3])
    summary = evaluate_distribution(samples, market_line=1.5, discrete=True)
    assert summary.p_push == 0.0
    assert summary.p_over + summary.p_under == pytest.approx(1.0)


def test_skewed_fair_line_uses_median_not_mean() -> None:
    samples = np.array([0.0] * 90 + [100.0] * 10)
    summary = evaluate_distribution(samples)
    assert summary.model_mean == pytest.approx(10.0)
    assert summary.model_median == 0.0
    assert summary.levline_fair_line == 0.0
    assert summary.levline_fair_line != summary.model_mean


def test_symmetric_continuous_fair_line_tracks_center() -> None:
    samples = np.array([-2.0, -1.0, 0.0, 1.0, 2.0])
    summary = evaluate_distribution(samples, market_line=0.0, discrete=False)
    assert summary.model_mean == pytest.approx(0.0)
    assert summary.model_median == pytest.approx(0.0)
    assert summary.levline_fair_line == pytest.approx(0.0)
    assert summary.p_over == pytest.approx(0.4)
    assert summary.p_under == pytest.approx(0.4)
    assert summary.p_push == pytest.approx(0.2)


def test_extreme_tail_market_line_evaluates_without_changing_fair_line() -> None:
    samples = np.arange(1.0, 101.0)
    baseline = evaluate_distribution(samples, discrete=False)
    extreme = evaluate_distribution(samples, market_line=10_000.5, discrete=False)
    assert extreme.levline_fair_line == baseline.levline_fair_line
    assert extreme.model_mean == baseline.model_mean
    assert extreme.p_over == pytest.approx(0.0)
    assert extreme.p_under == pytest.approx(1.0)
    assert extreme.p_push == pytest.approx(0.0)


def test_market_quote_does_not_change_simulation_and_canonical_forecast_fields() -> None:
    result = simulate_game(_game(), simulations=4000, seed=77)
    before = result.player_stats["wr-ari"]["receiving_yards"].copy()
    forecasts = build_forecasts(
        result,
        market_quotes={
            ("wr-ari", "receiving_yards"): MarketQuote(62.5, -110, -110),
            ("rb-ari", "receptions"): MarketQuote(3.0, -105, -115),
            ("rb-ari", "anytime_td"): MarketQuote(0.5, 135, -165),
        },
        forecast_timestamp="2026-09-17T22:30:00+00:00",
    )
    np.testing.assert_array_equal(before, result.player_stats["wr-ari"]["receiving_yards"])
    wr = next(
        f for f in forecasts if f.player_id == "wr-ari" and f.prop_type == "receiving_yards"
    )
    assert wr.game_id == _game().game_id
    assert wr.market_line == 62.5
    assert wr.p_over + wr.p_under + wr.p_push == pytest.approx(1.0)
    assert wr.market_no_vig_over_probability == pytest.approx(0.5)
    assert wr.line_edge == pytest.approx(wr.levline_fair_line - 62.5)
    td = next(f for f in forecasts if f.player_id == "rb-ari" and f.prop_type == "anytime_td")
    assert td.expected_tds is not None
    assert 0.0 <= td.probability_1_plus_td <= 1.0
    assert 0.0 <= td.probability_2_plus_td <= td.probability_1_plus_td
    assert td.td_count_distribution is not None
    assert sum(td.td_count_distribution.values()) == pytest.approx(1.0)


def test_game_script_preserves_shared_state_without_market_input() -> None:
    result = simulate_game(_game(), simulations=20_000, seed=123)
    corr = np.corrcoef(
        result.team_stats["ARI"]["pass_attempts"], result.team_stats["LAR"]["pass_attempts"]
    )[0, 1]
    assert corr < 0.25


def test_fail_closed_on_ambiguous_identity_invalid_share_and_nonfinite_input() -> None:
    game = _game()
    bad_player = PlayerSimulationInput(**{**game.players[0].__dict__, "player_id": ""})
    with pytest.raises(SimulationInputError, match="stable player_id"):
        simulate_game(
            GameSimulationInput(**{**game.__dict__, "players": (bad_player, *game.players[1:])}),
            simulations=10,
        )

    bad_share = PlayerSimulationInput(**{**game.players[2].__dict__, "target_share": 0.95})
    with pytest.raises(SimulationInputError, match="target_share"):
        simulate_game(
            GameSimulationInput(
                **{
                    **game.__dict__,
                    "players": (game.players[0], game.players[1], bad_share, *game.players[3:]),
                }
            ),
            simulations=10,
        )

    bad_efficiency = PlayerSimulationInput(
        **{**game.players[2].__dict__, "receiving_yards_per_reception": float("nan")}
    )
    with pytest.raises(SimulationInputError, match="must be finite"):
        simulate_game(
            GameSimulationInput(
                **{
                    **game.__dict__,
                    "players": (game.players[0], game.players[1], bad_efficiency, *game.players[3:]),
                }
            ),
            simulations=10,
        )


def test_fail_closed_on_partial_posterior_parameters() -> None:
    game = _game()
    bad_player = PlayerSimulationInput(
        **{
            **game.players[2].__dict__,
            "catch_alpha": 12.0,
            "catch_beta": None,
        }
    )
    with pytest.raises(SimulationInputError, match="must be supplied together"):
        simulate_game(
            GameSimulationInput(
                **{
                    **game.__dict__,
                    "players": (game.players[0], game.players[1], bad_player, *game.players[3:]),
                }
            ),
            simulations=10,
        )

    bad_team = TeamSimulationInput(
        **{
            **game.teams[0].__dict__,
            "dropback_rate_alpha": 55.0,
            "dropback_rate_beta": None,
        }
    )
    with pytest.raises(SimulationInputError, match="must be supplied together"):
        simulate_game(
            GameSimulationInput(
                **{
                    **game.__dict__,
                    "teams": (bad_team, game.teams[1]),
                }
            ),
            simulations=10,
        )
