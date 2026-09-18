from __future__ import annotations

"""Aggregate paired Props 2.0 latent dynamic-role V2 ablations.

Both route_only and full were frozen before outcome evaluation. This aggregator
reports them side-by-side and deliberately does not select a retrospective winner.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

CONTRACT_VERSION = "levline-props-v2-dynamic-role-development-v0.2.0"
BOOTSTRAP_SEED = 20260918
FROZEN_MODES = ("route_only", "full")


def implied_probability(american: float) -> float:
    value = float(american)
    if value < 0:
        return -value / (-value + 100.0)
    return 100.0 / (value + 100.0)


def no_vig_over(over: float, under: float) -> float:
    po = implied_probability(over)
    pu = implied_probability(under)
    return po / (po + pu)


def _prepare(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "contract_version", "role_mode", "game_id", "player_id", "prop_type",
        "market_line", "actual_result", "grading_result", "v1_grading_result",
        "fair_line", "v1_fair_line", "over_odds", "under_odds",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"challenger artifact missing fields: {sorted(missing)}")
    if set(frame["contract_version"].astype(str)) != {CONTRACT_VERSION}:
        raise ValueError("mixed or unexpected challenger contract version")
    modes = set(frame["role_mode"].astype(str))
    unknown = modes - set(FROZEN_MODES)
    if unknown:
        raise ValueError(f"unexpected role-mode result(s): {sorted(unknown)}")

    out = frame.copy()
    out = out[
        out["grading_result"].isin(["WIN", "LOSS"])
        & out["v1_grading_result"].isin(["WIN", "LOSS"])
    ].copy()
    out["challenger_correct"] = out["grading_result"].eq("WIN").astype(float)
    out["v1_correct"] = out["v1_grading_result"].eq("WIN").astype(float)
    out["market_outcome_recomputed"] = np.where(
        out["actual_result"] > out["market_line"],
        "OVER",
        np.where(out["actual_result"] < out["market_line"], "UNDER", "PUSH"),
    )
    out["market_no_vig_p_over"] = [
        no_vig_over(o, u) for o, u in zip(out["over_odds"], out["under_odds"])
    ]
    out["market_price_side"] = np.where(
        out["market_no_vig_p_over"] >= 0.5, "OVER", "UNDER"
    )
    out["market_price_correct"] = out["market_price_side"].eq(
        out["market_outcome_recomputed"]
    ).astype(float)
    return out


def _metrics(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {"n": 0}
    return {
        "n": int(len(frame)),
        "unique_games": int(frame["game_id"].astype(str).nunique()),
        "unique_players": int(frame["player_id"].astype(str).nunique()),
        "challenger_wins": int(frame["challenger_correct"].sum()),
        "v1_wins": int(frame["v1_correct"].sum()),
        "market_price_wins": int(frame["market_price_correct"].sum()),
        "challenger_accuracy": float(frame["challenger_correct"].mean()),
        "v1_accuracy": float(frame["v1_correct"].mean()),
        "market_price_direction_accuracy": float(frame["market_price_correct"].mean()),
        "challenger_minus_v1_accuracy": float(
            (frame["challenger_correct"] - frame["v1_correct"]).mean()
        ),
        "challenger_minus_market_accuracy": float(
            (frame["challenger_correct"] - frame["market_price_correct"]).mean()
        ),
        "challenger_fair_line_mae": float(
            np.mean(np.abs(frame["fair_line"] - frame["actual_result"]))
        ),
        "v1_fair_line_mae": float(
            np.mean(np.abs(frame["v1_fair_line"] - frame["actual_result"]))
        ),
        "sportsbook_line_mae": float(
            np.mean(np.abs(frame["market_line"] - frame["actual_result"]))
        ),
    }


def _cluster_bootstrap(frame: pd.DataFrame, replicates: int, seed: int) -> dict:
    games = np.asarray(sorted(frame["game_id"].astype(str).unique()))
    if len(games) < 2:
        return {
            "challenger_accuracy_ci95": [None, None],
            "challenger_minus_v1_ci95": [None, None],
            "challenger_minus_market_ci95": [None, None],
        }
    grouped = {game: frame[frame["game_id"].astype(str).eq(game)] for game in games}
    rng = np.random.default_rng(seed)
    acc = np.empty(replicates)
    dv1 = np.empty(replicates)
    dmkt = np.empty(replicates)
    for i in range(replicates):
        sampled = rng.choice(games, size=len(games), replace=True)
        boot = pd.concat([grouped[game] for game in sampled], ignore_index=True)
        acc[i] = boot["challenger_correct"].mean()
        dv1[i] = (boot["challenger_correct"] - boot["v1_correct"]).mean()
        dmkt[i] = (boot["challenger_correct"] - boot["market_price_correct"]).mean()
    interval = lambda x: [float(np.quantile(x, 0.025)), float(np.quantile(x, 0.975))]
    return {
        "challenger_accuracy_ci95": interval(acc),
        "challenger_minus_v1_ci95": interval(dv1),
        "challenger_minus_market_ci95": interval(dmkt),
    }


def _mode_summary(frame: pd.DataFrame, *, replicates: int, seed: int) -> dict:
    result = _metrics(frame)
    result.update(_cluster_bootstrap(frame, replicates, seed))
    result["by_season"] = {
        str(int(season)): _metrics(group)
        for season, group in frame.groupby("season", sort=True)
    }
    result["by_prop_type"] = {
        str(prop): _metrics(group)
        for prop, group in frame.groupby("prop_type", sort=True)
    }
    result["by_position"] = {
        str(position): _metrics(group)
        for position, group in frame.groupby("position", sort=True)
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    args = parser.parse_args()

    paths = sorted(args.input_dir.rglob("*_forecast_level.csv"))
    if not paths:
        raise ValueError("no challenger forecast-level artifacts found")
    frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    paired = _prepare(frame)

    by_mode = {}
    for index, mode in enumerate(FROZEN_MODES):
        group = paired[paired["role_mode"].astype(str).eq(mode)].copy()
        if group.empty:
            continue
        by_mode[mode] = _mode_summary(
            group,
            replicates=args.bootstrap_replicates,
            seed=BOOTSTRAP_SEED + index,
        )

    missing_modes = [mode for mode in FROZEN_MODES if mode not in by_mode]
    if missing_modes:
        raise ValueError(f"missing frozen role-mode result(s): {missing_modes}")

    summary = {
        "contract_version": CONTRACT_VERSION,
        "research_label": "RETROSPECTIVE CHALLENGER DEVELOPMENT - NOT PROMOTION EVIDENCE",
        "promotion_authorized": False,
        "frozen_ablation_modes": list(FROZEN_MODES),
        "retrospective_winner_selected": False,
        "by_role_mode": by_mode,
        "bootstrap": {
            "cluster": "game_id",
            "replicates": int(args.bootstrap_replicates),
            "seed_base": BOOTSTRAP_SEED,
        },
        "interpretation_boundary": (
            "route_only and full were frozen before outcome evaluation. Results are reported "
            "side-by-side and no retrospective winner is promoted or selected as the headline."
        ),
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    paired.to_csv(args.output_dir / "paired_rows.csv", index=False)

    report = [
        "# LevLine Props 2.0 — Latent Dynamic Role V2 Ablation",
        "",
        "**RETROSPECTIVE CHALLENGER DEVELOPMENT — NOT PROMOTION EVIDENCE**",
        "",
    ]
    for mode in FROZEN_MODES:
        h = by_mode[mode]
        report.extend([
            f"## {mode}",
            "",
            f"Paired decided props: {h['n']}",
            f"Unique games: {h['unique_games']}",
            f"Challenger accuracy: {100*h['challenger_accuracy']:.2f}%",
            f"Paired frozen-V1 accuracy: {100*h['v1_accuracy']:.2f}%",
            f"Opening-price direction accuracy: {100*h['market_price_direction_accuracy']:.2f}%",
            f"Challenger minus V1: {100*h['challenger_minus_v1_accuracy']:.2f} pp",
            f"Challenger minus market direction: {100*h['challenger_minus_market_accuracy']:.2f} pp",
            f"Challenger Fair-Line MAE: {h['challenger_fair_line_mae']:.3f}",
            f"V1 Fair-Line MAE: {h['v1_fair_line_mae']:.3f}",
            f"Sportsbook line MAE: {h['sportsbook_line_mae']:.3f}",
            f"Game-clustered accuracy 95% CI: {h['challenger_accuracy_ci95']}",
            f"Game-clustered challenger-minus-V1 95% CI: {h['challenger_minus_v1_ci95']}",
            "",
        ])
    report.extend([
        "No retrospective winner is selected. The ablation is diagnostic only and cannot "
        "authorize production because 2023–2025 outcomes were previously inspected.",
        "",
    ])
    (args.output_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print((args.output_dir / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
