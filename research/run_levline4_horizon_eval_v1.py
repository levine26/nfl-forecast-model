from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import pandas as pd

from research.levline4_horizon_eval_v1 import evaluate


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame()
    return pd.read_csv(path)


def run(
    *,
    shadow_path: str = "research_outputs/market_capture_v2/levline4_horizon_shadow.csv",
    prediction_history_path: str = "outputs/prediction_history.csv",
    report_path: str = "research_outputs/market_capture_v2/levline4_horizon_eval.json",
    status_path: str = "research_outputs/market_capture_v2/levline4_horizon_eval_status.json",
) -> dict:
    shadow_file = Path(shadow_path)
    history_file = Path(prediction_history_path)
    report_file = Path(report_path)
    status_file = Path(status_path)

    shadows = _read_csv(shadow_file)
    history = _read_csv(history_file)
    report = evaluate(shadows, history)
    generated = datetime.now(timezone.utc).isoformat()
    report["generated_at_utc"] = generated
    report["shadow_rows_available"] = int(len(shadows))
    report["official_history_rows_available"] = int(len(history))
    report["research_only"] = True
    report["production_authorized"] = False

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")

    status = {
        "status": "evaluated",
        "generated_at_utc": generated,
        "gate_status": report.get("gate_status"),
        "graded_shadow_rows": int(report.get("graded_shadow_rows", 0)),
        "shadow_rows_available": int(len(shadows)),
        "horizon_selection_authorized": False,
        "promotion_authorized": False,
        "production_authorized": False,
        "research_only": True,
    }
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status, indent=2, sort_keys=True), encoding="utf-8")
    return status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--shadow",
        default="research_outputs/market_capture_v2/levline4_horizon_shadow.csv",
    )
    parser.add_argument(
        "--prediction-history",
        default="outputs/prediction_history.csv",
    )
    parser.add_argument(
        "--report",
        default="research_outputs/market_capture_v2/levline4_horizon_eval.json",
    )
    parser.add_argument(
        "--status",
        default="research_outputs/market_capture_v2/levline4_horizon_eval_status.json",
    )
    args = parser.parse_args()
    result = run(
        shadow_path=args.shadow,
        prediction_history_path=args.prediction_history,
        report_path=args.report,
        status_path=args.status,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
