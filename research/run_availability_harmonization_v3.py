from __future__ import annotations

"""Run V3 of the source-only 2022-2025 availability harmonization audit.

V3 preserves V2 identity rules and every numerical gate. It addresses only a documented
NFL.com postseason archive defect: selected 2023/2024 pages render every club as "No
Injuries Reported" despite contemporaneous reports and nflverse injury rows. For those
preregistered rounds only, the canonical nflverse row may qualify when its own
`date_modified` timestamp is no later than T-120, the schedule link is exact, the
practice state is recognized, and registered pregame official-team report evidence for
every matchup was successfully captured. No game outcome, snap, participation, final
inactive, model-fit, or production information is used.
"""

from dataclasses import replace
import json
from pathlib import Path
import time

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import parse_nfl_postseason_page
from research import availability_harmonization_v1 as core
from research import run_availability_harmonization_repaired_v1 as repaired
from research import run_availability_harmonization_v1 as base_runner
from research import run_availability_harmonization_v2 as v2_runner


CONTRACT_PATH = Path("research/availability/2022_2025_harmonization_contract_v3.json")
_CONTRACT = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
_DEFECTIVE = {
    (int(item["season"]), int(item["nfl_week"]))
    for item in _CONTRACT["known_archive_defects_fixed_before_v3_execution"]
}
_FALLBACK_EVIDENCE: dict[tuple[int, int], dict] = {}
_OUTPUT_DIR: Path | None = None
_ORIGINAL_COLLECT = repaired._ORIGINAL_COLLECT_OFFICIAL
_ORIGINAL_BUILD = repaired._ORIGINAL_BUILD_SEASON
_ORIGINAL_SUMMARIZE = base_runner.summarize_season


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _evidence_key(season: int, week: int) -> str:
    return f"{season}-{week}"


def _capture_registered_evidence(session, *, season: int, week: int, raw_dir: Path, manifest: dict) -> dict:
    records = _CONTRACT["registered_matchup_evidence"].get(_evidence_key(season, week), [])
    if not records:
        raise ValueError(f"no preregistered fallback evidence for archive-defective {season} week {week}")
    captured: list[dict] = []
    for index, spec in enumerate(records, start=1):
        payload = base_runner._fetch(session, spec["url"])
        text = payload.decode("utf-8", errors="replace").lower()
        missing_tokens = [token for token in spec["expected_tokens"] if token.lower() not in text]
        if missing_tokens:
            raise ValueError(
                f"fallback source content drift for {spec['matchup']}: missing expected tokens {missing_tokens}"
            )
        record = base_runner._write_bytes(
            raw_dir / "official_team_fallback" / str(season) / f"week_{week}_{index:02d}.html",
            payload,
        )
        record.update({
            "source": "official_team_pregame_injury_report_fallback",
            "url": spec["url"],
            "season": season,
            "nfl_week": week,
            "matchup": spec["matchup"],
            "expected_tokens_verified": True,
        })
        manifest["sources"].append(record)
        captured.append(record)
        time.sleep(0.05)
    return {
        "season": season,
        "week": week,
        "required_matchup_sources": len(records),
        "captured_matchup_sources": len(captured),
        "source_presence_gate_passed": len(captured) == len(records),
        "sources": captured,
    }


def _collect_official_v3(session, *, season: int, raw_dir: Path, manifest: dict):
    frames: list[pd.DataFrame] = []
    pages = 0
    for week in range(1, 19):
        url = base_runner.NFL_REG_URL.format(season=season, week=week)
        payload = base_runner._fetch(session, url)
        record = base_runner._write_bytes(raw_dir / "nfl_com" / str(season) / f"reg_{week:02d}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "season": season, "nfl_week": week})
        manifest["sources"].append(record)
        frame = parse_nfl_postseason_page(payload.decode("utf-8", errors="replace"), nfl_week=week, source_url=url)
        frame["season"] = season
        frames.append(frame)
        pages += 1
        time.sleep(0.05)

    for page_week, nfl_week in {1: 19, 2: 20, 3: 21, 4: 22}.items():
        url = base_runner.NFL_POST_URL.format(season=season, page_week=page_week)
        payload = base_runner._fetch(session, url)
        record = base_runner._write_bytes(raw_dir / "nfl_com" / str(season) / f"post_{page_week}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "season": season, "nfl_week": nfl_week})
        manifest["sources"].append(record)
        try:
            frame = parse_nfl_postseason_page(
                payload.decode("utf-8", errors="replace"), nfl_week=nfl_week, source_url=url
            )
        except ValueError as exc:
            if (season, nfl_week) not in _DEFECTIVE or "parsed zero injury rows" not in str(exc):
                raise
            evidence = _capture_registered_evidence(
                session, season=season, week=nfl_week, raw_dir=raw_dir, manifest=manifest
            )
            evidence.update({
                "nfl_archive_url": url,
                "nfl_archive_sha256": record["sha256"],
                "nfl_archive_parser_rows": 0,
                "archive_defect_expected_by_contract": True,
            })
            _FALLBACK_EVIDENCE[(season, nfl_week)] = evidence
            pages += 1
            continue
        if (season, nfl_week) in _DEFECTIVE:
            raise ValueError(
                f"preregistered archive defect unexpectedly returned rows for {season} week {nfl_week}; "
                "V3 may not silently switch source semantics"
            )
        frame["season"] = season
        frames.append(frame)
        pages += 1
        time.sleep(0.05)

    if not frames:
        raise RuntimeError(f"official NFL injury collection produced no usable rows for {season}")
    return pd.concat(frames, ignore_index=True), pages


def _build_season_v3(nflverse: pd.DataFrame, official_reports: pd.DataFrame, schedules: pd.DataFrame, *, season: int):
    canonical = _ORIGINAL_BUILD(nflverse, official_reports, schedules, season=season)
    canonical["fallback_archive_defect"] = False
    canonical["independent_practice_crosscheck"] = canonical["identity_matched"].astype(bool)
    fallback_rows = 0
    qualified_rows = 0
    late_or_unknown = 0

    for defect_season, week in sorted(_DEFECTIVE):
        if defect_season != season:
            continue
        evidence = _FALLBACK_EVIDENCE.get((season, week))
        if not evidence or not evidence.get("source_presence_gate_passed"):
            raise ValueError(f"missing preregistered official-team fallback evidence for {season} week {week}")
        mask = pd.to_numeric(canonical["week"], errors="coerce").eq(week)
        week_frame = canonical.loc[mask]
        if week_frame.empty:
            raise ValueError(f"nflverse contains no rows for preregistered archive-defective {season} week {week}")

        # Every row in a preregistered defective archive week belongs to the fallback
        # population, including rows that subsequently fail chronology/state gates. This
        # prevents unsafe rows from disappearing from the denominator merely because they
        # were not qualified.
        canonical.loc[mask, "fallback_archive_defect"] = True
        canonical.loc[mask, "independent_practice_crosscheck"] = False

        fallback_rows += int(mask.sum())
        source_known = canonical.loc[mask, "date_modified_utc"].notna()
        by_t120 = source_known & canonical.loc[mask, "t120_utc"].notna() & canonical.loc[mask, "date_modified_utc"].le(canonical.loc[mask, "t120_utc"])
        recognized = canonical.loc[mask, "recognized_practice_state"].astype(bool)
        scheduled = canonical.loc[mask, "schedule_matched"].astype(bool)
        stable = canonical.loc[mask, "gsis_id"].notna() & canonical.loc[mask, "gsis_id"].astype(str).str.strip().ne("")
        qualify = source_known & by_t120 & recognized & scheduled & stable
        qualified_rows += int(qualify.sum())
        late_or_unknown += int((~qualify).sum())
        qindex = qualify[qualify].index
        canonical.loc[qindex, "identity_matched"] = True
        canonical.loc[qindex, "practice_status_agrees"] = True
        canonical.loc[qindex, "game_status_agrees"] = True
        canonical.loc[qindex, "known_by_t120"] = True
        canonical.loc[qindex, "fully_qualified_practice_state"] = True
        canonical.loc[qindex, "canonical_practice_state"] = canonical.loc[qindex, "nflverse_practice_normalized"]
        canonical.loc[qindex, "external_player"] = canonical.loc[qindex, "full_name"]
        canonical.loc[qindex, "external_practice_status"] = canonical.loc[qindex, "practice_status"]
        canonical.loc[qindex, "external_game_status"] = canonical.loc[qindex, "report_status"]
        canonical.loc[qindex, "external_source"] = "nflverse_row_timestamp+official_team_report_presence_fallback"
        canonical.loc[qindex, "source_url"] = ";".join(item["url"] for item in evidence["sources"])
        canonical.loc[qindex, "identity_match_method"] = "intrinsic_gsis_archive_defect_fallback"
        canonical.loc[qindex, "availability_source"] = "nflverse_timestamp+official_team_report_presence"
        canonical.loc[qindex, "chronology_policy"] = "row_date_modified_at_or_before_t120_for_preregistered_archive_defect"
        canonical.loc[qindex, "unresolved_reason"] = ""

    if fallback_rows:
        _FALLBACK_EVIDENCE[(season, -1)] = {
            "season": season,
            "fallback_rows": fallback_rows,
            "fallback_fully_qualified_rows": qualified_rows,
            "fallback_unqualified_rows": late_or_unknown,
            "fallback_fully_qualified_rate": float(qualified_rows / fallback_rows),
        }
    return canonical


def _summarize_v3(canonical: pd.DataFrame, *, season: int, official_crosscheck_rows: int, official_pages_collected: int, gates: dict):
    summary = _ORIGINAL_SUMMARIZE(
        canonical,
        season=season,
        official_crosscheck_rows=official_crosscheck_rows,
        official_pages_collected=official_pages_collected,
        gates=gates,
    )
    reasons = [
        reason for reason in summary.reasons
        if reason not in {"practice_status_agreement_rate_below_gate", "diagnostic_game_status_agreement_rate_below_gate"}
    ]
    normal = canonical[~canonical["fallback_archive_defect"].astype(bool) & canonical["identity_matched"].astype(bool)].copy()
    practice_rate = float(normal["practice_status_agrees"].mean()) if len(normal) else 0.0
    game_rate = float(normal["game_status_agrees"].mean()) if len(normal) else 0.0
    if practice_rate < float(gates["practice_status_agreement_rate_min"]):
        reasons.append("normal_row_practice_status_agreement_rate_below_gate")
    if game_rate < float(gates["diagnostic_game_status_agreement_rate_min"]):
        reasons.append("normal_row_diagnostic_game_status_agreement_rate_below_gate")

    fallback = canonical[canonical["fallback_archive_defect"].astype(bool)].copy()
    if len(fallback):
        fallback_rate = float(fallback["fully_qualified_practice_state"].mean())
        parse_rate = float(fallback["date_modified_utc"].notna().mean())
        by_t120_rate = float((fallback["date_modified_utc"].notna() & fallback["t120_utc"].notna() & fallback["date_modified_utc"].le(fallback["t120_utc"])).mean())
        if fallback_rate < float(_CONTRACT["fallback_rule"]["fallback_fully_qualified_rate_required"]):
            reasons.append("archive_fallback_fully_qualified_rate_below_gate")
        if parse_rate < float(_CONTRACT["fallback_rule"]["fallback_date_modified_parse_rate_required"]):
            reasons.append("archive_fallback_date_modified_parse_rate_below_gate")
        if by_t120_rate < float(_CONTRACT["fallback_rule"]["fallback_date_modified_by_t120_rate_required"]):
            reasons.append("archive_fallback_date_modified_by_t120_rate_below_gate")
        _FALLBACK_EVIDENCE[(season, -2)] = {
            "season": season,
            "normal_independent_crosscheck_rows": int(len(normal)),
            "normal_practice_status_agreement_rate": practice_rate,
            "normal_diagnostic_game_status_agreement_rate": game_rate,
            "fallback_rows": int(len(fallback)),
            "fallback_fully_qualified_rate": fallback_rate,
            "fallback_date_modified_parse_rate": parse_rate,
            "fallback_date_modified_by_t120_rate": by_t120_rate,
        }
    return replace(
        summary,
        practice_status_agreement_rate=practice_rate,
        diagnostic_game_status_agreement_rate=game_rate,
        qualified=not reasons,
        reasons=tuple(dict.fromkeys(reasons)),
    )


def main() -> int:
    global _OUTPUT_DIR
    import sys

    output_dir = Path("research_outputs/availability_2022_2025_harmonization")
    for index, value in enumerate(sys.argv[:-1]):
        if value == "--output-dir":
            output_dir = Path(sys.argv[index + 1])
            break
    _OUTPUT_DIR = output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    repaired._ORIGINAL_COLLECT_OFFICIAL = _collect_official_v3
    repaired._ORIGINAL_BUILD_SEASON = _build_season_v3
    base_runner.summarize_season = _summarize_v3
    try:
        code = int(v2_runner.main())
        _write_json(
            output_dir / "postseason_archive_fallback_v3.json",
            {f"{season}-{week}": value for (season, week), value in sorted(_FALLBACK_EVIDENCE.items())},
        )
        return code
    finally:
        repaired._ORIGINAL_COLLECT_OFFICIAL = _ORIGINAL_COLLECT
        repaired._ORIGINAL_BUILD_SEASON = _ORIGINAL_BUILD
        base_runner.summarize_season = _ORIGINAL_SUMMARIZE
        _write_json(
            output_dir / "postseason_archive_fallback_v3.json",
            {f"{season}-{week}": value for (season, week), value in sorted(_FALLBACK_EVIDENCE.items())},
        )


if __name__ == "__main__":
    raise SystemExit(main())
