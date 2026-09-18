from __future__ import annotations

"""Fail closed when a research-scoped change reaches production LevLine surfaces.

Research isolation may not depend solely on a branch-name convention. A pull request is
research-scoped when either its head uses a registered research prefix or its diff touches
an explicitly isolated or research-looking surface. Pure production changes remain outside
this firewall; mixed research/production diffs fail closed.

The Props Sunday sprint has one deliberately enumerated exception: its product/QA lane is
assigned a small set of publication/UI integration files. Those exact paths are allowed;
generic site/output/winner-model paths remain protected.
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
    "scripts/run_props_research_beta.py",
    "scripts/build_props_market_snapshot.py",
    "scripts/build_props_integration_manifest.py",
    "scripts/build_props_upstream_snapshot.py",
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
    "src/nfl_forecast/props_player_state.py",
    "src/nfl_forecast/props_player_sources.py",
    "src/nfl_forecast/props_efficiency_td.py",
    "src/nfl_forecast/props_opportunity.py",
    "src/nfl_forecast/props_opportunity_adapter.py",
    "src/nfl_forecast/props_opportunity_handoff.py",
    "src/nfl_forecast/props_market.py",
    "src/nfl_forecast/props_market_odds_api.py",
    "src/nfl_forecast/props_market_live.py",
    "src/nfl_forecast/props_manifest.py",
    "src/nfl_forecast/props_upstream.py",
    "src/nfl_forecast/props_integration.py",
    "tests/test_props_efficiency_td.py",
    "tests/test_props_integration.py",
    "tests/test_props_opportunity.py",
    "tests/test_props_opportunity_adapter.py",
    "tests/test_props_opportunity_handoff.py",
    "tests/test_props_market.py",
    "tests/test_props_market_odds_api.py",
    "tests/test_props_market_live.py",
    "tests/test_props_manifest.py",
    "tests/test_props_upstream.py",
    "tests/test_props_runner.py",
    "tests/test_props_player_state.py",
    "tests/test_props_player_sources.py",
}

# Exact carve-out authorized by the Props sprint charter. Keep this enumerated: do not
# broaden to site/, outputs/, scripts/, or src/nfl_forecast/ prefixes.
PROPS_PRODUCT_ALLOWED_EXACT = {
    ".github/workflows/dashboard.yml",
    ".github/workflows/props_product_qa.yml",
    "scripts/build_props_publication.py",
    "scripts/update_props_history.py",
    "src/nfl_forecast/props_publication.py",
    "tests/test_props_publication.py",
    "site/src/AppCoherent.jsx",
    "site/src/PropsResearchBeta.jsx",
    "site/src/props-research-beta.css",
    "site/src/propsPresentation.js",
    "site/tests/props-research-beta.spec.js",
    "site/tests/propsPresentation.test.mjs",
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
    "props_",
    "_research.",
    "research_",
)


def _normalize(path: str) -> str:
    return str(Path(path)).replace("\\", "/")


def path_allowed(path: str) -> bool:
    normalized = _normalize(path)
    if normalized in PROPS_PRODUCT_ALLOWED_EXACT:
        return True
    if normalized in PROTECTED_EXACT or normalized.startswith(PROTECTED_PREFIXES):
        return False
    return normalized in ALLOWED_EXACT or normalized.startswith(ALLOWED_PREFIXES)


def _looks_research_scoped(path: str) -> bool:
    normalized = _normalize(path).lower()
    return any(token in normalized for token in RESEARCH_PATH_HINTS)


def research_scope_triggered(paths: list[str], head_ref: str = "") -> bool:
    if head_ref.startswith(RESEARCH_HEAD_PREFIXES):
        return True
    return any(path_allowed(path) or _looks_research_scoped(path) for path in paths if path)


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
