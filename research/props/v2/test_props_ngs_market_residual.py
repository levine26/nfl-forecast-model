import numpy as np
import pandas as pd

from research.props.v2.props_ngs_market_residual import (
    FEATURES_BY_PROP,
    add_market_features,
    apply_ngs_market_residual,
    fit_ngs_market_residual,
)


def _training(prop_type: str, n: int = 160) -> pd.DataFrame:
    rows = []
    ngs_columns = FEATURES_BY_PROP[prop_type]
    for i in range(n):
        signal = 1.0 if i % 4 in {0, 1} else -1.0
        line = 50.5
        actual = 62.0 if signal > 0 else 39.0
        row = {
            "game_id": f"g{i // 4}",
            "player_id": f"p{i}",
            "prop_type": prop_type,
            "over_odds": -110,
            "under_odds": -110,
            "p_over": 0.53 if signal > 0 else 0.47,
            "market_line": line,
            "actual_result": actual,
        }
        for j, column in enumerate(ngs_columns):
            row[column] = signal * (1.0 + j / 10.0)
        rows.append(row)
    return pd.DataFrame(rows)


def test_market_features_are_finite_and_gap_is_zero_when_probabilities_match():
    frame = pd.DataFrame(
        [{
            "over_odds": -110,
            "under_odds": -110,
            "p_over": 0.5,
        }]
    )
    out = add_market_features(frame)
    assert abs(out.loc[0, "market_no_vig_p_over"] - 0.5) < 1e-12
    assert abs(out.loc[0, "levline_market_logit_gap"]) < 1e-12


def test_fit_is_deterministic_and_uses_fixed_market_offset():
    frame = _training("receiving_yards")
    first = fit_ngs_market_residual(frame, prop_type="receiving_yards")
    second = fit_ngs_market_residual(frame, prop_type="receiving_yards")
    assert first.training_rows == len(frame)
    assert first.training_games == frame["game_id"].nunique()
    assert np.allclose(first.coefficients, second.coefficients)
    assert np.isclose(first.intercept, second.intercept)
    scored = apply_ngs_market_residual(frame.drop(columns=["actual_result"]), {"receiving_yards": first})
    assert scored["ngs_challenger_p_over"].between(0, 1).all()
    assert set(scored["ngs_challenger_side"].dropna()) <= {"OVER", "UNDER"}


def test_missing_ngs_evidence_is_not_zero_performance():
    train = _training("rushing_yards")
    model = fit_ngs_market_residual(train, prop_type="rushing_yards")
    prediction = train.iloc[[0]].drop(columns=["actual_result"]).copy()
    for column in FEATURES_BY_PROP["rushing_yards"]:
        prediction[column] = np.nan
    scored = apply_ngs_market_residual(prediction, {"rushing_yards": model})
    assert np.isfinite(scored.iloc[0]["ngs_challenger_p_over"])
    missing_names = [name for name in model.transformed_feature_names if name.endswith("__missing")]
    assert missing_names


def test_pushes_are_excluded_from_training_count():
    frame = _training("passing_yards")
    push = frame.iloc[[0]].copy()
    push["player_id"] = "push"
    push["actual_result"] = push["market_line"]
    combined = pd.concat([frame, push], ignore_index=True)
    model = fit_ngs_market_residual(combined, prop_type="passing_yards")
    assert model.training_rows == len(frame)
