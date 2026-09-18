from __future__ import annotations

"""Aggregate the preregistered 2023-2025 LevLine Props historical backtest.

This script performs no model selection and no threshold tuning. It only combines
season outputs produced under levline-props-historical-directional-v1.0.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from run_historical_directional_backtest import (
    CONTRACT_VERSION,
    clustered_accuracy_interval,
    summarize,
)

PRIMARY_SEASONS = (2023, 2024, 2025)
EXPECTED_SIMULATIONS = 20_000
PRIMARY_BOOK_ID = 30
FROZEN_MODEL_REF = "research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d"


def _load(input_dir: Path) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    seen: set[int] = set()
    for season in PRIMARY_SEASONS:
        matches = sorted(input_dir.rglob(f"{season}_forecast_level.csv"))
        if len(matches) != 1:
            raise RuntimeError(
                f"expected exactly one {season}_forecast_level.csv under {input_dir}, got {len(matches)}"
            )
        frame = pd.read_csv(matches[0])
        if frame.empty:
            raise RuntimeError(f"{season} forecast-level output is empty")
        if "season" not in frame.columns:
            raise RuntimeError(f"{season} output missing season column")
        values = set(pd.to_numeric(frame["season"], errors="coerce").dropna().astype(int))
        if values != {season}:
            raise RuntimeError(f"{season} file contains unexpected season values: {sorted(values)}")
        seen.add(season)
        frames.append(frame)

    if seen != set(PRIMARY_SEASONS):
        raise RuntimeError(f"missing primary seasons: {sorted(set(PRIMARY_SEASONS) - seen)}")

    combined = pd.concat(frames, ignore_index=True)
    required = {
        "contract_version",
        "season",
        "week",
        "game_id",
        "player_id",
        "position",
        "prop_type",
        "book_id",
        "market_line",
        "fair_line",
        "actual_result",
        "model_side",
        "market_outcome",
        "grading_result",
        "simulations",
        "prior_trained_through",
    }
    missing = required - set(combined.columns)
    if missing:
        raise RuntimeError(f"combined output missing fields: {sorted(missing)}")

    contracts = set(combined["contract_version"].dropna().astype(str))
    if contracts != {CONTRACT_VERSION}:
        raise RuntimeError(f"unexpected historical contract(s): {sorted(contracts)}")

    books = set(pd.to_numeric(combined["book_id"], errors="coerce").dropna().astype(int))
    if books != {PRIMARY_BOOK_ID}:
        raise RuntimeError(f"primary aggregate requires genuine OPEN book 30 only, got {sorted(books)}")

    simulations = set(
        pd.to_numeric(combined["simulations"], errors="coerce").dropna().astype(int)
    )
    if simulations != {EXPECTED_SIMULATIONS}:
        raise RuntimeError(
            f"primary aggregate requires {EXPECTED_SIMULATIONS} simulations/game, got {sorted(simulations)}"
        )

    for season in PRIMARY_SEASONS:
        rows = combined[pd.to_numeric(combined["season"], errors="coerce").eq(season)]
        horizons = set(
            pd.to_numeric(rows["prior_trained_through"], errors="coerce")
            .dropna()
            .astype(int)
        )
        if horizons != {season - 1}:
            raise RuntimeError(
                f"{season} prior horizon must be {season - 1}, got {sorted(horizons)}"
            )

    identity = ["season", "game_id", "player_id", "prop_type"]
    if combined.duplicated(identity).any():
        dupes = int(combined.duplicated(identity).sum())
        raise RuntimeError(f"combined primary sample contains {dupes} duplicate forecast identities")

    return combined


def _grouped(frame: pd.DataFrame, column: str) -> dict:
    if frame.empty:
        return {}
    return {
        str(key): summarize(group)
        for key, group in frame.groupby(column, dropna=False, sort=True)
    }


def aggregate(input_dir: Path) -> tuple[pd.DataFrame, dict]:
    combined = _load(input_dir)
    primary = summarize(combined)
    decided = combined[combined["grading_result"].isin(["WIN", "LOSS"])].copy()
    seasons_present = sorted(
        set(pd.to_numeric(decided["season"], errors="coerce").dropna().astype(int))
    )
    coverage = {
        "minimum_nonpush_calls": 1000,
        "minimum_unique_games": 100,
        "required_seasons": list(PRIMARY_SEASONS),
        "nonpush_calls": int(
            decided["grading_result"].isin(["WIN", "LOSS"]).sum()
        ),
        "unique_games": int(decided["game_id"].nunique()),
        "seasons_present": seasons_present,
    }
    coverage["passes"] = bool(
        coverage["nonpush_calls"] >= coverage["minimum_nonpush_calls"]
        and coverage["unique_games"] >= coverage["minimum_unique_games"]
        and seasons_present == list(PRIMARY_SEASONS)
    )

    sensitivity_2425 = combined[
        pd.to_numeric(combined["season"], errors="coerce").isin([2024, 2025])
    ].copy()

    output = {
        "contract_version": CONTRACT_VERSION,
        "frozen_model_ref": FROZEN_MODEL_REF,
        "primary_window": "2023-2025 regular seasons, Weeks 1-18",
        "market_source": "Action Network genuine OPEN (book_id=30, inferred opens excluded)",
        "simulations_per_game": EXPECTED_SIMULATIONS,
        "headline": primary,
        "clustered_accuracy_ci95": clustered_accuracy_interval(combined),
        "coverage_rule": coverage,
        "by_season": _grouped(combined, "season"),
        "by_prop": _grouped(combined, "prop_type"),
        "by_position": _grouped(combined, "position"),
        "by_side": _grouped(combined, "model_side"),
        "sensitivity_2024_2025": {
            "headline": summarize(sensitivity_2425),
            "clustered_accuracy_ci95": clustered_accuracy_interval(sensitivity_2425),
        },
        "audit": {
            "rows_combined": int(len(combined)),
            "decided_nonpush_rows": int(len(decided)),
            "unique_games_all_qualified": int(combined["game_id"].nunique()),
            "unique_players_all_qualified": int(combined["player_id"].nunique()),
            "seasons": list(PRIMARY_SEASONS),
            "no_posthoc_threshold": True,
            "no_model_selection_from_outcomes": True,
            "winner_model_modified": False,
        },
    }
    return combined, output


def _pct(value) -> str:
    return "N/A" if value is None else f"{100.0 * float(value):.2f}%"


def _report(payload: dict) -> str:
    h = payload["headline"]
    ci = payload["clustered_accuracy_ci95"]
    wilson = h.get("wilson95") or [None, None]
    lines = [
        "# LevLine Props Accuracy — 2023–2025 Historical Evidence",
        "",
        f"**Directional accuracy: {_pct(h.get('accuracy'))} "
        f"({h.get('wins', 0)} wins / {h.get('wins', 0) + h.get('losses', 0)} decided non-push props).**",
        "",
        f"- Losses: {h.get('losses', 0)}",
        f"- Pushes excluded: {h.get('pushes', 0)}",
        f"- No-calls excluded: {h.get('no_calls', 0)}",
        f"- Unique games: {h.get('unique_games', 0)}",
        f"- Unique players: {h.get('unique_players', 0)}",
        f"- Wilson 95% interval: {_pct(wilson[0])} to {_pct(wilson[1])}",
        f"- Game-clustered 95% interval: {_pct(ci[0])} to {_pct(ci[1])}",
        f"- Fair-Line MAE: {h.get('mean_abs_fair_line_error')}",
        f"- Market-line MAE: {h.get('mean_abs_market_line_error')}",
        f"- Majority-side naive accuracy: {_pct(h.get('majority_side_naive_accuracy'))}",
        f"- Trailing-5 baseline accuracy: {_pct(h.get('l5_baseline_accuracy'))} "
        f"(N={h.get('l5_baseline_n', 0)})",
        f"- Genuine-OPEN coverage rule passed: {payload['coverage_rule']['passes']}",
        "",
        "## By season",
        "",
    ]
    for season, row in payload["by_season"].items():
        lines.append(
            f"- {season}: {_pct(row.get('accuracy'))} "
            f"({row.get('wins',0)}/{row.get('wins',0)+row.get('losses',0)} decided)"
        )
    lines.extend(["", "## By prop family", ""])
    for prop, row in payload["by_prop"].items():
        lines.append(
            f"- {prop}: {_pct(row.get('accuracy'))} "
            f"({row.get('wins',0)}/{row.get('wins',0)+row.get('losses',0)} decided)"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "This is a preregistered historical out-of-sample reconstruction of the frozen "
            "LevLine Props Research Beta, not prospective 2026 evidence. It uses real "
            "Action Network genuine opening thresholds, strict lagged football state, "
            "prior-season structural prior fits, and postgame snaps only for grading/void logic.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    combined, payload = aggregate(args.input_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    combined.to_csv(args.output_dir / "2023_2025_forecast_level.csv", index=False)
    (args.output_dir / "2023_2025_summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "2023_2025_report.md").write_text(
        _report(payload),
        encoding="utf-8",
    )
    print(json.dumps(payload["headline"], indent=2, default=str))
    print(json.dumps({"clustered_accuracy_ci95": payload["clustered_accuracy_ci95"]}, indent=2))
    print(json.dumps({"coverage_rule": payload["coverage_rule"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
