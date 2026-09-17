from __future__ import annotations

import numpy as np
import pytest

from nfl_forecast.props_simulation import (
    GameSimulationInput,
    MarketQuote,
    PlayerSimulationInput,
    SimulationInputError,
    TeamSimulationInput,
    build_forecasts,
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


def test_deterministic_execution() -> None:
    a = simulate_game(_game(), simulations=2500, seed=26)
    b = simulate_game(_game(), simulations=2500, seed=26)
    for pid in a.player_stats:
        for stat in a.player_stats[pid]:
            np.testing.assert_array_equal(a.player_stats[pid][stat], b.player_stats[pid][stat])


def test_opportunity_and_yardage_accounting_identities() -> None:
    result = simulate_game(_game(), simulations=3000, seed=8)
    for team in result.team_stats.values():
        np.testing.assert_array_equal(
            team["pass_attempts"] + team["rush_attempts"], team["offensive_plays"]
        )
        np.testing.assert_array_equal(
            team["modeled_qb_pass_attempts"] + team["residual_qb_pass_attempts"],
            team["pass_attempts"],
        )
        np.testing.assert_array_equal(
            team["targets"] + team["residual_targets"], team["pass_attempts"]
        )
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
        assert np.all(stats["receptions"] <= stats["targets"])
        assert np.all(stats["completions"] <= stats["pass_attempts"])


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


def test_fail_closed_on_ambiguous_identity_and_invalid_share() -> None:
    game = _game()
    bad_player = PlayerSimulationInput(**{**game.players[0].__dict__, "player_id": ""})
    with pytest.raises(SimulationInputError, match="stable player_id"):
        simulate_game(
            GameSimulationInput(
                **{**game.__dict__, "players": (bad_player, *game.players[1:])}
            ),
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
