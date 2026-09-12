from __future__ import annotations

"""Diagnostics-only analysis for the failed strict regular-season v2 source contract.

This script never changes qualification thresholds or source-state semantics. It reads
artifacts already produced by the frozen v2 audit and emits descriptive counts that can
support a separately preregistered future contract if the v2 failures are source-semantic
rather than data-quality failures.
"""

import argparse
import json
from pathlib import Path

import pandas as pd


def _normalized_text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip().str.lower()


def _write_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)


def _value_counts(frame: pd.DataFrame, columns: list[str], count_name: str = "rows") -> pd.DataFrame:
    available = [column for column in columns if column in frame.columns]
    if not available or frame.empty:
        return pd.DataFrame(columns=available + [count_name])
    return (
        frame.groupby(available, dropna=False)
        .size()
        .rename(count_name)
        .reset_index()
        .sort_values(count_name, ascending=False, kind="stable")
        .reset_index(drop=True)
    )


def run(output_dir: str | Path) -> dict:
    out = Path(output_dir)
    qualification_path = out / "qualification.json"
    canonical_path = out / "availability_2022_2025_regular_strict.csv"
    unresolved_path = out / "official_identity_unresolved_all.csv"

    qualification = json.loads(qualification_path.read_text(encoding="utf-8"))
    canonical = pd.read_csv(canonical_path, low_memory=False)
    try:
        unresolved = pd.read_csv(unresolved_path, low_memory=False)
    except pd.errors.EmptyDataError:
        unresolved = pd.DataFrame()

    diagnostic_dir = out / "diagnostics"
    diagnostic_dir.mkdir(parents=True, exist_ok=True)

    if not unresolved.empty:
        for column in (
            "external_player",
            "external_position",
            "external_injury",
            "external_practice_status",
            "external_game_status",
            "identity_match_state",
            "identity_match_method",
        ):
            if column not in unresolved.columns:
                unresolved[column] = ""
        unresolved["practice_blank"] = _normalized_text(unresolved["external_practice_status"]).eq("")
        unresolved["game_status_blank"] = _normalized_text(unresolved["external_game_status"]).eq("")
        unresolved["injury_blank"] = _normalized_text(unresolved["external_injury"]).eq("")
        _write_csv(
            unresolved.sort_values(
                [column for column in ["audit_season", "week", "team", "external_player"] if column in unresolved.columns],
                kind="stable",
            ),
            diagnostic_dir / "official_unresolved_rows.csv",
        )
        _write_csv(
            _value_counts(
                unresolved,
                [
                    "audit_season",
                    "identity_match_state",
                    "identity_match_method",
                    "practice_blank",
                    "game_status_blank",
                    "injury_blank",
                ],
            ),
            diagnostic_dir / "official_unresolved_semantic_profile.csv",
        )
        _write_csv(
            _value_counts(unresolved, ["audit_season", "week", "team"]),
            diagnostic_dir / "official_unresolved_by_team_week.csv",
        )
        _write_csv(
            _value_counts(
                unresolved,
                ["audit_season", "external_practice_status", "external_game_status"],
            ),
            diagnostic_dir / "official_unresolved_status_pairs.csv",
        )
    else:
        _write_csv(pd.DataFrame(), diagnostic_dir / "official_unresolved_rows.csv")
        _write_csv(pd.DataFrame(), diagnostic_dir / "official_unresolved_semantic_profile.csv")
        _write_csv(pd.DataFrame(), diagnostic_dir / "official_unresolved_by_team_week.csv")
        _write_csv(pd.DataFrame(), diagnostic_dir / "official_unresolved_status_pairs.csv")

    game_mask = pd.Series(False, index=canonical.index)
    if "identity_matched" in canonical.columns:
        game_mask |= canonical["identity_matched"].fillna(False).astype(bool)
    if "game_status_agrees" in canonical.columns:
        game_mask &= ~canonical["game_status_agrees"].fillna(False).astype(bool)
    game_mismatch = canonical.loc[game_mask].copy()
    _write_csv(game_mismatch, diagnostic_dir / "game_status_mismatch_rows.csv")
    _write_csv(
        _value_counts(
            game_mismatch,
            ["season", "nflverse_game_normalized", "external_game_normalized"],
        ),
        diagnostic_dir / "game_status_mismatch_pairs.csv",
    )
    _write_csv(
        _value_counts(game_mismatch, ["season", "week", "team"]),
        diagnostic_dir / "game_status_mismatch_by_team_week.csv",
    )

    practice_mask = pd.Series(False, index=canonical.index)
    if "identity_matched" in canonical.columns:
        practice_mask |= canonical["identity_matched"].fillna(False).astype(bool)
    if "practice_status_agrees" in canonical.columns:
        practice_mask &= ~canonical["practice_status_agrees"].fillna(False).astype(bool)
    practice_mismatch = canonical.loc[practice_mask].copy()
    _write_csv(practice_mismatch, diagnostic_dir / "practice_status_mismatch_rows.csv")
    _write_csv(
        _value_counts(
            practice_mismatch,
            ["season", "nflverse_practice_normalized", "external_practice_normalized"],
        ),
        diagnostic_dir / "practice_status_mismatch_pairs.csv",
    )

    by_season = {}
    for season in sorted(pd.to_numeric(canonical["season"], errors="coerce").dropna().astype(int).unique()):
        unresolved_season = (
            unresolved[pd.to_numeric(unresolved.get("audit_season"), errors="coerce").eq(season)]
            if not unresolved.empty and "audit_season" in unresolved.columns
            else pd.DataFrame()
        )
        game_season = game_mismatch[pd.to_numeric(game_mismatch["season"], errors="coerce").eq(season)]
        practice_season = practice_mismatch[pd.to_numeric(practice_mismatch["season"], errors="coerce").eq(season)]
        by_season[str(season)] = {
            "official_unresolved_rows": int(len(unresolved_season)),
            "unresolved_practice_blank_rows": int(unresolved_season.get("practice_blank", pd.Series(dtype=bool)).sum()) if not unresolved_season.empty else 0,
            "unresolved_game_status_blank_rows": int(unresolved_season.get("game_status_blank", pd.Series(dtype=bool)).sum()) if not unresolved_season.empty else 0,
            "unresolved_injury_blank_rows": int(unresolved_season.get("injury_blank", pd.Series(dtype=bool)).sum()) if not unresolved_season.empty else 0,
            "game_status_mismatch_rows": int(len(game_season)),
            "practice_status_mismatch_rows": int(len(practice_season)),
        }

    summary = {
        "record_version": 1,
        "source_contract": "V09B-AVAILABILITY-REGULAR-SEASON-HARMONIZATION-V2",
        "diagnostics_only": True,
        "v2_disposition_preserved": qualification.get("research_classification") == "BLOCKED",
        "v09b_execution_authorized": False,
        "thresholds_changed": False,
        "source_state_semantics_changed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "hard_blockers_observed": qualification.get("hard_blockers", []),
        "by_season": by_season,
    }
    (diagnostic_dir / "diagnostic_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="research_outputs/availability_harmonization_regular_v2",
    )
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
