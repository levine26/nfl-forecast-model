from __future__ import annotations

"""Write cumulative research-only prospective evaluation for frozen F-ST-01 locks."""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.challenger_prospective import evaluate_frozen_fst


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--shadow-history", default="challenger_outputs/prediction_history_shadow.csv")
    parser.add_argument("--output-dir", default="challenger_outputs/fst")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()

    history_path = Path(args.shadow_history)
    if not history_path.exists():
        raise SystemExit(f"Missing challenger shadow history: {history_path}")
    report, weekly = evaluate_frozen_fst(
        pd.read_csv(history_path),
        bootstrap_samples=args.bootstrap_samples,
    )
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "prospective_evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    weekly.to_csv(out / "prospective_weekly.csv", index=False)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
