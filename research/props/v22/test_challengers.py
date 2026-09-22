from __future__ import annotations

import pytest

from research.props.v22.challengers import Props22Error, build_challenger_set


def _source(**overrides):
    row = {
        "forecast_id": "p21_test",
        "player_id": "00-1",
        "player_name": "Test Player",
        "team": "ARI",
        "opponent": "SEA",
        "position": "WR",
        "game_id": "2026_03_ARI_SEA",
        "prop_type": "receiving_yards",
        "kickoff_utc": "2026-09-27T20:25:00+00:00",
        "forecast_timestamp_utc": "2026-09-27T16:00:00+00:00",
        "model_mean": 82.0,
        "model_median": 80.0,
        "probability_over": 0.70,
        "probability_td": None,
        "market_line": 70.0,
        "market_probability_over": 0.55,
        "market_probability_td": None,
        "role_state": {"state": "STARTER_EXPECTED"},
        "market_state": {
            "book_count": 6,
            "quote_as_of": "2026-09-27T15:59:00+00:00",
        },
        "qa": {"research_eligible": True},
        "provenance": {
            "challenger_model_version": "levline-props-2.1-sunday-v0.1",
            "source_data_horizon_utc": "2026-09-27T15:55:00+00:00",
        },
    }
    row.update(overrides)
    return row


def _by_id(rows):
    return {row["challenger_id"]: row for row in rows}


def test_fixed_v02_grid_applies_line_and_market_probability_residual_math():
    rows = _by_id(build_challenger_set(_source()))

    assert rows["P21_BASE"]["line"]["challenger_line"] == pytest.approx(80.0)
    assert rows["P22_LINE_RESIDUAL_25"]["line"]["challenger_line"] == pytest.approx(72.5)
    assert rows["P22_LINE_RESIDUAL_50"]["line"]["challenger_line"] == pytest.approx(75.0)

    assert rows["P22_PROB_RESIDUAL_25"]["probability"]["challenger_probability"] == pytest.approx(
        0.55 + 0.25 * (0.70 - 0.55)
    )
    assert rows["P22_PROB_RESIDUAL_50"]["probability"]["challenger_probability"] == pytest.approx(
        0.55 + 0.50 * (0.70 - 0.55)
    )
    assert rows["P22_CAL_50"]["probability"]["challenger_probability"] == pytest.approx(0.60)

    c25 = rows["P22_COMBINED_25"]
    assert c25["line"]["challenger_line"] == pytest.approx(72.5)
    assert c25["probability"]["challenger_probability"] == pytest.approx(0.5875)
    assert c25["promotion_eligible"] is True
    assert c25["challenger_role"] == "primary_challenger"

    c50 = rows["P22_COMBINED_50"]
    assert c50["line"]["challenger_line"] == pytest.approx(75.0)
    assert c50["probability"]["challenger_probability"] == pytest.approx(0.625)
    assert c50["line"]["model_residual_vs_market"] == pytest.approx(10.0)
    assert c50["probability"]["model_residual_vs_market"] == pytest.approx(0.15)
    assert c50["research_only"] is True
    assert c50["production_authorized"] is False
    assert c50["outcome"] is None
    assert c50["chronology"]["market_chronology_ok"] is True
    assert len(c50["receipt_sha256"]) == 64


def test_missing_market_line_only_disables_market_anchored_line_candidates():
    rows = _by_id(build_challenger_set(_source(market_line=None)))
    assert rows["P21_BASE"]["line"]["line_available"] is True
    assert rows["P22_CAL_50"]["line"]["line_available"] is True
    for cid in [
        "P22_LINE_RESIDUAL_25",
        "P22_LINE_RESIDUAL_50",
        "P22_COMBINED_25",
        "P22_COMBINED_50",
    ]:
        assert rows[cid]["line"]["line_available"] is False
        assert (
            rows[cid]["line"]["unavailable_reason"]
            == "missing_market_line_for_residual_challenger"
        )


def test_missing_market_probability_disables_only_market_probability_candidates():
    rows = _by_id(build_challenger_set(_source(market_probability_over=None)))
    assert rows["P21_BASE"]["probability"]["probability_available"] is True
    assert rows["P22_CAL_50"]["probability"]["probability_available"] is True
    for cid in [
        "P22_PROB_RESIDUAL_25",
        "P22_PROB_RESIDUAL_50",
        "P22_COMBINED_25",
        "P22_COMBINED_50",
    ]:
        assert rows[cid]["probability"]["probability_available"] is False
        assert (
            rows[cid]["probability"]["unavailable_reason"]
            == "missing_market_probability_for_residual_challenger"
        )


def test_market_anchored_candidates_require_point_in_time_market_timestamp():
    source = _source(
        market_state={"book_count": 6, "quote_as_of": None},
    )
    rows = _by_id(build_challenger_set(source))

    assert rows["P21_BASE"]["line"]["line_available"] is True
    assert rows["P21_BASE"]["probability"]["probability_available"] is True
    assert rows["P22_CAL_50"]["probability"]["probability_available"] is True
    for cid in ["P22_COMBINED_25", "P22_COMBINED_50"]:
        assert rows[cid]["line"]["line_available"] is False
        assert rows[cid]["probability"]["probability_available"] is False
        assert rows[cid]["line"]["unavailable_reason"] == "missing_or_postforecast_market_timestamp"
        assert rows[cid]["probability"]["unavailable_reason"] == "missing_or_postforecast_market_timestamp"


def test_binary_td_keeps_probability_challengers_without_inventing_a_line():
    rows = _by_id(
        build_challenger_set(
            _source(
                prop_type="anytime_td",
                model_median=None,
                market_line=None,
                probability_over=None,
                probability_td=0.40,
                market_probability_over=None,
                market_probability_td=0.30,
            )
        )
    )
    for row in rows.values():
        assert row["line"]["line_available"] is False
        assert row["line"]["unavailable_reason"] == "binary_td_market_has_no_continuous_line"
    assert rows["P22_PROB_RESIDUAL_25"]["probability"]["challenger_probability"] == pytest.approx(
        0.325
    )
    assert rows["P22_PROB_RESIDUAL_50"]["probability"]["challenger_probability"] == pytest.approx(
        0.35
    )
    assert rows["P22_CAL_50"]["probability"]["challenger_probability"] == pytest.approx(0.45)


def test_invalid_source_chronology_is_rejected():
    source = _source(
        provenance={
            "challenger_model_version": "levline-props-2.1-sunday-v0.1",
            "source_data_horizon_utc": "2026-09-27T16:05:00+00:00",
        }
    )
    with pytest.raises(Props22Error, match="invalid source forecast chronology"):
        build_challenger_set(source)


def test_outcome_contamination_is_rejected():
    source = _source(outcome={"actual": 88.0})
    with pytest.raises(Props22Error, match="outcome-contaminated"):
        build_challenger_set(source)
