from __future__ import annotations

"""Real-data FTN source preflight that stops before model fitting or evaluation.

This job exists to validate the preregistered data plumbing against the actual 2022-2025
source domains without viewing a held-out model result. It uses the corrected exact-key
identity gate, verifies source-game schedule chronology coverage, and builds team-game
aggregates. No candidate probabilities are fit or scored.
"""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from research.ftn_identity_v1 import join_ftn_to_pbp
from research.ftn_process_v1 import aggregate_ftn_team_games
from research.run_ftn_process_v1 import _load_inputs

DEFAULT_OUTPUT = Path("research_outputs/ftn_source_preflight_v1/audit.json")


def _safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def run(config_path: str = "config/model.yaml", output_path: str | Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    ftn, pbp, schedule_scope, evaluation_games = _load_inputs(config_path)
    joined, identity_audit = join_ftn_to_pbp(ftn, pbp)

    schedule_ids = set(schedule_scope["game_id"].astype(str))
    joined_ids = set(joined["nflverse_game_id"].astype(str))
    missing_schedule_ids = sorted(joined_ids - schedule_ids)

    audit: dict[str, Any] = {
        "schema_version": "ftn-source-preflight-v1",
        "experiment_id": "FTN-PROCESS-01",
        "stage": "real_source_preflight_before_model_fit",
        "identity_audit": identity_audit,
        "ftn_rows": int(len(ftn)),
        "pbp_rows": int(len(pbp)),
        "eligible_joined_rows": int(len(joined)),
        "joined_source_games": int(len(joined_ids)),
        "schedule_scope_games": int(len(schedule_scope)),
        "market_evaluation_games": int(len(evaluation_games)),
        "missing_schedule_game_count": int(len(missing_schedule_ids)),
        "missing_schedule_game_ids_sample": missing_schedule_ids[:25],
        "model_fit": False,
        "historical_evaluation_executed": False,
        "completed_2026_outcomes_used": 0,
        "production_authorized": False,
    }

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if missing_schedule_ids:
        audit["status"] = "failed_schedule_identity"
        out.write_text(json.dumps(_safe(audit), indent=2, sort_keys=True) + "\n", encoding="utf-8")
        raise RuntimeError(
            f"FTN source preflight found {len(missing_schedule_ids)} source games outside preregistered 2022-2025 REG/POST schedule scope"
        )

    team_games = aggregate_ftn_team_games(joined, schedule_scope)
    audit.update(
        {
            "status": "passed",
            "team_game_rows": int(len(team_games)),
            "team_game_unique_source_games": int(team_games["game_id"].nunique()),
            "team_game_unique_teams": int(team_games["team"].nunique()),
            "team_game_missing_kickoff_rows": int(team_games["source_game_kickoff_utc"].isna().sum()),
            "team_game_missing_availability_rows": int(team_games["available_at_utc"].isna().sum()),
        }
    )
    out.write_text(json.dumps(_safe(audit), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(_safe(audit), indent=2, sort_keys=True))
    if audit["team_game_missing_kickoff_rows"] or audit["team_game_missing_availability_rows"]:
        raise RuntimeError("FTN source preflight produced team-game rows without chronology/availability")
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/model.yaml")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    run(config_path=args.config, output_path=args.output)


if __name__ == "__main__":
    main()
