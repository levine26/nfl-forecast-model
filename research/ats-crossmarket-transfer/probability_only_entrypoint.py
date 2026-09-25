from __future__ import annotations

"""Lean, numerically equivalent entrypoint for ATS cross-market transfer.

This experiment needs only historical schedule/results/spread/total plus the immutable
F-ST probability archive. It deliberately avoids loading PBP/team-feature data that do
not enter any ATS-XM candidate. The resulting regular-season historical identity is
hard-gated to the accepted #582 game universe. Mean-preserving KL projection is also
accelerated by vectorizing the Student-t integer lattice and caching baseline support.
The statistical contract, constraints and tolerances are unchanged.
"""

from hashlib import sha256
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

# Canonical historical-game identity from accepted PR #582 execution artifact.
ACCEPTED_HISTORICAL_GAME_IDS_SHA256 = "26aed1cdeb34d0381e1af3fbc4e00a14360330861ad04ecc5c244635b8e0b156"


def build_schedule_only_historical_games() -> tuple[pd.DataFrame, dict]:
    """Reproduce the accepted regular-season historical ATS scaffold without PBP."""
    model_cfg = runner.hist.load_config(str(runner.hist.REPO_ROOT / "config" / "model.yaml"))
    start = int(model_cfg["data"]["core_start_season"])
    max_season = 2025
    schedules = pd.read_csv(
        "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv",
        low_memory=False,
    )
    schedules["season"] = pd.to_numeric(schedules["season"], errors="coerce")
    schedules["week"] = pd.to_numeric(schedules["week"], errors="coerce")
    games = schedules[schedules["season"].between(start, max_season, inclusive="both")].copy()
    if "game_type" in games.columns:
        games = games[games["game_type"].eq("REG")].copy()
    games = games[games["home_score"].notna() & games["away_score"].notna()].copy()
    if games.empty or games["season"].ge(2026).any():
        raise runner.CrossMarketError("schedule-only historical frame violated 2025 cutoff")

    games["home_win"] = (pd.to_numeric(games["home_score"], errors="raise") > pd.to_numeric(games["away_score"], errors="raise")).astype(float)
    margin = pd.to_numeric(games["home_score"], errors="raise") - pd.to_numeric(games["away_score"], errors="raise")
    if not np.allclose(margin.to_numpy(dtype=float), np.round(margin.to_numpy(dtype=float)), atol=1e-9):
        raise runner.CrossMarketError("non-integer NFL final margin in schedule-only frame")
    games["actual_margin"] = np.round(margin).astype(int)
    games["spread_line"] = pd.to_numeric(games["spread_line"], errors="coerce")
    games["total_line"] = pd.to_numeric(games["total_line"], errors="coerce")
    games["market_margin"] = runner.v2.market_margin(games["spread_line"])

    ids = sorted(games["game_id"].astype(str).tolist())
    identity_hash = sha256(("\n".join(ids) + "\n").encode("utf-8")).hexdigest()
    if identity_hash != ACCEPTED_HISTORICAL_GAME_IDS_SHA256:
        raise runner.CrossMarketError(
            f"schedule-only historical identity drift: {identity_hash} != {ACCEPTED_HISTORICAL_GAME_IDS_SHA256}"
        )
    identity = {
        "requested_seasons": list(range(start, max_season + 1)),
        "historical_rows": int(len(games)),
        "completed_rows": int(len(games)),
        "first_season": int(games["season"].min()),
        "last_season": int(games["season"].max()),
        "completed_2026_rows": 0,
        "game_ids_sha256": identity_hash,
        "schedule_only": True,
        "accepted_582_identity_match": True,
    }
    return games, identity


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
    expected_common = {"2021": 272, "2022": 271, "2023": 272, "2024": 272, "2025": 272}
    observed_common = {k: int(v["common_rows"]) for k, v in coverage.items()}
    if observed_common != expected_common:
        raise runner.CrossMarketError(f"common-row drift versus accepted #582 archive: {observed_common}")
    return archive, {
        "coverage_by_season": coverage,
        "probability_only": True,
        "accepted_582_common_rows_match": True,
    }, fst_receipts


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


runner.hist.build_historical_games = build_schedule_only_historical_games
runner.hist.build_center_archive = build_probability_archive
runner._adaptive_support = fast_adaptive_support

if __name__ == "__main__":
    runner.main()
