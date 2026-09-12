from __future__ import annotations

"""Execute the preregistered strict regular-season availability harmonization audit."""

import argparse
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import platform
import subprocess
import time

import pandas as pd
import requests

from nfl_forecast.availability_2025_reconstruction import parse_nfl_postseason_page
from research.availability_harmonization_regular_v2 import (
    SCHEDULE_HASH_COLUMNS,
    build_strict_season,
    collapse_exact_official_duplicates,
    evaluate_strict_harmonization,
    filter_model_eligible_schedule,
    schedule_subset_sha256,
    sha256_bytes,
    validate_strict_injury_frame,
    validate_v09b_preregistry,
    verify_2025_receipt,
)
from research.availability_identity_regular_v2 import (
    PLAYER_MASTER_URL,
    validate_player_master_payload,
)


CONTRACT_PATH = Path("research/availability/harmonization_regular_season_contract_v2.json")
EXPERIMENTS_PATH = Path("research/experiments.json")
RECEIPT_2025_PATH = Path("research/availability/2025_reconstruction_qualification_v1.json")
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LevLineResearch/2.0; regular-season-availability-audit)",
    "Accept": "text/html,text/csv,text/plain,application/xhtml+xml,*/*",
}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "unknown"


def _fetch(session: requests.Session, url: str, *, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # pragma: no cover - live network behavior
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def _capture(path: Path, payload: bytes, **metadata) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": str(path),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        **metadata,
    }


def _collect_official_regular_season(
    session: requests.Session,
    *,
    season: int,
    url_template: str,
    raw_dir: Path,
    manifest: list[dict],
) -> tuple[pd.DataFrame, int]:
    frames: list[pd.DataFrame] = []
    for week in range(1, 19):
        url = url_template.format(season=season, week=week)
        payload = _fetch(session, url)
        manifest.append(
            _capture(
                raw_dir / "nfl_com" / str(season) / f"reg_{week:02d}.html",
                payload,
                source="nfl_com_official_injury_page",
                url=url,
                season=season,
                week=week,
            )
        )
        frame = parse_nfl_postseason_page(
            payload.decode("utf-8", errors="replace"),
            nfl_week=week,
            source_url=url,
        )
        frame["season"] = season
        frames.append(frame)
        time.sleep(0.05)
    official = pd.concat(frames, ignore_index=True)
    official, collapsed = collapse_exact_official_duplicates(official)
    manifest.append(
        {
            "source": "nfl_com_official_semantic_dedupe",
            "season": season,
            "rows_after_exact_dedupe": int(len(official)),
            "exact_semantic_duplicate_rows_collapsed": int(collapsed),
        }
    )
    return official, 18


def _write_mismatch_diagnostics(out: Path, canonical: pd.DataFrame, *, season: int) -> dict:
    """Persist row-level discrepancies without changing any qualification denominator."""
    matched = canonical[canonical["identity_matched"]].copy()

    game_mismatch = matched.loc[~matched["game_status_agrees"]].copy()
    game_columns = [
        column
        for column in [
            "season", "week", "team", "gsis_id", "full_name", "external_player",
            "report_status", "external_game_status", "nflverse_game_normalized",
            "external_game_normalized", "practice_status", "external_practice_status",
            "source_url", "identity_match_method",
        ]
        if column in game_mismatch.columns
    ]
    game_mismatch[game_columns].to_csv(
        out / f"game_status_mismatches_{season}.csv", index=False
    )
    if len(game_mismatch):
        (
            game_mismatch.groupby(
                ["nflverse_game_normalized", "external_game_normalized"],
                dropna=False,
            )
            .size()
            .reset_index(name="rows")
            .sort_values("rows", ascending=False)
            .to_csv(out / f"game_status_mismatch_pairs_{season}.csv", index=False)
        )
    else:
        pd.DataFrame(
            columns=["nflverse_game_normalized", "external_game_normalized", "rows"]
        ).to_csv(out / f"game_status_mismatch_pairs_{season}.csv", index=False)

    practice_mismatch = matched.loc[~matched["practice_status_agrees"]].copy()
    practice_columns = [
        column
        for column in [
            "season", "week", "team", "gsis_id", "full_name", "external_player",
            "practice_status", "external_practice_status", "nflverse_practice_normalized",
            "external_practice_normalized", "report_status", "external_game_status",
            "source_url", "identity_match_method",
        ]
        if column in practice_mismatch.columns
    ]
    practice_mismatch[practice_columns].to_csv(
        out / f"practice_status_mismatches_{season}.csv", index=False
    )

    return {
        "season": int(season),
        "identity_matched_rows": int(len(matched)),
        "game_status_mismatch_rows": int(len(game_mismatch)),
        "practice_status_mismatch_rows": int(len(practice_mismatch)),
        "diagnostic_only": True,
        "qualification_logic_changed": False,
    }


def run(
    *,
    output_dir: str = "research_outputs/availability_harmonization_regular_v2",
    contract_path: str | Path = CONTRACT_PATH,
) -> dict:
    contract_path = Path(contract_path)
    contract = _load_json(contract_path)
    registry = _load_json(EXPERIMENTS_PATH)
    receipt_2025 = _load_json(RECEIPT_2025_PATH)

    governance = contract["governance"]
    if governance.get("research_only") is not True:
        raise RuntimeError("strict availability contract must remain research-only")
    for key in (
        "game_outcomes_allowed_in_source_qualification",
        "completed_2026_outcomes_allowed",
        "probability_model_built_by_this_contract",
        "probability_feature_authorized_by_this_contract",
        "production_dependency_authorized",
        "candidate_promotion_authorized",
        "postseason_V4_reopened",
    ):
        if governance.get(key) is not False:
            raise RuntimeError(f"unsafe strict availability governance flag: {key}")

    out = Path(output_dir)
    raw_dir = out / "raw"
    out.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    source_manifest: list[dict] = []

    schedule_url = contract["schedule_source"]["url"]
    schedule_payload = _fetch(session, schedule_url)
    source_manifest.append(
        _capture(
            raw_dir / "nflverse" / "games.csv",
            schedule_payload,
            source="nflverse_schedule_raw",
            url=schedule_url,
        )
    )
    schedule_raw = pd.read_csv(
        StringIO(schedule_payload.decode("utf-8")),
        usecols=SCHEDULE_HASH_COLUMNS,
        low_memory=False,
    )
    schedules, schedule_exceptions = filter_model_eligible_schedule(
        schedule_raw,
        contract["model_universe_exceptions"],
    )
    schedule_digest = schedule_subset_sha256(schedules)
    schedules.to_csv(out / "model_eligible_schedule_2022_2025.csv", index=False)
    schedule_exceptions.to_csv(out / "schedule_model_universe_exceptions.csv", index=False)
    source_manifest.append(
        {
            "source": "nflverse_schedule_model_eligible_subset",
            "rows": int(len(schedules)),
            "sha256": schedule_digest,
            "expected_sha256": contract["schedule_source"]["expected_derived_subset_sha256"],
        }
    )

    identity_payload = _fetch(session, PLAYER_MASTER_URL)
    source_manifest.append(
        _capture(
            raw_dir / "identity" / "players.csv",
            identity_payload,
            source="nflverse_players_identity",
            url=PLAYER_MASTER_URL,
        )
    )
    player_master = validate_player_master_payload(identity_payload)

    canonical_parts: list[pd.DataFrame] = []
    audits = []
    unresolved_parts: list[pd.DataFrame] = []
    exception_parts: list[pd.DataFrame] = []
    mismatch_diagnostics: list[dict] = []

    injury_source = contract["primary_state_source"]
    official_source = contract["independent_crosscheck"]
    for season in [int(x) for x in contract["target_seasons"]]:
        key = str(season)
        injury_url = injury_source["url_template"].format(season=season)
        injury_payload = _fetch(session, injury_url)
        source_manifest.append(
            _capture(
                raw_dir / "nflverse" / f"injuries_{season}.csv",
                injury_payload,
                source="nflverse_injuries",
                url=injury_url,
                season=season,
            )
        )
        injury, injury_digest = validate_strict_injury_frame(
            injury_payload,
            season=season,
            expected_rows=int(injury_source["expected_full_asset_rows"][key]),
            expected_sha256=str(injury_source["expected_sha256"][key]),
        )

        official, page_count = _collect_official_regular_season(
            session,
            season=season,
            url_template=official_source["url_template"],
            raw_dir=raw_dir,
            manifest=source_manifest,
        )
        official.to_csv(out / f"official_nfl_regular_crosscheck_{season}.csv", index=False)

        canonical, audit, unresolved, exception_rows = build_strict_season(
            injury,
            official,
            schedules,
            player_master,
            season=season,
            injury_source_sha256=injury_digest,
            official_pages_collected=page_count,
            exceptions=contract["model_universe_exceptions"],
        )
        canonical.to_csv(out / f"availability_regular_{season}_canonical.csv", index=False)
        unresolved.to_csv(out / f"official_identity_unresolved_{season}.csv", index=False)
        mismatch_diagnostics.append(_write_mismatch_diagnostics(out, canonical, season=season))
        canonical_parts.append(canonical)
        audits.append(audit)
        if not unresolved.empty:
            unresolved = unresolved.copy()
            unresolved["audit_season"] = season
            unresolved_parts.append(unresolved)
        if not exception_rows.empty:
            exception_rows = exception_rows.copy()
            exception_rows["audit_season"] = season
            exception_parts.append(exception_rows)

    canonical_all = pd.concat(canonical_parts, ignore_index=True)
    canonical_all = canonical_all.sort_values(
        ["season", "week", "team", "gsis_id"], kind="stable"
    ).reset_index(drop=True)
    canonical_all.to_csv(out / "availability_2022_2025_regular_strict.csv", index=False)
    pd.DataFrame([audit.as_dict() for audit in audits]).to_csv(
        out / "season_summaries.csv", index=False
    )
    _write_json(out / "mismatch_diagnostics.json", mismatch_diagnostics)
    if unresolved_parts:
        pd.concat(unresolved_parts, ignore_index=True, sort=False).to_csv(
            out / "official_identity_unresolved_all.csv", index=False
        )
    else:
        pd.DataFrame().to_csv(out / "official_identity_unresolved_all.csv", index=False)
    if exception_parts:
        pd.concat(exception_parts, ignore_index=True, sort=False).to_csv(
            out / "model_universe_exception_rows.csv", index=False
        )
    else:
        pd.DataFrame().to_csv(out / "model_universe_exception_rows.csv", index=False)

    prereg_ok, prereg_reasons = validate_v09b_preregistry(registry)
    receipt_ok = verify_2025_receipt(receipt_2025)
    report = evaluate_strict_harmonization(
        audits,
        contract,
        schedule_sha256=schedule_digest,
        v09b_prereg_ok=prereg_ok,
        qualified_2025_receipt_ok=receipt_ok,
    )
    report.update(
        {
            "contract_path": str(contract_path),
            "mode": "strict_regular_season_source_state_harmonization_only",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "git_sha": _git_sha(),
            "preregistration_drift_reasons": prereg_reasons,
            "diagnostic_expansion": {
                "row_level_game_status_mismatches_persisted": True,
                "row_level_practice_status_mismatches_persisted": True,
                "qualification_logic_changed": False,
                "thresholds_changed": False,
            },
            "environment": {
                "python": platform.python_version(),
                "pandas": pd.__version__,
            },
            "source_manifest": source_manifest,
        }
    )
    _write_json(out / "source_manifest.json", source_manifest)
    _write_json(out / "qualification.json", report)
    print(json.dumps(report, indent=2, sort_keys=True, default=str))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        default="research_outputs/availability_harmonization_regular_v2",
    )
    parser.add_argument(
        "--contract",
        default=str(CONTRACT_PATH),
    )
    args = parser.parse_args()
    run(output_dir=args.output_dir, contract_path=args.contract)


if __name__ == "__main__":
    main()
