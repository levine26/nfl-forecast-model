from __future__ import annotations

"""Build research-only expected-lineup impact outputs from an explicit pregame input file."""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.player_impact_engine import (
    build_expected_lineup_impacts,
    build_game_matchup_context,
)


def run(input_path: str, output_dir: str, schedules_path: str | None = None) -> dict:
    source = Path(input_path)
    if not source.exists():
        raise RuntimeError(f"Expected-lineup input does not exist: {source}")
    expected_lineup = pd.read_csv(source)
    build = build_expected_lineup_impacts(expected_lineup)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    build.player_impacts.to_csv(out / "player_impacts.csv", index=False)
    build.unit_impacts.to_csv(out / "unit_impacts.csv", index=False)
    build.team_impacts.to_csv(out / "team_impacts.csv", index=False)

    matchup_rows = 0
    if schedules_path is not None:
        schedules = pd.read_csv(schedules_path)
        matchup = build_game_matchup_context(schedules, build.team_impacts)
        matchup.to_csv(out / "game_matchup_context.csv", index=False)
        matchup_rows = int(len(matchup))

    audit = {
        **build.audit,
        "source_input": str(source),
        "matchup_rows": matchup_rows,
        "production_outputs_modified": 0,
        "public_site_modified": 0,
        "official_probability_modified": 0,
    }
    (out / "audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit, indent=2))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Explicit pregame expected-lineup CSV")
    parser.add_argument("--output-dir", default="research_outputs/player_impact")
    parser.add_argument("--schedules", default=None, help="Optional schedule CSV for game matchup aggregation")
    args = parser.parse_args()
    run(args.input, args.output_dir, args.schedules)


if __name__ == "__main__":
    main()
