from __future__ import annotations

"""Audit real-data FTN matchup-state coverage without fitting any coefficients."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from research.props.v2.props_ftn_matchup_state import (
    build_ftn_matchup_state,
    load_ftn_and_pbp,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--week", type=int, default=10)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.season > 2025:
        raise ValueError("coverage audit intentionally excludes completed 2026 data")
    if args.week < 2 or args.week > 18:
        raise ValueError("week must leave at least one prior-week observation")

    ftn, pbp = load_ftn_and_pbp([args.season])
    state, audit = build_ftn_matchup_state(
        ftn,
        pbp,
        season=args.season,
        week=args.week,
    )

    payload = {
        "promotion_authorized": False,
        "coefficients_fitted": False,
        "fair_lines_modified": False,
        "state_rows": int(len(state)),
        "teams_with_offense_history": int(
            state["ftn_off_games"].gt(0).sum() if not state.empty else 0
        ),
        "teams_with_defense_history": int(
            state["ftn_def_games"].gt(0).sum() if not state.empty else 0
        ),
        "audit": audit,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    state.to_csv(args.output_dir / "team_matchup_state.csv", index=False)
    (args.output_dir / "coverage.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
