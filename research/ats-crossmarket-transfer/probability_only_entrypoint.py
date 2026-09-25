from __future__ import annotations

"""Lean, numerically equivalent entrypoint for ATS cross-market transfer.

It avoids unrelated historical fair-margin reconstruction and accelerates the frozen
mean-preserving KL projection by vectorizing the Student-t integer lattice and caching the
baseline support once per game. The statistical contract, constraints and tolerances are
unchanged.
"""

import importlib.util
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd
from scipy.stats import t as student_t

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("ats_crossmarket_runner", ROOT / "run_experiment.py")
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load cross-market runner")
runner = importlib.util.module_from_spec(SPEC)
sys.modules["ats_crossmarket_runner"] = runner
SPEC.loader.exec_module(runner)


def build_probability_archive(games: pd.DataFrame):
    frozen = runner.hist.load_frozen_training_frame()
    frozen["season"] = pd.to_numeric(frozen["season"], errors="raise").astype(int)
    if frozen["season"].ge(2026).any():
        raise runner.CrossMarketError("frozen F-ST training frame contains 2026 outcomes")

    game_cols = [
        "game_id", "season", "week", "gameday", "home_team", "away_team",
        "actual_margin", "spread_line", "total_line", "market_margin",
    ]
    parts = []
    coverage = {}
    fst_receipts = {}
    for season in range(int(runner.CONFIG["inner_archive_first_season"]), max(runner.OUTER) + 1):
        probs, fst_receipt = runner.hist.fit_fst_fold(frozen, season)
        target = frozen[frozen["season"] == season].copy().reset_index(drop=True)
        if len(target) != len(probs):
            raise runner.CrossMarketError(f"F-ST probability alignment failed for {season}")
        target["fst_home_prob"] = np.asarray(probs, dtype=float)
        season_games = games[games["season"] == season][game_cols].copy()
        joined = target.merge(
            season_games,
            on=["game_id", "season"],
            how="inner",
            validate="one_to_one",
        )
        required = [
            "actual_margin", "spread_line", "total_line", "market_margin",
            "market_prob", "pure_prob", "fst_home_prob", "home_win",
        ]
        mask = pd.Series(True, index=joined.index)
        for col in required:
            vals = pd.to_numeric(joined[col], errors="coerce").to_numpy(dtype=float)
            mask &= np.isfinite(vals)
        common = joined[mask].copy()
        common["actual_margin"] = pd.to_numeric(common["actual_margin"], errors="raise").astype(int)
        parts.append(common)
        coverage[str(season)] = {
            "frozen_fst_rows": int(len(target)),
            "historical_game_rows": int(len(season_games)),
            "joined_rows": int(len(joined)),
            "common_rows": int(len(common)),
        }
        fst_receipts[str(season)] = fst_receipt

    archive = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    if archive["season"].ge(2026).any():
        raise runner.CrossMarketError("2026 outcome entered probability archive")
    return archive, {"coverage_by_season": coverage, "probability_only": True}, fst_receipts


_SUPPORT_CACHE: dict[tuple, tuple[np.ndarray, np.ndarray, float]] = {}


def fast_adaptive_support(parts: dict) -> tuple[np.ndarray, np.ndarray, float]:
    key = (
        float(parts["loc"]), float(parts["sigma"]), float(parts["nu"]),
        tuple(float(x) for x in parts["key"]),
    )
    cached = _SUPPORT_CACHE.get(key)
    if cached is not None:
        return cached

    bound = int(runner.CONFIG["initial_support_bound"])
    max_bound = int(runner.CONFIG["maximum_support_bound"])
    while True:
        left = float(runner.v2.m4_leq(-bound - 1, parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
        right = float(1.0 - runner.v2.m4_leq(bound, parts["loc"], parts["sigma"], parts["nu"], parts["key"]))
        tail = left + right
        if tail < runner.TAIL_TOL:
            break
        bound *= 2
        if bound > max_bound:
            raise runner.CrossMarketError(f"adaptive support failed tail tolerance: {tail}")

    margins = np.arange(-bound, bound + 1, dtype=int)
    loc = float(parts["loc"])
    sigma = float(parts["sigma"])
    nu = float(parts["nu"])
    upper = student_t.cdf((margins.astype(float) + 0.5 - loc) / sigma, df=nu)
    lower = student_t.cdf((margins.astype(float) - 0.5 - loc) / sigma, df=nu)
    base = np.maximum(0.0, upper - lower)
    g0, g3, g7 = (float(x) for x in parts["key"])
    weight = np.ones(len(margins), dtype=float)
    weight[margins == 0] = math.exp(g0)
    weight[np.abs(margins) == 3] = math.exp(g3)
    weight[np.abs(margins) == 7] = math.exp(g7)
    z = float(runner.v2.m4_normalizer(loc, sigma, nu, parts["key"]))
    q = base * weight / z
    if not np.isfinite(q).all() or (q < 0).any():
        raise runner.CrossMarketError("invalid vectorized adaptive support")
    result = (margins, q, float(tail))
    _SUPPORT_CACHE[key] = result
    return result


runner.hist.build_center_archive = build_probability_archive
runner._adaptive_support = fast_adaptive_support

if __name__ == "__main__":
    runner.main()
