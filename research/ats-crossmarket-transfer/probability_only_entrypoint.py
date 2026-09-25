from __future__ import annotations

"""Lean entrypoint for the ATS cross-market transfer experiment.

The canonical historical-center builder also reconstructs fair margins and therefore refits
margin-regression sigmas. Cross-market transfer does not use that quantity. This entrypoint
reuses the exact same frozen F-ST historical frame and prior-only stack fitting while joining
only the probability and sportsbook fields required by the frozen experiment contract.
"""

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd

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


runner.hist.build_center_archive = build_probability_archive

if __name__ == "__main__":
    runner.main()
