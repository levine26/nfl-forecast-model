from __future__ import annotations

"""Run the research-only NGS next-game efficiency challenger on real nflverse data."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.props.v2.props_ngs_efficiency_model import (
    RESEARCH_LABEL,
    build_efficiency_learning_table,
    evaluate_rolling_origin,
)
from research.props.v2.props_ngs_efficiency_state import load_ngs_efficiency_history


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season-start", type=int, default=2020)
    parser.add_argument("--season-end", type=int, default=2025)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.season_start < 2016:
        raise ValueError("NGS research season_start must be >= 2016")
    if args.season_end > 2025:
        raise ValueError("completed 2026 outcomes are prohibited")
    if args.season_start > args.season_end:
        raise ValueError("season_start cannot exceed season_end")

    seasons = list(range(args.season_start, args.season_end + 1))
    raw = load_ngs_efficiency_history(seasons)
    table, audit = build_efficiency_learning_table(
        passing=raw["passing"],
        receiving=raw["receiving"],
        rushing=raw["rushing"],
        season_start=args.season_start,
        season_end=args.season_end,
    )
    evaluation = evaluate_rolling_origin(
        table,
        evaluation_seasons=tuple(
            season for season in (2024, 2025)
            if args.season_start <= season <= args.season_end
        ),
    )

    result = {
        "research_label": RESEARCH_LABEL,
        "promotion_authorized": False,
        "learning_table_audit": audit,
        "rolling_origin": evaluation,
        "interpretation_boundary": (
            "Efficiency-only retrospective development evidence. "
            "No Props Fair Line or production forecast is modified."
        ),
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(args.output_dir / "learning_table.csv", index=False)
    (args.output_dir / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    report = [
        "# LevLine Props 2.0 — NGS Efficiency Gate",
        "",
        "**RETROSPECTIVE CHALLENGER DEVELOPMENT — NOT PROMOTION EVIDENCE**",
        "",
    ]
    for season, metrics in evaluation["evaluation"].items():
        report.append(f"## {season}")
        report.append("")
        for metric, payload in metrics.items():
            if payload["status"] != "evaluated":
                report.append(
                    f"- {metric}: insufficient data "
                    f"(train={payload['training_rows']}, eval={payload['evaluation_rows']})"
                )
                continue
            m = payload["metrics"]
            report.append(
                f"- {metric}: baseline MAE {m['baseline_mae']:.4f}; "
                f"challenger MAE {m['challenger_mae']:.4f}; "
                f"improvement {m['mae_improvement']:.4f}; "
                f"95% player-cluster CI {m['mae_improvement_player_clustered_ci95']}"
            )
        report.append("")
    report.extend(
        [
            "This gate asks only whether lagged NGS context improves next-game efficiency "
            "prediction. Passing does not authorize integration into Fair Lines.",
            "",
        ]
    )
    (args.output_dir / "report.md").write_text("\n".join(report), encoding="utf-8")
    print((args.output_dir / "report.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
