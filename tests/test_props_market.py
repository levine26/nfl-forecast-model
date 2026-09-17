from __future__ import annotations

from datetime import datetime, timezone

import pytest

from nfl_forecast.props_market import (
    PropMarketQuote,
    american_to_decimal,
    american_to_implied,
    best_available_price,
    build_market_artifact,
    closing_line_value,
    closing_price_value,
    compare_levline_to_market,
    decimal_to_american,
    decimal_to_implied,
    implied_to_american,
    market_survival_points,
    remove_vig_two_way,
)


UTC = timezone.utc
KICKOFF = datetime(2026, 9, 20, 17, 0, tzinfo=UTC)


def _quote(
    book: str,
    line: float | None = 75.5,
    *,
    ts: datetime = datetime(2026, 9, 20, 14, 0, tzinfo=UTC),
    over: float | None = -110,
    under: float | None = -110,
    yes: float | None = None,
    no: float | None = None,
    prop_type: str = "receiving_yards",
    alt: bool = False,
    closing: bool = False,
) -> PropMarketQuote:
    return PropMarketQuote(
        provider="test",
        sportsbook_key=book,
        sportsbook_title=book.upper(),
        captured_at_utc=ts,
        player_id="00-0031234",
        player="Example Receiver",
        game_id="2026_03_A_B",
        prop_type=prop_type,
        line=line,
        over_american=over,
        under_american=under,
        yes_american=yes,
        no_american=no,
        team="A",
        opponent="B",
        position="WR",
        kickoff_utc=KICKOFF,
        provider_event_id="event-1",
        provider_market_key="player_reception_yds",
        is_alternative_line=alt,
        is_closing=closing,
        related_market_group_id="2026_03_A_B:A",
    )


def test_american_decimal_implied_conversions_round_trip() -> None:
    assert american_to_decimal(-110) == pytest.approx(1.9090909091)
    assert american_to_decimal(150) == pytest.approx(2.5)
    assert american_to_implied(-110) == pytest.approx(110 / 210)
    assert decimal_to_implied(2.5) == pytest.approx(0.4)
    assert decimal_to_american(american_to_decimal(-135)) == pytest.approx(-135)
    assert decimal_to_american(american_to_decimal(175)) == pytest.approx(175)
    assert implied_to_american(0.5) == pytest.approx(100.0)
    for bad in (0, 99, -99, float("nan"), float("inf")):
        with pytest.raises(ValueError):
            american_to_decimal(bad)


def test_two_way_devig_preserves_raw_and_normalizes_all_supported_methods() -> None:
    for method in ("proportional", "additive", "power"):
        result = remove_vig_two_way(-115, -105, method=method)
        assert result["overround"] > 0
        assert result["first_raw_implied"] + result["second_raw_implied"] > 1
        assert result["first_no_vig"] + result["second_no_vig"] == pytest.approx(1.0)
        assert result["method"] == method


def test_quote_preserves_one_sided_anytime_td_without_fabricated_no_vig() -> None:
    quote = _quote(
        "book-a",
        None,
        over=None,
        under=None,
        yes=145,
        no=None,
        prop_type="anytime_td",
    )
    record = quote.to_record()
    assert record["yes_raw_implied"] == pytest.approx(100 / 245)
    assert record["yes_no_vig"] is None
    assert record["no_no_vig"] is None
    assert record["devig_method"] is None


def test_quote_rejects_missing_stable_identity_and_post_kickoff_capture() -> None:
    with pytest.raises(ValueError, match="player_id"):
        PropMarketQuote(
            provider="test",
            sportsbook_key="a",
            sportsbook_title="A",
            captured_at_utc=datetime(2026, 9, 20, 14, 0, tzinfo=UTC),
            player_id="",
            player="Player",
            game_id="g",
            prop_type="receptions",
            line=5.5,
            over_american=-110,
        )
    with pytest.raises(ValueError, match="post-kickoff"):
        _quote(
            "book-a",
            ts=datetime(2026, 9, 20, 17, 1, tzinfo=UTC),
        )


def test_market_artifact_filters_future_and_closing_quotes_from_live_state() -> None:
    current = _quote("a", 75.5, over=-105, under=-115)
    future = _quote(
        "b",
        99.5,
        ts=datetime(2026, 9, 20, 16, 0, tzinfo=UTC),
        over=150,
        under=-180,
    )
    closing = _quote(
        "c",
        88.5,
        ts=datetime(2026, 9, 20, 16, 59, tzinfo=UTC),
        over=-110,
        under=-110,
        closing=True,
    )
    artifact = build_market_artifact(
        [current, future, closing],
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    assert artifact["consensus_line"] == 75.5
    assert artifact["sportsbooks"] == ["a"]
    assert artifact["closing_evaluation"] is None


def test_closing_data_is_explicit_evaluation_only_and_never_part_of_live_consensus() -> None:
    live = _quote("a", 75.5)
    closing = _quote(
        "a",
        79.5,
        ts=datetime(2026, 9, 20, 16, 59, tzinfo=UTC),
        over=-105,
        under=-115,
        closing=True,
    )
    artifact = build_market_artifact(
        [live, closing],
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        include_closing_evaluation=True,
        evaluation_as_of_utc=KICKOFF,
    )
    assert artifact["consensus_line"] == 75.5
    closing_eval = artifact["closing_evaluation"]
    assert closing_eval["evaluation_only"] is True
    assert closing_eval["evaluation_as_of_utc"] == KICKOFF.isoformat()
    assert closing_eval["closing_line"] == 79.5
    assert closing_eval["best_closing_over_price"]["american"] == -105
    assert closing_eval["best_closing_under_price"]["american"] == -115
    assert closing_eval["individual_books"][0]["over_american"] == -105
    assert closing_eval["individual_books"][0]["closing_evaluation_only"] is True


def test_closing_attachment_requires_explicit_non_lookahead_evaluation_horizon() -> None:
    live = _quote("a", 75.5)
    closing = _quote(
        "a",
        79.5,
        ts=datetime(2026, 9, 20, 16, 59, tzinfo=UTC),
        closing=True,
    )
    forecast_as_of = datetime(2026, 9, 20, 15, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="evaluation_as_of_utc is required"):
        build_market_artifact(
            [live, closing],
            as_of_utc=forecast_as_of,
            include_closing_evaluation=True,
        )

    before_close = build_market_artifact(
        [live, closing],
        as_of_utc=forecast_as_of,
        include_closing_evaluation=True,
        evaluation_as_of_utc=datetime(2026, 9, 20, 16, 30, tzinfo=UTC),
    )
    assert before_close["closing_evaluation"] is None


def test_consensus_reports_line_dispersion_and_like_for_like_probability() -> None:
    quotes = [
        _quote("a", 74.5, over=-120, under=100),
        _quote("b", 75.5, over=-110, under=-110),
        _quote("c", 76.5, over=100, under=-120),
    ]
    artifact = build_market_artifact(
        quotes,
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    assert artifact["consensus_line"] == 75.5
    assert artifact["line_min"] == 74.5
    assert artifact["line_max"] == 76.5
    assert artifact["line_range"] == 2.0
    assert artifact["consensus_no_vig_p_over"] == pytest.approx(0.5)
    assert artifact["consensus_no_vig_p_under"] == pytest.approx(0.5)
    assert artifact["consensus_probability_method"] == "market_survival_at_consensus_line"
    assert artifact["market_data_quality"]["state"] == "multi_book_two_way"
    assert artifact["market_data_quality"]["primary_sportsbook_count"] == 3
    assert artifact["market_data_quality"]["two_way_probability_available"] is True


def test_alternative_line_survival_is_monotone_after_projection() -> None:
    quotes = [
        _quote("a", 75.5),
        _quote("a", 70.5, over=125, under=-145, alt=True),
        _quote("b", 80.5, over=-145, under=125, alt=True),
    ]
    points = market_survival_points(
        quotes,
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    probs = [row["monotone_p_over"] for row in points]
    assert all(left >= right for left, right in zip(probs, probs[1:]))
    assert [row["line"] for row in points] == sorted(row["line"] for row in points)


def test_best_available_price_is_selected_at_same_threshold() -> None:
    quotes = [
        _quote("a", 75.5, over=-120, under=100),
        _quote("b", 75.5, over=105, under=-125),
        _quote("c", 76.5, over=130, under=-150),
    ]
    best = best_available_price(
        quotes,
        side="over",
        line=75.5,
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    assert best["sportsbook_key"] == "b"
    assert best["american"] == 105


def test_movement_uses_only_observed_primary_snapshots() -> None:
    quotes = [
        _quote("a", 72.5, ts=datetime(2026, 9, 20, 12, 0, tzinfo=UTC)),
        _quote("a", 75.5, ts=datetime(2026, 9, 20, 14, 0, tzinfo=UTC)),
        _quote("b", 74.5, ts=datetime(2026, 9, 20, 13, 0, tzinfo=UTC)),
    ]
    artifact = build_market_artifact(
        quotes,
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    assert artifact["movement"]["consensus_opening_line"] == 73.5
    assert artifact["movement"]["consensus_current_line"] == 75.0
    assert artifact["movement"]["consensus_line_movement"] == 1.5
    by_book = {
        row["sportsbook_key"]: row
        for row in artifact["movement"]["per_book"]
    }
    assert by_book["a"]["price_movement_comparable"] is False
    assert by_book["a"]["over_price_movement_decimal"] is None
    assert by_book["b"]["price_movement_comparable"] is True
    assert by_book["b"]["over_price_movement_decimal"] == pytest.approx(0.0)


def test_price_movement_is_computed_only_when_threshold_is_unchanged() -> None:
    quotes = [
        _quote(
            "a",
            75.5,
            ts=datetime(2026, 9, 20, 12, 0, tzinfo=UTC),
            over=-120,
            under=100,
        ),
        _quote(
            "a",
            75.5,
            ts=datetime(2026, 9, 20, 14, 0, tzinfo=UTC),
            over=105,
            under=-125,
        ),
    ]
    artifact = build_market_artifact(
        quotes,
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    row = artifact["movement"]["per_book"][0]
    assert row["price_movement_comparable"] is True
    assert row["over_price_movement_decimal"] == pytest.approx(
        american_to_decimal(105) - american_to_decimal(-120)
    )
    assert row["over_raw_implied_movement_pp"] == pytest.approx(
        100.0 * (american_to_implied(105) - american_to_implied(-120))
    )


def test_levline_comparison_outputs_deltas_and_fair_prices_not_recommendation() -> None:
    market = build_market_artifact(
        [_quote("a", 76.5), _quote("b", 76.5)],
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    comparison = compare_levline_to_market(
        market,
        levline_fair_line=83.5,
        levline_p_over=0.618,
        levline_p_under=0.382,
    )
    assert comparison["line_difference"] == 7.0
    assert comparison["probability_difference_over_pp"] == pytest.approx(11.8)
    assert comparison["levline_fair_over_american"] < 0
    assert comparison["bet_recommendation"] is None


def test_binary_two_way_market_can_be_devigged_but_one_sided_cannot() -> None:
    two_way = _quote(
        "a",
        None,
        over=None,
        under=None,
        yes=-135,
        no=115,
        prop_type="anytime_td",
    )
    one_way = _quote(
        "b",
        None,
        over=None,
        under=None,
        yes=150,
        no=None,
        prop_type="anytime_td",
    )
    artifact = build_market_artifact(
        [two_way, one_way],
        as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
    )
    assert artifact["consensus_no_vig_probability"] is not None
    assert artifact["best_yes_price"]["sportsbook_key"] == "b"
    assert [row["yes_no_vig"] for row in artifact["individual_books"]].count(None) == 1


def test_market_artifact_rejects_mixed_player_or_prop_identity() -> None:
    first = _quote("a")
    second = PropMarketQuote(
        provider="test",
        sportsbook_key="b",
        sportsbook_title="B",
        captured_at_utc=datetime(2026, 9, 20, 14, 0, tzinfo=UTC),
        player_id="different",
        player="Other",
        game_id=first.game_id,
        prop_type=first.prop_type,
        line=75.5,
        over_american=-110,
        under_american=-110,
        kickoff_utc=KICKOFF,
    )
    with pytest.raises(ValueError, match="cannot mix"):
        build_market_artifact(
            [first, second],
            as_of_utc=datetime(2026, 9, 20, 15, 0, tzinfo=UTC),
        )


def test_side_aware_threshold_and_same_line_price_clv() -> None:
    assert closing_line_value(captured_line=76.5, closing_line=80.5, side="over") == 4.0
    assert closing_line_value(captured_line=80.5, closing_line=76.5, side="under") == 4.0
    assert closing_price_value(captured_american=105, closing_american=-110) == pytest.approx(
        american_to_decimal(105) - american_to_decimal(-110)
    )
