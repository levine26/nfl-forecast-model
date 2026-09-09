import numpy as np
import pandas as pd

from nfl_forecast.market_diagnostics import (
    analytic_linear_brier_weight,
    blend_probabilities,
    build_market_diagnostics,
    build_walk_forward_blend,
    build_weight_grid,
    current_slate_summary,
    disagreement_buckets,
)


def _frame():
    return pd.DataFrame({
        "season": [2022, 2022, 2023, 2023, 2024, 2024, 2025, 2025],
        "home_win": [1, 0, 1, 0, 1, 0, 1, 0],
        "pure": [0.52, 0.48, 0.55, 0.45, 0.58, 0.42, 0.62, 0.38],
        "market": [0.80, 0.20, 0.78, 0.22, 0.76, 0.24, 0.74, 0.26],
    }).assign(
        gap=lambda x: (x.pure - x.market).abs(),
        favorite_flip=lambda x: (x.pure >= 0.5) != (x.market >= 0.5),
    )


def test_blend_boundaries_match_sources_for_linear_and_logit():
    pure = np.array([0.31, 0.66, 0.82])
    market = np.array([0.48, 0.58, 0.73])
    for method in ("linear", "logit"):
        np.testing.assert_allclose(blend_probabilities(pure, market, 0.0, method), pure)
        np.testing.assert_allclose(blend_probabilities(pure, market, 1.0, method), market)


def test_market_dominant_sample_prefers_high_weight_and_analytic_clips_to_one():
    frame = _frame()
    grid = build_weight_grid(frame, weights=[0.0, 0.25, 0.5, 0.75, 1.0])
    linear = grid[grid.method.eq("linear")].sort_values("brier")
    assert float(linear.iloc[0].market_weight) == 1.0
    analytic = analytic_linear_brier_weight(frame)
    assert analytic["unconstrained"] > 1.0
    assert analytic["constrained"] == 1.0


def test_walk_forward_selection_uses_only_prior_seasons():
    frame = _frame()
    walk = build_walk_forward_blend(frame, weights=[0.0, 1.0])
    row = walk[(walk.method.eq("linear")) & (walk.test_season.eq(2024))].iloc[0]
    assert int(row.train_through) == 2023
    assert int(row.train_games) == 4
    assert float(row.selected_market_weight) == 1.0


def test_disagreement_buckets_and_current_slate_summary():
    frame = pd.DataFrame({
        "season": [2023, 2023, 2024, 2024],
        "home_win": [1, 0, 1, 0],
        "pure": [0.70, 0.40, 0.62, 0.47],
        "market": [0.55, 0.60, 0.58, 0.46],
    })
    frame["gap"] = (frame.pure - frame.market).abs()
    frame["favorite_flip"] = (frame.pure >= 0.5) != (frame.market >= 0.5)
    buckets = disagreement_buckets(frame)
    by_gap = {row["minimum_gap_pp"]: row for row in buckets}
    assert by_gap[5.0]["games"] == 2
    assert by_gap[10.0]["games"] == 2
    assert by_gap[0.0]["favorite_flips"] == 1

    current = pd.DataFrame({
        "game_id": ["a", "b", "c"],
        "away_team": ["A", "C", "E"],
        "home_team": ["B", "D", "F"],
        "pure_home_prob": [0.70, 0.42, 0.51],
        "market_home_prob": [0.55, 0.58, 0.505],
        "final_home_prob": [0.6625, 0.46, 0.50875],
    })
    summary = current_slate_summary(current)
    assert summary["games_with_market"] == 3
    assert summary["favorite_flips"] == 1
    assert summary["gaps_10pp_or_more"] == 2
    assert summary["largest_disagreements"][0]["game_id"] in {"a", "b"}


def test_full_audit_labels_closing_market_and_does_not_recommend_production_change():
    # Historical and OOF inputs share the same original indices, as in pipeline.run.
    idx = list(range(8))
    oof = _frame().set_index(pd.Index(idx))[["season", "home_win", "pure"]].rename(columns={"pure": "stack"})
    historical = pd.DataFrame({
        "season": _frame().season,
        "home_win": _frame().home_win,
        "market_home_prob": _frame().market,
        "game_id": [f"g{i}" for i in idx],
    }, index=idx)
    audit, grid, walk = build_market_diagnostics(historical, oof)
    assert audit["status"] == "healthy"
    assert "closing-line" in audit["historical_market_scope"]
    assert audit["production_market_weight"] == 0.25
    assert audit["descriptive_closing_line_best"]["linear"]["market_weight"] == 1.0
    assert len(grid) > 0
    assert set(walk.method) == {"linear", "logit"}
    assert any("must not" in text for text in audit["guardrails"])
