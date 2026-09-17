from copy import deepcopy
from datetime import datetime, timezone

import numpy as np
import pytest

from nfl_forecast.challenger_props_simulation import (
    GameSimulationInput,
    PlayerSimulationInput,
    TeamSimulationInput,
    simulate_game,
)
from nfl_forecast.props_integration import (
    assert_simulation_accounting,
    build_forecast_artifact,
    public_prop_type,
)
from nfl_forecast.props_market import PropMarketQuote, build_market_artifact
from nfl_forecast.props_publication import (
    build_history_view,
    build_public_props,
    grade_forecast_receipt,
    make_closing_event,
    make_forecast_receipt,
)

UTC = timezone.utc
FORECAST = datetime(2026, 9, 17, 22, 0, tzinfo=UTC)
KICKOFF = datetime(2026, 9, 20, 20, 0, tzinfo=UTC)


def _player(
    player_id,
    player,
    position,
    team,
    opponent,
    *,
    pass_share=0.0,
    target_share=0.0,
    catch_rate=0.65,
    ypr=10.0,
    carry_share=0.0,
    ypc=4.2,
    rec_td_share=0.0,
    rush_td_share=0.0,
    primary_qb=False,
):
    return PlayerSimulationInput(
        player_id=player_id,
        player=player,
        position=position,
        team=team,
        opponent=opponent,
        availability_probability=1.0,
        pass_attempt_share=pass_share,
        target_share=target_share,
        catch_rate=catch_rate,
        receiving_yards_per_reception=ypr,
        carry_share=carry_share,
        rushing_yards_per_carry=ypc,
        receiving_td_share=rec_td_share,
        rushing_td_share=rush_td_share,
        data_quality_state="opportunity:high;efficiency:qualified_moderate_history",
        route_participation=0.90 if target_share else 0.0,
        is_primary_qb=primary_qb,
        passing_td_share=1.0 if primary_qb else 0.0,
    )


def _game():
    ari = TeamSimulationInput(
        team="ARI",
        opponent="LAR",
        mean_offensive_plays=64,
        offensive_plays_sd=5,
        neutral_pass_rate=0.58,
        pass_rate_sd=0.03,
        pass_rate_game_script_sensitivity=0.03,
        expected_passing_tds=1.8,
        expected_rushing_tds=1.0,
        residual_catch_rate=0.62,
        residual_yards_per_reception=9.5,
        residual_yards_per_carry=4.0,
    )
    lar = TeamSimulationInput(
        team="LAR",
        opponent="ARI",
        mean_offensive_plays=63,
        offensive_plays_sd=5,
        neutral_pass_rate=0.60,
        pass_rate_sd=0.03,
        pass_rate_game_script_sensitivity=0.03,
        expected_passing_tds=1.7,
        expected_rushing_tds=0.9,
        residual_catch_rate=0.63,
        residual_yards_per_reception=9.8,
        residual_yards_per_carry=4.0,
    )
    players = (
        _player("qb-a", "ARI QB", "QB", "ARI", "LAR", pass_share=1, carry_share=.12, ypc=5.0, rush_td_share=.16, primary_qb=True),
        _player("rb-a1", "ARI RB1", "RB", "ARI", "LAR", target_share=.14, catch_rate=.78, ypr=7.5, carry_share=.48, ypc=4.5, rec_td_share=.08, rush_td_share=.46),
        _player("rb-a2", "ARI RB2", "RB", "ARI", "LAR", target_share=.08, catch_rate=.74, ypr=7.0, carry_share=.18, ypc=4.2, rec_td_share=.05, rush_td_share=.18),
        _player("wr-a1", "ARI WR1", "WR", "ARI", "LAR", target_share=.25, catch_rate=.68, ypr=13.0, carry_share=.01, ypc=6.0, rec_td_share=.30, rush_td_share=.01),
        _player("wr-a2", "ARI WR2", "WR", "ARI", "LAR", target_share=.15, catch_rate=.64, ypr=11.5, rec_td_share=.16),
        _player("te-a", "ARI TE", "TE", "ARI", "LAR", target_share=.13, catch_rate=.71, ypr=10.2, rec_td_share=.18),
        _player("qb-l", "LAR QB", "QB", "LAR", "ARI", pass_share=1, carry_share=.10, ypc=4.5, rush_td_share=.10, primary_qb=True),
        _player("rb-l", "LAR RB", "RB", "LAR", "ARI", target_share=.14, carry_share=.58, rec_td_share=.08, rush_td_share=.55),
        _player("wr-l", "LAR WR", "WR", "LAR", "ARI", target_share=.30, catch_rate=.68, ypr=12.5, rec_td_share=.38),
        _player("te-l", "LAR TE", "TE", "LAR", "ARI", target_share=.18, catch_rate=.70, ypr=10.0, rec_td_share=.22),
    )
    return GameSimulationInput(
        game_id="2026_03_ARI_LAR",
        home_team="ARI",
        away_team="LAR",
        data_horizon=FORECAST.isoformat(),
        teams=(ari, lar),
        players=players,
        shared_pace_correlation=.2,
        shared_scoring_log_sd=.1,
    )


def _market(player_id, player, prop_type, *, line=None, yes_no=False):
    quotes = []
    for key, over, under in (("a", -110, -110), ("b", -105, -115)):
        kwargs = dict(
            provider="fixture",
            sportsbook_key=key,
            sportsbook_title=f"Book {key.upper()}",
            captured_at_utc=FORECAST,
            player_id=player_id,
            player=player,
            game_id="2026_03_ARI_LAR",
            prop_type=prop_type,
            team="ARI",
            opponent="LAR",
            position="QB" if player_id == "qb-a" else "RB" if player_id.startswith("rb") else "TE" if player_id.startswith("te") else "WR",
            kickoff_utc=KICKOFF,
        )
        if yes_no:
            quotes.append(PropMarketQuote(**kwargs, yes_american=over, no_american=under))
        else:
            quotes.append(PropMarketQuote(**kwargs, line=line, over_american=over, under_american=under))
    return build_market_artifact(quotes, as_of_utc=FORECAST)


def _markets():
    return [
        _market("qb-a", "ARI QB", "passing_yards", line=245.5),
        _market("qb-a", "ARI QB", "rushing_yards", line=27.5),
        _market("qb-a", "ARI QB", "passing_tds", line=1.5),
        _market("rb-a1", "ARI RB1", "rushing_yards", line=68.5),
        _market("rb-a1", "ARI RB1", "receiving_yards", line=21.5),
        _market("rb-a1", "ARI RB1", "receptions", line=3.5),
        _market("rb-a1", "ARI RB1", "rushing_tds", line=.5),
        _market("rb-a1", "ARI RB1", "anytime_td", yes_no=True),
        _market("wr-a1", "ARI WR1", "receiving_yards", line=71.5),
        _market("wr-a1", "ARI WR1", "receptions", line=5.5),
        _market("wr-a1", "ARI WR1", "anytime_td", yes_no=True),
        _market("te-a", "ARI TE", "receiving_yards", line=43.5),
        _market("te-a", "ARI TE", "receptions", line=4.5),
        _market("te-a", "ARI TE", "anytime_td", yes_no=True),
    ]


def test_td_prop_names_normalize_only_at_publication_boundary():
    assert public_prop_type("rushing_tds") == "rushing_td"
    assert public_prop_type("receiving_tds") == "receiving_td"
    assert public_prop_type("passing_tds") == "passing_tds"


def test_integrated_synthetic_game_generates_required_research_beta_markets():
    result = simulate_game(_game(), simulations=5000, seed=20260917)
    assert assert_simulation_accounting(result)
    before = result.player_stats["wr-a1"]["receiving_yards"].copy()

    artifact = build_forecast_artifact(
        result,
        _markets(),
        kickoff_utc=KICKOFF,
        forecast_timestamp_utc=FORECAST,
    )
    np.testing.assert_array_equal(before, result.player_stats["wr-a1"]["receiving_yards"])

    required = {
        ("qb-a", "passing_yards"),
        ("qb-a", "rushing_yards"),
        ("qb-a", "passing_tds"),
        ("rb-a1", "rushing_yards"),
        ("rb-a1", "receiving_yards"),
        ("rb-a1", "receptions"),
        ("rb-a1", "rushing_td"),
        ("rb-a1", "anytime_td"),
        ("wr-a1", "receiving_yards"),
        ("wr-a1", "receptions"),
        ("wr-a1", "anytime_td"),
        ("te-a", "receiving_yards"),
        ("te-a", "receptions"),
        ("te-a", "anytime_td"),
    }
    index = {(row["player_id"], row["prop_type"]): row for row in artifact["forecasts"]}
    assert required.issubset(index)
    assert all(index[key]["signal_state"] == "WATCH" for key in required)

    qb_pass = index[("qb-a", "passing_yards")]
    assert qb_pass["model"]["fair_line"] == qb_pass["model"]["median"]
    assert qb_pass["market"]["line"] == 245.5
    assert qb_pass["model"]["over_probability"] + qb_pass["model"]["under_probability"] + qb_pass["model"]["push_probability"] == pytest.approx(1.0)
    assert qb_pass["market"]["raw_implied_over_probability"] is not None
    assert qb_pass["market"]["no_vig_over_probability"] is not None

    rb_td = index[("rb-a1", "rushing_td")]
    assert rb_td["market"]["underlying_count_line"] == .5
    assert 0 <= rb_td["model"]["td_probability"] <= 1
    assert 0 <= rb_td["model"]["probability_2_plus_td"] <= rb_td["model"]["td_probability"]
    assert rb_td["market"]["no_vig_probability"] is not None

    # Residual/unmodeled buckets remain live and reconcile with modeled production.
    assert np.any(result.team_stats["ARI"]["residual_targets"] > 0)
    assert np.any(result.team_stats["ARI"]["residual_receiving_yards"] > 0)

    public = build_public_props(artifact, now_utc=FORECAST)
    public_index = {(row["player_id"], row["prop_type"]): row for row in public["forecasts"]}
    assert public_index[("qb-a", "passing_yards")]["model"]["fair_line"] == qb_pass["model"]["fair_line"]
    assert public_index[("rb-a1", "rushing_td")]["model"]["td_probability"] == rb_td["model"]["td_probability"]


def test_non_half_rushing_td_count_market_fails_closed_for_binary_card():
    result = simulate_game(_game(), simulations=1500, seed=7)
    bad_market = _market("rb-a1", "ARI RB1", "rushing_tds", line=1.5)
    artifact = build_forecast_artifact(
        result,
        [bad_market],
        kickoff_utc=KICKOFF,
        forecast_timestamp_utc=FORECAST,
    )
    row = next(
        row for row in artifact["forecasts"]
        if row["player_id"] == "rb-a1" and row["prop_type"] == "rushing_td"
    )
    assert row["signal_state"] == "NO SIGNAL"
    assert row["data_quality"]["critical_ok"] is False
    assert any("0.5" in note for note in row["data_quality"]["notes"])


def test_forecast_lock_close_and_grade_lifecycle_preserves_original():
    result = simulate_game(_game(), simulations=2000, seed=11)
    artifact = build_forecast_artifact(
        result,
        [_market("wr-a1", "ARI WR1", "receiving_yards", line=71.5)],
        kickoff_utc=KICKOFF,
        forecast_timestamp_utc=FORECAST,
    )
    raw = next(
        row for row in artifact["forecasts"]
        if row["player_id"] == "wr-a1" and row["prop_type"] == "receiving_yards"
    )
    original = deepcopy(raw)
    receipt = make_forecast_receipt(raw, recorded_utc=FORECAST)
    close = make_closing_event(
        receipt["forecast_id"],
        captured_utc="2026-09-20T19:55:00+00:00",
        source="consensus",
        line=74.5,
        over_price_american=-110,
        under_price_american=-110,
    )
    grade = grade_forecast_receipt(
        receipt,
        actual_result=80,
        graded_utc="2026-09-20T23:00:00+00:00",
    )
    view = build_history_view([receipt], [close], [grade])[0]
    assert receipt["original_forecast"] == original
    assert view["original_forecast"]["market"]["line"] == 71.5
    assert view["closing_market"]["line"] == 74.5
    assert view["grade"]["actual_result"] == 80
