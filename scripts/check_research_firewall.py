from __future__ import annotations

"""Fail closed when a research branch changes production LevLine surfaces."""

import argparse
from pathlib import Path
import subprocess
import sys

RESEARCH_HEAD_PREFIXES = ("research/", "challenger/")

ALLOWED_PREFIXES = (
    ".github/workflows/challenger",
    ".github/workflows/research_",
    "challenger_outputs/",
    "research_outputs/",
    "research/",
    "docs/LEVLINE_RESEARCH",
    "scripts/check_research_firewall.py",
    "scripts/run_challenger",
    "scripts/run_player_state_research.py",
    "scripts/build_player_impact_cards.py",
    "scripts/build_expected_lineup_impacts.py",
    "src/nfl_forecast/challenger",
    "src/nfl_forecast/experiment_registry.py",
    "src/nfl_forecast/player_state_research.py",
    "src/nfl_forecast/player_impact_cards.py",
    "src/nfl_forecast/player_impact_engine.py",
    "src/nfl_forecast/availability_qualification.py",
    "tests/test_challenger",
    "tests/test_experiment_registry.py",
    "tests/test_research_firewall.py",
    "tests/test_player_state_research.py",
    "tests/test_player_impact_cards.py",
    "tests/test_player_impact_engine.py",
    "tests/test_availability_qualification.py",
)

PROTECTED_PREFIXES = (
    "site/",
    "outputs/",
)

PROTECTED_EXACT = {
    "src/nfl_forecast/data.py",
    "src/nfl_forecast/features.py",
    "src/nfl_forecast/models.py",
    "src/nfl_forecast/pipeline.py",
    "src/nfl_forecast/publish.py",
    "src/nfl_forecast/market.py",
    "src/nfl_forecast/market_t120.py",
    "src/nfl_forecast/lock_verify.py",
    "scripts/run_week.py",
    "scripts/refresh_market.py",
    "scripts/pregame_due.py",
    "scripts/verify_pregame_lock.py",
}


def path_allowed(path: str) -> bool:
    normalized = str(Path(path)).replace("\\", "/")
    if normalized in PROTECTED_EXACT or normalized.startswith(PROTECTED_PREFIXES):
        return False
    return normalized.startswith(ALLOWED_PREFIXES)


def validate_changed_paths(paths: list[str]) -> list[str]:
    return sorted({path for path in paths if path and not path_allowed(path)})


def changed_paths(base: str) -> list[str]:
    command = ["git", "diff", "--name-only", f"{base}...HEAD"]
    output = subprocess.check_output(command, text=True)
    return [line.strip() for line in output.splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="origin/main")
    parser.add_argument("--head-ref", default="")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()

    if args.head_ref and not args.head_ref.startswith(RESEARCH_HEAD_PREFIXES):
        print(f"research firewall skipped for non-research head: {args.head_ref}")
        return 0
    paths = args.paths or changed_paths(args.base)
    violations = validate_changed_paths(paths)
    print("research changed paths:")
    for path in paths:
        print(f"  {path}")
    if violations:
        print("\nRESEARCH FIREWALL VIOLATION", file=sys.stderr)
        print("Research branches may modify only explicitly isolated research surfaces.", file=sys.stderr)
        for path in violations:
            print(f"  blocked: {path}", file=sys.stderr)
        return 1
    print("research firewall: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
