from __future__ import annotations

"""Fail closed when a research-scoped change reaches production LevLine surfaces.

Research isolation may not depend solely on a branch-name convention. A pull request is
research-scoped when either its head uses a registered research prefix or its diff touches
an explicitly isolated or research-looking surface. Pure production changes remain outside
this firewall; mixed research/production diffs fail closed.
"""

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
    "docs/IMPACT_MONITOR_GAP_ANALYSIS.md",
    "docs/FST_FREEZE_PROVENANCE.md",
    "scripts/check_research_firewall.py",
    "scripts/run_challenger",
    "scripts/run_fst_",
    "scripts/verify_fst_",
    "scripts/run_player_state_research.py",
    "scripts/build_player_impact_cards.py",
    "scripts/build_expected_lineup_impacts.py",
    "scripts/reconstruct_2025_availability.py",
    "src/nfl_forecast/challenger",
    "src/nfl_forecast/experiment_registry.py",
    "src/nfl_forecast/player_state_research.py",
    "src/nfl_forecast/player_impact_cards.py",
    "src/nfl_forecast/player_impact_engine.py",
    "src/nfl_forecast/player_impact_monitor.py",
    "src/nfl_forecast/availability_qualification.py",
    "src/nfl_forecast/availability_2025_reconstruction.py",
    "tests/test_challenger",
    "tests/test_fst_",
    "tests/test_experiment_registry.py",
    "tests/test_research_firewall.py",
    "tests/test_player_state_research.py",
    "tests/test_player_impact_cards.py",
    "tests/test_player_impact_engine.py",
    "tests/test_player_impact_monitor.py",
    "tests/test_availability_qualification.py",
    "tests/test_availability_2025_reconstruction.py",
)

ALLOWED_EXACT = {
    "src/nfl_forecast/fst_provenance.py",
    "src/nfl_forecast/fst_reconstruction.py",
}

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
    "src/nfl_forecast/fst_production.py",
    "src/nfl_forecast/fst_nested_pure.py",
    "scripts/run_week.py",
    "scripts/refresh_market.py",
    "scripts/pregame_due.py",
    "scripts/verify_pregame_lock.py",
}

RESEARCH_PATH_HINTS = (
    "research/",
    "research_outputs/",
    "challenger_outputs/",
    "challenger",
    "fst_provenance",
    "fst_reconstruction",
    "run_fst_",
    "verify_fst_",
    "experiment_registry",
    "player_state_research",
    "player_impact",
    "availability_qualification",
    "availability_2025_reconstruction",
    "reconstruct_2025_availability",
    "_research.",
    "research_",
)


def _normalize(path: str) -> str:
    return str(Path(path)).replace("\\", "/")


def path_allowed(path: str) -> bool:
    normalized = _normalize(path)
    if normalized in PROTECTED_EXACT or normalized.startswith(PROTECTED_PREFIXES):
        return False
    return normalized in ALLOWED_EXACT or normalized.startswith(ALLOWED_PREFIXES)


def _looks_research_scoped(path: str) -> bool:
    normalized = _normalize(path).lower()
    return any(token in normalized for token in RESEARCH_PATH_HINTS)


def research_scope_triggered(paths: list[str], head_ref: str = "") -> bool:
    """Return whether the diff must satisfy the isolated-research allowlist.

    Registered research/challenger branch names always trigger the firewall. For other
    branch names, touching an allowlisted research surface or any research-looking path
    also triggers it. The latter is deliberately broader than the allowlist so a new,
    unregistered research file fails closed instead of silently escaping on ``fix/...``.
    """

    if head_ref.startswith(RESEARCH_HEAD_PREFIXES):
        return True
    return any(
        path_allowed(path) or _looks_research_scoped(path)
        for path in paths
        if path
    )


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

    paths = args.paths or changed_paths(args.base)
    if not research_scope_triggered(paths, args.head_ref):
        print(f"research firewall skipped for production-only diff: {args.head_ref or '<unnamed>'}")
        return 0

    violations = validate_changed_paths(paths)
    print("research changed paths:")
    for path in paths:
        print(f"  {path}")
    if violations:
        print("\nRESEARCH FIREWALL VIOLATION", file=sys.stderr)
        print("Research-scoped changes may modify only explicitly isolated research surfaces.", file=sys.stderr)
        for path in violations:
            print(f"  blocked: {path}", file=sys.stderr)
        return 1
    print("research firewall: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
