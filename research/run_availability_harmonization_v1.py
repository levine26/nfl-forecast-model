from __future__ import annotations

"""Execute the preregistered 2022-2025 availability source harmonization audit.

This is source/state qualification only. It does not fit or score V09B, inspect game
outcomes, or authorize any production/probability feature.
"""

import argparse
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import time

import pandas as pd
import requests

from nfl_forecast.availability_2025_reconstruction import parse_nfl_postseason_page
from research.availability_harmonization_v1 import (
    LEGACY_SEASONS,
    build_season_reconstruction,
    missingness_report,
    sha256_bytes,
    standardize_canonical,
    summarize_season,
)

CONTRACT_PATH = Path("research/availability/2022_2025_harmonization_contract_v1.json")
QUALIFIED_2025_RECEIPT_PATH = Path("research/availability/2025_reconstruction_qualification_v1.json")
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
NFLVERSE_URL = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{season}.csv"
NFL_REG_URL = "https://www.nfl.com/injuries/league/{season}/reg{week}"
NFL_POST_URL = "https://www.nfl.com/injuries/league/{season}/post{page_week}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LevLineResearch/1.0; cross-season-availability-audit)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _write_bytes(path: Path, payload: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"path": str(path), "bytes": len(payload), "sha256": sha256_bytes(payload)}


def _fetch(session: requests.Session, url: str, *, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # pragma: no cover - live network behavior
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def _collect_official_season(
    session: requests.Session,
    *,
    season: int,
    raw_dir: Path,
    manifest: dict,
) -> tuple[pd.DataFrame, int]:
    frames: list[pd.DataFrame] = []
    pages = 0
    for week in range(1, 19):
        url = NFL_REG_URL.format(season=season, week=week)
        payload = _fetch(session, url)
        record = _write_bytes(raw_dir / "nfl_com" / str(season) / f"reg_{week:02d}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "season": season, "nfl_week": week})
        manifest["sources"].append(record)
        frame = parse_nfl_postseason_page(
            payload.decode("utf-8", errors="replace"),
            nfl_week=week,
            source_url=url,
        )
        frame["season"] = season
        frames.append(frame)
        pages += 1
        time.sleep(0.08)

    for page_week, nfl_week in {1: 19, 2: 20, 3: 21, 4: 22}.items():
        url = NFL_POST_URL.format(season=season, page_week=page_week)
        payload = _fetch(session, url)
        record = _write_bytes(raw_dir / "nfl_com" / str(season) / f"post_{page_week}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "season": season, "nfl_week": nfl_week})
        manifest["sources"].append(record)
        frame = parse_nfl_postseason_page(
            payload.decode("utf-8", errors="replace"),
            nfl_week=nfl_week,
            source_url=url,
        )
        frame["season"] = season
        frames.append(frame)
        pages += 1
        time.sleep(0.08)

    if not frames:
        raise RuntimeError(f"official NFL injury-page collection produced no rows for {season}")
    return pd.concat(frames, ignore_index=True), pages


def _adapt_qualified_2025(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "season", "week", "team", "gsis_id", "position", "full_name",
        "nflverse_practice_normalized", "identity_matched", "practice_status_agrees",
        "game_status_agrees", "known_by_t120", "fully_qualified_practice_state",
        "kickoff_utc", "t120_utc", "report_deadline_eod_utc", "availability_source",
        "chronology_policy", "historical_game_status_feature_authorized", "postgame_information_used",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"qualified 2025 canonical frame missing fields: {sorted(missing)}")
    out = frame.copy()
    out["canonical_practice_state"] = out["nflverse_practice_normalized"].where(
        out["fully_qualified_practice_state"].astype(bool),
        "unknown",
    )
    out["date_modified_utc"] = pd.NaT

    def reason(row: pd.Series) -> str:
        reasons: list[str] = []
        if not bool(row["identity_matched"]):
            reasons.append("identity_unresolved")
        if bool(row["identity_matched"]) and not bool(row["practice_status_agrees"]):
            reasons.append("practice_state_crosscheck_mismatch")
        if bool(row["identity_matched"]) and not bool(row["known_by_t120"]):
            reasons.append("not_proven_known_by_t120")
        if not bool(row["fully_qualified_practice_state"]) and not reasons:
            reasons.append("practice_state_unqualified")
        return ";".join(reasons)

    out["unresolved_reason"] = out.apply(reason, axis=1)
    return standardize_canonical(out)


def _validate_2025_receipt(runtime_qualification: dict, receipt: dict) -> list[str]:
    reasons: list[str] = []
    if runtime_qualification.get("qualified") is not True:
        reasons.append("runtime_2025_reconstruction_not_qualified")
    expected = receipt["qualification_metrics"]
    checks = {
        "nflverse_rows": expected["nflverse_rows"],
        "external_rows": expected["external_crosscheck_rows"],
        "identity_match_rate": expected["identity_match_rate"],
        "practice_status_agreement_rate": expected["practice_status_agreement_rate"],
        "game_status_agreement_rate": expected["diagnostic_game_status_agreement_rate"],
        "known_by_t120_rate": expected["known_by_t120_rate_among_matched_rows"],
        "fully_qualified_practice_state_rate": expected["fully_qualified_practice_state_rate"],
    }
    for key, expected_value in checks.items():
        actual = runtime_qualification.get(key)
        if isinstance(expected_value, float):
            if actual is None or abs(float(actual) - expected_value) > 1e-12:
                reasons.append(f"2025_receipt_metric_drift:{key}")
        elif actual != expected_value:
            reasons.append(f"2025_receipt_metric_drift:{key}")
    if runtime_qualification.get("completed_2026_outcomes_used") != 0:
        reasons.append("runtime_2025_completed_2026_outcomes_nonzero")
    if runtime_qualification.get("actual_snaps_used") != 0:
        reasons.append("runtime_2025_actual_snaps_nonzero")
    if runtime_qualification.get("postgame_participation_used") != 0:
        reasons.append("runtime_2025_postgame_participation_nonzero")
    return reasons


def collect(output_dir: Path, *, reconstruction_2025_dir: Path) -> dict:
    contract = _load_json(CONTRACT_PATH)
    receipt_2025 = _load_json(QUALIFIED_2025_RECEIPT_PATH)
    gates = contract["qualification_gates"]
    if contract["game_outcomes_allowed"] is not False or contract["completed_2026_outcomes_allowed"] is not False:
        raise RuntimeError("harmonization contract must prohibit outcomes before collection")
    if contract["v09b_execution_authorized"] is not False or contract["probability_feature_authorized"] is not False:
        raise RuntimeError("harmonization contract may not authorize V09B or a probability feature")

    session = requests.Session()
    raw_dir = output_dir / "raw"
    manifest: dict = {
        "contract": str(CONTRACT_PATH),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_seasons": contract["target_seasons"],
        "production_authorized": False,
        "probability_feature_authorized": False,
        "v09b_execution_authorized": False,
        "completed_2026_outcomes_used": 0,
        "game_outcomes_used": 0,
        "sources": [],
    }

    schedule_payload = _fetch(session, SCHEDULE_URL)
    schedule_record = _write_bytes(raw_dir / "nflverse" / "games.csv", schedule_payload)
    schedule_record.update({"source": "nflverse_schedule", "url": SCHEDULE_URL})
    manifest["sources"].append(schedule_record)
    schedules = pd.read_csv(StringIO(schedule_payload.decode("utf-8")), low_memory=False)

    canonical_frames: list[pd.DataFrame] = []
    season_summaries: list[dict] = []

    for season in LEGACY_SEASONS:
        url = NFLVERSE_URL.format(season=season)
        payload = _fetch(session, url)
        record = _write_bytes(raw_dir / "nflverse" / f"injuries_{season}.csv", payload)
        record.update({"source": "nflverse_injuries", "url": url, "season": season})
        manifest["sources"].append(record)
        injury = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)

        official, page_count = _collect_official_season(
            session,
            season=season,
            raw_dir=raw_dir,
            manifest=manifest,
        )
        official.to_csv(output_dir / f"official_nfl_report_crosscheck_{season}.csv", index=False)
        canonical = build_season_reconstruction(
            injury,
            official,
            schedules,
            season=season,
        )
        canonical.to_csv(output_dir / f"availability_{season}_canonical_audit.csv", index=False)
        summary = summarize_season(
            canonical,
            season=season,
            official_crosscheck_rows=len(official),
            official_pages_collected=page_count,
            gates=gates,
        )
        season_summaries.append(summary.as_dict())
        canonical_frames.append(standardize_canonical(canonical))

    qualification_2025 = _load_json(reconstruction_2025_dir / "qualification.json")
    receipt_drift = _validate_2025_receipt(qualification_2025, receipt_2025)
    canonical_2025_raw = pd.read_csv(reconstruction_2025_dir / "availability_2025_canonical.csv", low_memory=False)
    canonical_2025 = _adapt_qualified_2025(canonical_2025_raw)
    canonical_frames.append(canonical_2025)

    q2025 = receipt_2025["qualification_metrics"]
    schedule_rate_2025 = float(canonical_2025["kickoff_utc"].notna().mean())
    duplicate_2025 = int(canonical_2025.duplicated(["season", "week", "team", "gsis_id"]).sum())
    summary_2025_reasons = list(receipt_drift)
    if schedule_rate_2025 < float(gates["schedule_match_rate_min"]):
        summary_2025_reasons.append("schedule_match_rate_below_gate")
    if duplicate_2025 > int(gates["duplicate_identity_rows_allowed"]):
        summary_2025_reasons.append("duplicate_identity_rows_above_gate")
    if float(q2025["identity_match_rate"]) < float(gates["unique_identity_match_rate_min"]):
        summary_2025_reasons.append("identity_match_rate_below_gate")
    if float(q2025["practice_status_agreement_rate"]) < float(gates["practice_status_agreement_rate_min"]):
        summary_2025_reasons.append("practice_status_agreement_rate_below_gate")
    if float(q2025["diagnostic_game_status_agreement_rate"]) < float(gates["diagnostic_game_status_agreement_rate_min"]):
        summary_2025_reasons.append("diagnostic_game_status_agreement_rate_below_gate")
    if float(q2025["known_by_t120_rate_among_matched_rows"]) < float(gates["known_by_t120_rate_required_among_matched_rows"]):
        summary_2025_reasons.append("known_by_t120_rate_below_gate")
    if float(q2025["fully_qualified_practice_state_rate"]) < float(gates["fully_qualified_practice_state_rate_min"]):
        summary_2025_reasons.append("fully_qualified_practice_state_rate_below_gate")

    season_summaries.append({
        "season": 2025,
        "nflverse_rows": int(q2025["nflverse_rows"]),
        "official_crosscheck_rows": int(q2025["external_crosscheck_rows"]),
        "official_pages_collected": 22,
        "stable_gsis_missing_rate": 0.0,
        "unique_identity_match_rate": float(q2025["identity_match_rate"]),
        "practice_status_agreement_rate": float(q2025["practice_status_agreement_rate"]),
        "diagnostic_game_status_agreement_rate": float(q2025["diagnostic_game_status_agreement_rate"]),
        "known_by_t120_rate_among_matched_rows": float(q2025["known_by_t120_rate_among_matched_rows"]),
        "fully_qualified_practice_state_rate": float(q2025["fully_qualified_practice_state_rate"]),
        "date_modified_parse_rate": None,
        "schedule_match_rate": schedule_rate_2025,
        "duplicate_identity_rows": duplicate_2025,
        "qualified": not summary_2025_reasons,
        "reasons": summary_2025_reasons,
    })

    unified = pd.concat(canonical_frames, ignore_index=True)
    unified = unified.sort_values(["season", "week", "team", "gsis_id"], kind="stable").reset_index(drop=True)
    unified.to_csv(output_dir / "availability_2022_2025_harmonized_audit.csv", index=False)
    unresolved = unified[unified["canonical_practice_state"].eq("unknown")].copy()
    unresolved.to_csv(output_dir / "availability_2022_2025_unresolved.csv", index=False)
    missingness_report(unified).to_csv(output_dir / "availability_2022_2025_missingness.csv", index=False)

    observed_seasons = sorted(pd.to_numeric(unified["season"], errors="coerce").dropna().astype(int).unique().tolist())
    required_seasons = list(map(int, gates["required_seasons_exact"]))
    global_reasons: list[str] = []
    if observed_seasons != required_seasons:
        global_reasons.append("required_seasons_mismatch")
    if any(not bool(item["qualified"]) for item in season_summaries):
        global_reasons.append("one_or_more_seasons_failed_preregistered_gates")

    result = {
        "contract_version": contract["contract_version"],
        "qualified": not global_reasons,
        "reasons": global_reasons,
        "season_summaries": season_summaries,
        "harmonized_rows": int(len(unified)),
        "unresolved_rows": int(len(unresolved)),
        "observed_seasons": observed_seasons,
        "actual_snaps_used": 0,
        "postgame_participation_used": 0,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "probability_feature_authorized": False,
        "v09b_execution_authorized": False,
        "production_authorized": False,
        "historical_game_status_feature_authorized": False,
        "schedule_capture_sha256": schedule_record["sha256"],
    }
    _write_json(output_dir / "qualification.json", result)
    _write_json(output_dir / "source_manifest.json", manifest)
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/availability_2022_2025_harmonization")
    parser.add_argument(
        "--reconstruction-2025-dir",
        default="research_outputs/availability_2025_reconstruction",
    )
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result = collect(output_dir, reconstruction_2025_dir=Path(args.reconstruction_2025_dir))
    if args.require_qualified and not result["qualified"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
