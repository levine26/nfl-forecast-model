from __future__ import annotations

"""Run the preregistered LevLine Props empirical evaluation.

The runner is intentionally read-only with respect to forecast/history ledgers. It joins
immutable originals to later closing/result events and writes research-only evaluation
artifacts. Missing ledgers produce an explicit N=0 evidence report instead of synthetic data.
"""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nfl_forecast.props_evaluation import (  # noqa: E402
    BOOTSTRAP_REPLICATES,
    EVALUATION_CONTRACT_VERSION,
    evaluate_history,
)

DEFAULT_HISTORY = ROOT / "outputs" / "props" / "history"
DEFAULT_OUT = ROOT / "research_outputs" / "props_accuracy"


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{lineno}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"JSONL row must be an object at {path}:{lineno}")
        rows.append(value)
    return rows


def _fingerprint(path: Path) -> dict:
    if not path.exists():
        display = str(path)
        try:
            display = str(path.relative_to(ROOT))
        except ValueError:
            pass
        return {"path": display, "present": False, "sha256": None, "bytes": 0}
    raw = path.read_bytes()
    display = str(path)
    try:
        display = str(path.relative_to(ROOT))
    except ValueError:
        pass
    return {
        "path": display,
        "present": True,
        "sha256": sha256(raw).hexdigest(),
        "bytes": len(raw),
    }


def _pct(value):
    return "not measurable" if value is None else f"{100.0 * float(value):.1f}%"


def _number(value, digits=3):
    return "not measurable" if value is None else f"{float(value):.{digits}f}"


def _sample_line(sample: dict) -> str:
    return (
        f"N={int(sample.get('forecasts', 0))} forecasts, "
        f"{int(sample.get('unique_players', 0))} players, "
        f"{int(sample.get('unique_games', 0))} games, "
        f"{int(sample.get('unique_weeks', 0))} weeks"
    )


def _report(summary: dict, *, generated_utc: str) -> str:
    sample = summary["sample"]
    graded = summary["graded_sample"]
    continuous = summary["continuous"]
    probability = summary["probability"]
    market = summary["market_relative"]
    betting = summary["betting"]
    claims = summary["claim_readiness"]

    lines = [
        "# LevLine Props Accuracy — Current Evidence",
        "",
        f"Generated: {generated_utc}",
        f"Evaluation contract: {summary['evaluation_contract_version']}",
        f"Frozen model reference: {summary['frozen_model_ref']}",
        "",
        "## Plain-English findings",
        "",
    ]

    if graded.get("forecasts", 0) == 0:
        lines.extend(
            [
                "**There is not yet a legitimate empirical predictive-accuracy sample in the evaluated immutable repository history.** "
                "The evaluation found no graded frozen forecast receipts. Software tests and synthetic fixtures are therefore excluded from all accuracy claims.",
                "",
                f"Current sample: {_sample_line(sample)}; graded sample: {_sample_line(graded)}.",
                "",
                "- **How accurate are its Fair Lines?** Not yet measurable from frozen graded receipts.",
                "- **How well calibrated are its probabilities?** Not yet measurable.",
                "- **How does it compare with sportsbook markets?** Not yet measurable; no matched graded market sample is present.",
                "- **What is the MODEL EDGE record?** N=0 eligible graded MODEL EDGE bets in the evaluated history.",
                "- **What is its ROI?** Not measurable.",
                "- **Does it demonstrate positive CLV?** Not measurable.",
                "- **Which prop families look strongest and weakest?** No empirical ranking is supportable.",
                "- **How uncertain are these conclusions?** Maximally uncertain with respect to predictive performance because the graded sample is empty.",
                "- **What can we currently claim?** The engine is implemented with prospective immutability/leakage safeguards and is ready to accumulate evaluable evidence.",
                "- **What can we NOT currently claim?** Any hit rate, calibration quality, market superiority, positive CLV, profitable ROI, or strongest/weakest prop family.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"Current frozen-receipt sample: {_sample_line(sample)}; graded: {_sample_line(graded)}.",
                "",
                f"- **Fair Lines:** MAE = {_number(continuous.get('mae_fair_line'))}; "
                f"model-mean MAE = {_number(continuous.get('mae_model_mean'))}.",
                f"- **Probability quality:** Brier = {_number(probability.get('brier_model'), 4)}; "
                f"log loss = {_number(probability.get('log_loss_model'), 4)}; "
                f"ECE = {_number(probability.get('expected_calibration_error'), 4)}.",
                f"- **Sportsbook comparison:** paired Fair-Line minus original-market absolute-error difference = "
                f"{_number(market.get('paired_absolute_error_difference_fair_minus_market'))} "
                "(negative favors LevLine).",
                f"- **MODEL EDGE record:** {betting.get('wins', 0)}-{betting.get('losses', 0)}"
                f"-{betting.get('pushes', 0)} (W-L-P), status: {betting.get('status')}.",
                f"- **ROI:** {_pct(betting.get('roi'))}; net units = {_number(betting.get('net_units'))}.",
                f"- **Positive CLV:** threshold CLV mean = {_number(market.get('threshold_clv_mean'))}; "
                f"positive-CLV rate = {_pct(market.get('positive_threshold_clv_rate'))}.",
                "",
                "All estimates above must be interpreted with the displayed sample counts and clustered uncertainty intervals below. "
                "Subgroup differences are descriptive unless they satisfy the preregistered minimum-sample rules.",
                "",
            ]
        )

    lines.extend(
        [
            "## Claim readiness",
            "",
            f"- Projection-accuracy claim ready: **{claims['projection_accuracy']}**",
            f"- Calibration claim ready: **{claims['calibration']}**",
            f"- Market-superiority claim ready: **{claims['market_superiority']}**",
            f"- ROI claim ready: **{claims['roi']}**",
            "",
            "## Scientific metrics",
            "",
            "### Continuous projections",
            "",
            "~~~json",
            json.dumps(continuous, indent=2, sort_keys=True),
            "~~~",
            "",
            "### Probability quality and calibration",
            "",
            "~~~json",
            json.dumps(probability, indent=2, sort_keys=True),
            "~~~",
            "",
            "### Market-relative performance",
            "",
            "~~~json",
            json.dumps(market, indent=2, sort_keys=True),
            "~~~",
            "",
            "### Betting/signal performance",
            "",
            "~~~json",
            json.dumps(betting, indent=2, sort_keys=True),
            "~~~",
            "",
            "## Sample and provenance",
            "",
            f"- Overall: {_sample_line(sample)}",
            f"- Graded: {_sample_line(graded)}",
            f"- Forecast originals received: {summary['audit'].get('forecast_receipts_received', 0)}",
            f"- Closing events received: {summary['audit'].get('closing_events_received', 0)}",
            f"- Grade events received: {summary['audit'].get('grade_events_received', 0)}",
            "",
            "CRPS and PIT are intentionally not estimated unless the exact frozen simulation distribution is preserved. "
            "They are not approximated from mean/standard deviation.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate frozen LevLine Props forecast history.")
    parser.add_argument("--forecast-ledger", type=Path, default=DEFAULT_HISTORY / "forecast_originals.jsonl")
    parser.add_argument("--closing-ledger", type=Path, default=DEFAULT_HISTORY / "market_closes.jsonl")
    parser.add_argument("--grade-ledger", type=Path, default=DEFAULT_HISTORY / "grades.jsonl")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--frozen-model-ref",
        default="research/props-integration@db5478fd735ef0cad8fd1215e8b1fb6a96a3a21d",
    )
    parser.add_argument("--bootstrap-replicates", type=int, default=BOOTSTRAP_REPLICATES)
    args = parser.parse_args()

    if args.bootstrap_replicates <= 0:
        raise ValueError("--bootstrap-replicates must be positive")

    receipts = _read_jsonl(args.forecast_ledger)
    closes = _read_jsonl(args.closing_ledger)
    grades = _read_jsonl(args.grade_ledger)
    provenance = {
        "forecast_ledger": _fingerprint(args.forecast_ledger),
        "closing_ledger": _fingerprint(args.closing_ledger),
        "grade_ledger": _fingerprint(args.grade_ledger),
    }

    summary, detail = evaluate_history(
        receipts,
        closes,
        grades,
        frozen_model_ref=args.frozen_model_ref,
        source_provenance=provenance,
        bootstrap_replicates=args.bootstrap_replicates,
    )
    generated = datetime.now(timezone.utc).isoformat()
    summary["generated_utc"] = generated
    summary["evaluation_metadata"] = {
        "evaluation_contract_version": EVALUATION_CONTRACT_VERSION,
        "bootstrap_replicates": args.bootstrap_replicates,
        "bootstrap_seed": 20260917,
        "preregistration": "research/props/evaluation/PROPS_ACCURACY_EVALUATION_PREREGISTRATION.md",
        "synthetic_test_results_count_as_predictive_evidence": False,
    }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    detail.to_csv(args.output_dir / "forecast_level.csv", index=False)
    calibration = pd.DataFrame(summary["probability"].get("calibration", []))
    calibration.to_csv(args.output_dir / "calibration.csv", index=False)

    subgroup_rows: list[dict] = []
    for dimension, groups in summary["subgroups"].items():
        for value, metrics in groups.items():
            subgroup_rows.append(
                {
                    "dimension": dimension,
                    "value": value,
                    **{f"sample_{k}": v for k, v in metrics["sample"].items()},
                    **{f"continuous_{k}": v for k, v in metrics["continuous"].items()},
                    **{f"probability_{k}": v for k, v in metrics["probability"].items()},
                }
            )
    pd.DataFrame(subgroup_rows).to_csv(args.output_dir / "performance_by_family.csv", index=False)
    (args.output_dir / "report.md").write_text(
        _report(summary, generated_utc=generated),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "evaluation_contract_version": EVALUATION_CONTRACT_VERSION,
                "output_dir": str(args.output_dir),
                "sample": summary["sample"],
                "graded_sample": summary["graded_sample"],
                "claim_readiness": summary["claim_readiness"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
