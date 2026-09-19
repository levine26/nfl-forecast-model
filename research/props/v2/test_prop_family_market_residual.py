import pandas as pd

from research.props.v2.props_market_residual import (
    apply_market_prior_residual,
    fit_market_prior_residual,
    grade_directional_rows,
)


def _ledger():
    rows=[]
    props=["passing_yards","passing_tds","rushing_yards","receiving_yards","receptions"]
    for p_index, prop in enumerate(props):
        for i in range(80):
            over = (i + p_index) % 3 != 0
            rows.append({
                "season": 2023,
                "week": 1 + (i % 9),
                "game_id": f"g{p_index}_{i//4}",
                "player_id": f"p{p_index}_{i}",
                "prop_type": prop,
                "market_line": 50.5,
                "over_odds": -110,
                "under_odds": -110,
                "p_over": 0.58 if over else 0.42,
                "model_side": "OVER" if over else "UNDER",
                "actual_result": 60.0 if over else 40.0,
            })
    return pd.DataFrame(rows)


def test_each_family_can_fit_independently_without_cross_family_rows():
    data=_ledger()
    for prop, rows in data.groupby("prop_type"):
        model=fit_market_prior_residual(rows)
        assert model.training_rows == len(rows)
        assert model.training_games == rows["game_id"].nunique()
        scored=grade_directional_rows(apply_market_prior_residual(rows, model))
        assert scored["challenger_correct"].notna().all()
        assert set(scored["prop_type"]) == {prop}


def test_family_models_can_have_different_parameters():
    data=_ledger()
    # Make passing TD outcomes oppose V1 while receptions reinforce V1.
    td=data["prop_type"].eq("passing_tds")
    data.loc[td, "actual_result"] = data.loc[td, "market_line"].where(
        data.loc[td, "model_side"].eq("OVER"), 60.0
    )
    data.loc[td & data["model_side"].eq("OVER"), "actual_result"] = 40.0
    data.loc[td & data["model_side"].eq("UNDER"), "actual_result"] = 60.0
    a=fit_market_prior_residual(data[data["prop_type"].eq("passing_tds")])
    b=fit_market_prior_residual(data[data["prop_type"].eq("receptions")])
    assert abs(a.residual_beta - b.residual_beta) > 0.01
