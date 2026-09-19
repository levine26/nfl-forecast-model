import numpy as np
import pandas as pd

from research.props.v2.props_ftn_market_residual import (
    FEATURES_BY_PROP,
    add_market_features,
    apply_ftn_market_residual,
    fit_ftn_market_residual,
)


def _training(prop_type: str, n: int = 180) -> pd.DataFrame:
    rows = []
    features = FEATURES_BY_PROP[prop_type]
    for i in range(n):
        signal = 1.0 if i % 4 in {0, 1} else -1.0
        row = {
            "game_id": f"g{i // 5}",
            "player_id": f"p{i}",
            "prop_type": prop_type,
            "over_odds": -110,
            "under_odds": -110,
            "p_over": 0.52 if signal > 0 else 0.48,
            "market_line": 50.5,
            "actual_result": 62.0 if signal > 0 else 39.0,
        }
        for j, feature in enumerate(features):
            row[feature] = signal * (1.0 + j / 20.0)
        rows.append(row)
    return pd.DataFrame(rows)


def test_market_offset_gap_zero_when_probabilities_match():
    frame = pd.DataFrame([{"over_odds": -110, "under_odds": -110, "p_over": 0.5}])
    out = add_market_features(frame)
    assert abs(out.loc[0, "market_no_vig_p_over"] - 0.5) < 1e-12
    assert abs(out.loc[0, "levline_market_logit_gap"]) < 1e-12


def test_fit_is_deterministic_and_scores():
    frame = _training("receiving_yards")
    first = fit_ftn_market_residual(frame, prop_type="receiving_yards")
    second = fit_ftn_market_residual(frame, prop_type="receiving_yards")
    assert first.training_rows == len(frame)
    assert np.isclose(first.intercept, second.intercept)
    assert np.allclose(first.coefficients, second.coefficients)
    scored = apply_ftn_market_residual(
        frame.drop(columns=["actual_result"]),
        {"receiving_yards": first},
    )
    assert scored["ftn_challenger_p_over"].between(0, 1).all()
    assert set(scored["ftn_challenger_side"].dropna()) <= {"OVER", "UNDER"}


def test_missing_ftn_is_explicit_not_zero_performance():
    train = _training("rushing_yards")
    model = fit_ftn_market_residual(train, prop_type="rushing_yards")
    pred = train.iloc[[0]].drop(columns=["actual_result"]).copy()
    for feature in FEATURES_BY_PROP["rushing_yards"]:
        pred[feature] = np.nan
    scored = apply_ftn_market_residual(pred, {"rushing_yards": model})
    assert np.isfinite(scored.iloc[0]["ftn_challenger_p_over"])
    assert any(name.endswith("__missing") for name in model.transformed_feature_names)


def test_matched_baseline_can_exclude_all_ftn_features():
    frame = _training("passing_yards")
    model = fit_ftn_market_residual(
        frame,
        prop_type="passing_yards",
        feature_columns=("levline_market_logit_gap",),
    )
    assert model.transform.columns == ("levline_market_logit_gap",)
    assert model.transformed_feature_names == ("levline_market_logit_gap",)


def test_push_is_excluded_from_training():
    frame = _training("receptions")
    push = frame.iloc[[0]].copy()
    push["player_id"] = "push"
    push["actual_result"] = push["market_line"]
    combined = pd.concat([frame, push], ignore_index=True)
    model = fit_ftn_market_residual(combined, prop_type="receptions")
    assert model.training_rows == len(frame)
