import pandas as pd
import pytest

from nfl_forecast.props_opportunity import _player_beta_posterior
from nfl_forecast.props_opportunity_adapter import (
    current_players_from_canonical_state,
    prepare_player_history_for_opportunity,
)


def _state():
    return pd.DataFrame(
        [
            {
                "schema_version": "levline_props_player_state.v1",
                "game_id": "2026_03_LA_ARI",
                "player_id": "QB1",
                "player_name": "Quarterback",
                "position": "QB",
                "team": "ARI",
                "expected_active_state": "AVAILABLE",
                "availability_source_status": "CURRENT_TIMESTAMPED",
                "expected_role": "QB_PRIMARY",
            },
            {
                "schema_version": "levline_props_player_state.v1",
                "game_id": "2026_03_LA_ARI",
                "player_id": "QB2",
                "player_name": "Backup Quarterback",
                "position": "QB",
                "team": "ARI",
                "expected_active_state": "AVAILABLE",
                "availability_source_status": "CURRENT_TIMESTAMPED",
                "expected_role": "QB_RESERVE",
            },
            {
                "schema_version": "levline_props_player_state.v1",
                "game_id": "2026_03_LA_ARI",
                "player_id": "WR1",
                "player_name": "Wide One",
                "position": "WR",
                "team": "ARI",
                "expected_active_state": "QUESTIONABLE",
                "availability_source_status": "CURRENT_TIMESTAMPED",
                "expected_role": "WR_PRIMARY",
            },
            {
                "schema_version": "levline_props_player_state.v1",
                "game_id": "2026_03_LA_ARI",
                "player_id": "WR2",
                "player_name": "Wide Two",
                "position": "WR",
                "team": "ARI",
                "expected_active_state": "OUT",
                "availability_source_status": "CURRENT_TIMESTAMPED",
                "expected_role": "WR_REGULAR",
            },
        ]
    )


def test_adapter_requires_explicit_prior_for_uncertain_state():
    with pytest.raises(ValueError, match="preregistered Beta prior"):
        current_players_from_canonical_state(
            _state(),
            game_id="2026_03_LA_ARI",
            team="ARI",
        )


def test_adapter_preserves_explicit_states_and_beta_uncertainty():
    out = current_players_from_canonical_state(
        _state(),
        game_id="2026_03_LA_ARI",
        team="ARI",
        availability_priors={"QUESTIONABLE": (3.0, 2.0)},
    ).set_index("player_id")

    assert out.loc["QB1", "availability_probability"] == 1.0
    assert bool(out.loc["QB1", "is_primary_qb"]) is True
    assert bool(out.loc["QB2", "is_primary_qb"]) is False
    assert out.loc["WR2", "availability_probability"] == 0.0
    assert out.loc["WR1", "availability_probability"] == pytest.approx(0.6)
    assert out.loc["WR1", "availability_uncertainty"] > 0
    assert str(out.loc["WR1", "availability_prior_source"]).startswith("explicit_beta_prior")


def test_governed_qb_and_role_overrides_require_provenance():
    kwargs = {
        "game_id": "2026_03_LA_ARI",
        "team": "ARI",
        "availability_priors": {"QUESTIONABLE": (3.0, 2.0)},
    }
    with pytest.raises(ValueError, match="primary QB override"):
        current_players_from_canonical_state(
            _state(),
            **kwargs,
            primary_qb_player_id="QB2",
        )
    with pytest.raises(ValueError, match="role adjustments"):
        current_players_from_canonical_state(
            _state(),
            **kwargs,
            role_adjustments={"WR1": {"target_role_multiplier": 0.5}},
        )

    out = current_players_from_canonical_state(
        _state(),
        **kwargs,
        primary_qb_player_id="QB2",
        primary_qb_provenance="verified pregame starter source",
        role_adjustments={"WR1": {"target_role_multiplier": 0.5}},
        role_adjustments_provenance="verified pregame limitation source",
    ).set_index("player_id")
    assert bool(out.loc["QB2", "is_primary_qb"]) is True
    assert bool(out.loc["QB1", "is_primary_qb"]) is False
    assert out.loc["WR1", "target_role_multiplier"] == 0.5
    assert out.loc["QB2", "primary_qb_source"] == "verified pregame starter source"
    assert out.loc["WR1", "role_adjustment_source"] == "verified pregame limitation source"


def test_missing_routes_require_explicit_prior_and_add_zero_effective_evidence():
    team_history = pd.DataFrame(
        [
            {"game_id": "g1", "team": "ARI", "dropbacks": 40.0},
            {"game_id": "g2", "team": "ARI", "dropbacks": 36.0},
        ]
    )
    player_history = pd.DataFrame(
        [
            {"game_id": "g1", "team": "ARI", "player_id": "WR1", "position": "WR", "routes": None},
            {"game_id": "g2", "team": "ARI", "player_id": "WR1", "position": "WR", "routes": None},
            {"game_id": "g1", "team": "ARI", "player_id": "TE1", "position": "TE", "routes": 25},
            {"game_id": "g2", "team": "ARI", "player_id": "TE1", "position": "TE", "routes": 22},
        ]
    )

    with pytest.raises(ValueError, match="position prior means"):
        prepare_player_history_for_opportunity(player_history, team_history)

    prepared, audit = prepare_player_history_for_opportunity(
        player_history,
        team_history,
        route_prior_means={"WR": 0.80},
    )
    wr = prepared[prepared["player_id"].eq("WR1")]
    te = prepared[prepared["player_id"].eq("TE1")]
    assert wr["route_history_observed"].eq(False).all()
    assert wr["dropbacks"].sum() == 0.0
    assert wr["route_prior_mean"].dropna().unique().tolist() == [0.8]
    assert te["route_history_observed"].eq(True).all()
    assert te["dropbacks"].tolist() == [40.0, 36.0]
    assert audit["route_prior_only_player_ids"] == ["WR1"]
    assert audit["fabricated_observed_routes"] == 0
    assert audit["prior_only_dropbacks_per_missing_row"] == 0.0


def test_explicit_missing_route_prior_survives_same_position_observed_history():
    team_history = pd.DataFrame(
        [
            {"game_id": "g1", "team": "ARI", "dropbacks": 40},
            {"game_id": "g2", "team": "ARI", "dropbacks": 40},
        ]
    )
    player_history = pd.DataFrame(
        [
            {"game_id": "g1", "season": 2025, "week": 1, "team": "ARI", "player_id": "WR_MISSING", "position": "WR", "routes": None},
            {"game_id": "g2", "season": 2025, "week": 2, "team": "ARI", "player_id": "WR_MISSING", "position": "WR", "routes": None},
            {"game_id": "g1", "season": 2025, "week": 1, "team": "ARI", "player_id": "WR_OBS", "position": "WR", "routes": 10},
            {"game_id": "g2", "season": 2025, "week": 2, "team": "ARI", "player_id": "WR_OBS", "position": "WR", "routes": 10},
        ]
    )
    prepared, _ = prepare_player_history_for_opportunity(
        player_history,
        team_history,
        route_prior_means={"WR": 0.80},
    )
    dist, trials = _player_beta_posterior(
        prepared,
        team_history,
        "WR_MISSING",
        "WR",
        numerator="routes",
        denominator="dropbacks",
        default_mean=0.45,
        prior_strength=24.0,
        half_life_games=8.0,
        label="route-test",
        prior_mean_column="route_prior_mean",
    )
    assert trials == 0.0
    assert dist["mean"] == pytest.approx(0.80)
