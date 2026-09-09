from __future__ import annotations

import numpy as np
import pandas as pd


def american_to_implied(odds: pd.Series) -> pd.Series:
    x = pd.to_numeric(odds, errors="coerce")
    return pd.Series(np.where(x < 0, (-x) / ((-x) + 100.0), 100.0 / (x + 100.0)), index=odds.index)


def add_vig_free_market_prob(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if not {"home_moneyline","away_moneyline"}.issubset(out.columns):
        out["market_home_prob"] = np.nan
        return out
    hp = american_to_implied(out["home_moneyline"])
    ap = american_to_implied(out["away_moneyline"])
    out["market_home_prob"] = hp / (hp + ap)
    return out
