"""Research-only frozen-vs-chronological F-ST population and tie audit.

No model refit, production state, 2026 outcomes, or candidate selection.
"""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from nfl_forecast.fst_nested_pure import load_frozen_training_frame
from nfl_forecast.fst_production import load_fst_artifact, frozen_fst_probability
from research.post_week4_phase3.run_candidates import frozen_panel

KNOWN_TIES = {
    "2022_01_IND_HOU": "IND 20 at HOU 20",
    "2022_13_WAS_NYG": "WAS 20 at NYG 20",
    "2025_04_GB_DAL": "GB 40 at DAL 40",
}
SEASONS = (2022, 2023, 2024, 2025)
FIRST = 2022


def audit() -> dict:
    panel = frozen_panel()
    target = panel[panel.season.isin(SEASONS)].copy()
    artifact = load_fst_artifact()
    frozen = load_frozen_training_frame()
    keyed = frozen[["game_id", "market_prob", "pure_prob", "home_win"]].copy()
    pred = frozen_fst_probability(
        keyed.market_prob.to_numpy(dtype=float),
        keyed.pure_prob.to_numpy(dtype=float),
        artifact,
    )
    frozen_prob = pd.DataFrame({"game_id": keyed.game_id.astype(str), "fixed_prob": pred})
    joined = target.merge(frozen_prob[["game_id", "fixed_prob"]], on="game_id", validate="one_to_one")
    if len(joined) != 1087 or joined.game_id.duplicated().any():
        raise RuntimeError("Frozen baseline identity or size mismatch")
    y = joined.home_win.to_numpy(int)
    summary = {}
    for name, col in [("season_forward", "fst_prob"), ("frozen_final_coefficients", "fixed_prob")]:
        prob = joined[col].to_numpy(dtype=float)
        correct = (prob >= .5) == y
        summary[name] = {
            "correct": int(correct.sum()),
            "games": int(len(joined)),
            "weeks_1_4": {"correct": int(correct[joined.week.le(4).to_numpy()].sum()),
                          "games": int(joined.week.le(4).sum())},
            "weeks_1_6": {"correct": int(correct[joined.week.le(6).to_numpy()].sum()),
                          "games": int(joined.week.le(6).sum())},
            "by_season": {
                str(s): {"correct": int(correct[joined.season.eq(s).to_numpy()].sum()),
                         "games": int(joined.season.eq(s).sum())}
                for s in SEASONS
            },
        }
    if summary["season_forward"]["correct"] != 741 or summary["frozen_final_coefficients"]["correct"] != 740:
        raise RuntimeError("Frozen F-ST comparator no longer matches prior verified evidence")

    tie_frame = joined[joined.game_id.isin(KNOWN_TIES)].sort_values("game_id")
    if len(tie_frame) != len(KNOWN_TIES) or not tie_frame.home_win.eq(0).all():
        raise RuntimeError("Tied-game label identity changed")
    ties = []
    for r in tie_frame.itertuples():
        ties.append({
            "game_id": r.game_id,
            "real_final": KNOWN_TIES[r.game_id],
            "legacy_home_win": int(r.home_win),
            "season_forward_home_prob": float(r.fst_prob),
            "frozen_final_home_prob": float(r.fixed_prob),
            "wrongly_credited_as_away_win": bool(r.fst_prob < .5 and r.fixed_prob < .5),
        })
    ties_in_training = sorted(set(KNOWN_TIES) & set(frozen.game_id.astype(str)))
    strict = joined[~joined.game_id.isin(KNOWN_TIES)].copy()
    strict_y = strict.home_win.to_numpy(int)
    summary["static_exclude_ties_no_refit"] = {
        col: {"correct": int(((strict[col].to_numpy(dtype=float) >= .5) == strict_y).sum()),
              "games": int(len(strict))}
        for col in ("fst_prob", "fixed_prob")
    }
    return {
        "contract": "research_only_legacy_label_reconciliation",
        "outcomes_2026_used": 0,
        "authoritative_frozen_artifact_training_digest": artifact.training_data_sha256,
        "historical_training_rows": len(frozen),
        "paired_games": len(joined),
        "baseline_definitions": summary,
        "three_known_ties": ties,
        "tied_game_ids_in_training": ties_in_training,
        "source_limitation": "Three listed ties are known game keys; full all-year tie inventory requires official complete scoreboard crosscheck.",
        "interpretation": "Season-forward and frozen-final-coefficient F-ST are different estimands; static tie exclusion is not a retrained tie-excluded OOS result.",
        "production_changed": False,
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = audit()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result["baseline_definitions"][k] for k in
                      ("season_forward", "frozen_final_coefficients")}, indent=2))


if __name__ == "__main__":
    main()
