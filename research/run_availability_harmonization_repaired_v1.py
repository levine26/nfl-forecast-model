from __future__ import annotations

"""Integrity-repair wrapper for the preregistered availability harmonization audit.

The first live audit halted before season qualification metrics because an official NFL
page rendered one identical player row twice. A second run halted before the legacy
2022-2024 audit because reverse-identity accounting incorrectly reused the legacy
`date_modified` schema requirement for the separately-qualified 2025 asset.

These repairs are source-plumbing only: exact duplicate evidence may collapse,
conflicting duplicates remain fail-closed, and official->nflverse identity accounting
uses only the stable identity fields it actually requires. No model fitting, outcome
scoring, threshold relaxation, or production behavior is introduced here.
"""

import argparse
import json
from pathlib import Path

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import attach_stable_identity, normalize_team
from research import run_availability_harmonization_v1 as base_runner


CONTRACT_PATH = Path("research/availability/2022_2025_harmonization_contract_v1.json")
OFFICIAL_SEMANTIC_COLUMNS = [
    "season", "week", "team", "external_player", "external_position", "external_injury",
    "external_practice_status", "external_game_status", "external_source", "source_url",
]
REVERSE_IDENTITY_REQUIRED_NFLVERSE = {
    "season", "week", "team", "gsis_id", "full_name", "first_name", "last_name",
}

_OUTPUT_DIR: Path | None = None
_AUDIT: dict[int, dict] = {}
_ORIGINAL_COLLECT_OFFICIAL = base_runner._collect_official_season
_ORIGINAL_BUILD_SEASON = base_runner.build_season_reconstruction


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def collapse_exact_official_duplicates(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Collapse only rows whose complete official-source semantics are identical."""
    missing = set(OFFICIAL_SEMANTIC_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"official cross-check missing duplicate-reconciliation fields: {sorted(missing)}")
    duplicate_mask = frame.duplicated(OFFICIAL_SEMANTIC_COLUMNS, keep=False)
    duplicates = frame.loc[duplicate_mask, OFFICIAL_SEMANTIC_COLUMNS].copy()
    deduped = frame.drop_duplicates(OFFICIAL_SEMANTIC_COLUMNS, keep="first").reset_index(drop=True)
    return deduped, duplicates


def _identity_base(nflverse: pd.DataFrame, *, season: int) -> pd.DataFrame:
    """Validate only the stable fields needed for symmetric identity accounting.

    The original 2022-2024 builder separately enforces its stronger legacy schema,
    including `date_modified`. Reverse identity itself must also work on the already-
    qualified 2025 asset, whose source schema does not contain that legacy field.
    """
    missing = REVERSE_IDENTITY_REQUIRED_NFLVERSE - set(nflverse.columns)
    if missing:
        raise ValueError(f"{season} nflverse identity audit missing fields: {sorted(missing)}")
    out = nflverse[pd.to_numeric(nflverse["season"], errors="coerce").eq(season)].copy()
    if out.empty:
        raise ValueError(f"{season} nflverse identity audit has no target-season rows")
    out["week"] = pd.to_numeric(out["week"], errors="raise").astype(int)
    out["team"] = out["team"].map(normalize_team)
    return out


def reverse_identity_audit(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    *,
    season: int,
) -> tuple[dict, pd.DataFrame]:
    """Account for every distinct official row against stable nflverse identity."""
    base = _identity_base(nflverse, season=season)
    matched = attach_stable_identity(official, base)
    unique = matched["identity_match_state"].eq("unique")
    total = int(len(matched))
    resolved = int(unique.sum())
    unresolved = matched.loc[~unique].copy()
    rate = float(resolved / total) if total else 0.0
    return ({
        "season": int(season),
        "official_distinct_rows": total,
        "official_unique_stable_identity_rows": resolved,
        "official_unresolved_identity_rows": int(len(unresolved)),
        "official_identity_resolution_rate": rate,
    }, unresolved)


def _record_reverse_identity(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    *,
    season: int,
) -> None:
    contract = _load_contract()
    threshold = float(contract["qualification_gates"]["official_identity_resolution_rate_min"])
    metrics, unresolved = reverse_identity_audit(official, nflverse, season=season)
    metrics["official_identity_resolution_rate_min"] = threshold
    metrics["official_identity_gate_passed"] = metrics["official_identity_resolution_rate"] >= threshold
    _AUDIT.setdefault(int(season), {}).update(metrics)
    if _OUTPUT_DIR is not None:
        unresolved.to_csv(_OUTPUT_DIR / f"official_identity_unresolved_{season}.csv", index=False)
        _write_json(_OUTPUT_DIR / "official_reverse_identity_audit.json", _AUDIT)
    if not metrics["official_identity_gate_passed"]:
        raise ValueError(
            f"{season} official->nflverse stable identity resolution "
            f"{metrics['official_identity_resolution_rate']:.6f} is below frozen gate {threshold:.6f}"
        )


def _collect_official_with_exact_dedupe(*args, **kwargs):
    frame, pages = _ORIGINAL_COLLECT_OFFICIAL(*args, **kwargs)
    season = int(kwargs["season"])
    deduped, duplicate_rows = collapse_exact_official_duplicates(frame)
    _AUDIT.setdefault(season, {}).update({
        "official_rows_before_exact_dedupe": int(len(frame)),
        "official_rows_after_exact_dedupe": int(len(deduped)),
        "official_exact_duplicate_rows_collapsed": int(len(frame) - len(deduped)),
    })
    if _OUTPUT_DIR is not None:
        duplicate_rows.to_csv(_OUTPUT_DIR / f"official_exact_duplicate_rows_{season}.csv", index=False)
        _write_json(_OUTPUT_DIR / "official_reverse_identity_audit.json", _AUDIT)
    return deduped, pages


def _build_season_with_reverse_accounting(
    nflverse: pd.DataFrame,
    official_reports: pd.DataFrame,
    schedules: pd.DataFrame,
    *,
    season: int,
) -> pd.DataFrame:
    _record_reverse_identity(official_reports, nflverse, season=season)
    # The original builder still owns legacy schema checks and stable-key conflict
    # handling. Thus a non-identical duplicate remains a hard failure.
    return _ORIGINAL_BUILD_SEASON(nflverse, official_reports, schedules, season=season)


def _audit_qualified_2025(reconstruction_dir: Path) -> None:
    official_path = reconstruction_dir / "official_nfl_report_crosscheck_2025.csv"
    nflverse_path = reconstruction_dir / "raw" / "nflverse" / "injuries_2025.csv"
    if not official_path.exists() or not nflverse_path.exists():
        raise FileNotFoundError("qualified 2025 reconstruction is missing reverse-identity audit inputs")
    official = pd.read_csv(official_path, low_memory=False)
    nflverse = pd.read_csv(nflverse_path, low_memory=False)
    deduped, duplicate_rows = collapse_exact_official_duplicates(official)
    _AUDIT.setdefault(2025, {}).update({
        "official_rows_before_exact_dedupe": int(len(official)),
        "official_rows_after_exact_dedupe": int(len(deduped)),
        "official_exact_duplicate_rows_collapsed": int(len(official) - len(deduped)),
        "inherited_2025_reconstruction_qualification": True,
    })
    if _OUTPUT_DIR is not None:
        duplicate_rows.to_csv(_OUTPUT_DIR / "official_exact_duplicate_rows_2025.csv", index=False)
    _record_reverse_identity(deduped, nflverse, season=2025)


def main() -> int:
    global _OUTPUT_DIR
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/availability_2022_2025_harmonization")
    parser.add_argument("--reconstruction-2025-dir", default="research_outputs/availability_2025_reconstruction")
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()

    _OUTPUT_DIR = Path(args.output_dir)
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    reconstruction_2025_dir = Path(args.reconstruction_2025_dir)

    base_runner._collect_official_season = _collect_official_with_exact_dedupe
    base_runner.build_season_reconstruction = _build_season_with_reverse_accounting

    result: dict | None = None
    try:
        _audit_qualified_2025(reconstruction_2025_dir)
        result = base_runner.collect(_OUTPUT_DIR, reconstruction_2025_dir=reconstruction_2025_dir)
        result["official_reverse_identity_audit"] = {str(k): v for k, v in sorted(_AUDIT.items())}
        result["implementation_repair"] = {
            "first_live_run_failure": "2022 identical official duplicate stable player-week row",
            "second_live_run_failure": "2025 reverse identity incorrectly inherited legacy date_modified requirement",
            "exact_duplicate_policy": "collapse only complete semantic duplicates",
            "conflicting_duplicate_policy": "fail closed in original stable-key duplicate gate",
            "reverse_identity_schema_policy": "stable identity fields only; legacy date_modified remains enforced separately for 2022-2024",
            "numeric_threshold_relaxation": False,
            "game_outcomes_consulted": False,
            "completed_2026_outcomes_consulted": False,
        }
        _write_json(_OUTPUT_DIR / "qualification_with_integrity_repairs.json", result)
        print(json.dumps(result, indent=2, sort_keys=True, default=str))
        if args.require_qualified and not bool(result.get("qualified")):
            return 1
        return 0
    finally:
        _write_json(_OUTPUT_DIR / "official_reverse_identity_audit.json", {str(k): v for k, v in sorted(_AUDIT.items())})


if __name__ == "__main__":
    raise SystemExit(main())
