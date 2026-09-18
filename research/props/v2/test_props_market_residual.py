import numpy as np
import pandas as pd

from research.props.v2.props_market_residual import (
    ENGINE_VERSION,
    apply_market_prior_residual,
    fit_market_prior_residual,
    grade_directional_rows,
    no_vig_over_probability,
)


def _rows(n=40):
    records = []
    for i in range(n):
        market_over = -110 if i % 2 == 0 else 105
        market_under = -110 if i % 2 == 0 else -125
        # Synthetic training relation: when LevLine is above the market, OVER is more
        # likely. This tests mechanics only and is not predictive evidence.
        p_over = 0.62 if i % 4 in {0, 1} else 0.38
        line = 50.5
        over = p_over > 0.5
        actual = 60.0 if over else 40.0
        records.append(
            {
                "game_id": f"g{i // 4}",
                "player_id": f"p{i}",
                "prop_type": "receiving_yards",
                "over_odds": market_over,
                "under_odds": market_under,
                "p_over": p_over,
                "market_line": line,
                "actual_result": actual,
                "model_side": "OVER" if over else "UNDER",
            }
        )
    return pd.DataFrame(records)


def test_no_vig_probability_is_normalized():
    p = no_vig_over_probability(-110, -110)
    assert abs(p - 0.5) < 1e-12
    p = no_vig_over_probability(100, -120)
    assert 0.0 < p < 0.5


def test_fit_and_apply_are_deterministic():
    frame = _rows()
    first = fit_market_prior_residual(frame)
    second = fit_market_prior_residual(frame)
    assert first.engine_version == ENGINE_VERSION
    assert first.training_rows == len(frame)
    assert first.training_games == frame["game_id"].nunique()
    assert np.isclose(first.intercept, second.intercept)
    assert np.isclose(first.residual_beta, second.residual_beta)

    prediction_only = frame.drop(columns=["actual_result"])
    scored = apply_market_prior_residual(prediction_only, first)
    assert scored["challenger_p_over"].between(0, 1).all()
    assert set(scored["challenger_side"]) <= {"OVER", "UNDER"}
    assert set(scored["market_price_side"]) <= {"OVER", "UNDER"}


def test_fit_excludes_pushes():
    frame = _rows()
    push = frame.iloc[[0]].copy()
    push["player_id"] = "push"
    push["actual_result"] = push["market_line"]
    combined = pd.concat([frame, push], ignore_index=True)
    model = fit_market_prior_residual(combined)
    assert model.training_rows == len(frame)


def test_grade_preserves_push_as_unscored():
    frame = _rows(8)
    model = fit_market_prior_residual(frame)
    scored = apply_market_prior_residual(frame, model)
    scored.loc[0, "actual_result"] = scored.loc[0, "market_line"]
    graded = grade_directional_rows(scored)
    assert graded.loc[0, "market_outcome_recomputed"] == "PUSH"
    assert np.isnan(graded.loc[0, "challenger_correct"])
    assert np.isnan(graded.loc[0, "market_price_correct"])
    assert graded.loc[1:, "challenger_correct"].notna().all()
