from __future__ import annotations

"""Collect and audit the preregistered 2025 all-position availability reconstruction."""

import argparse
from datetime import datetime, timezone
from io import StringIO
import json
from pathlib import Path
import time

import pandas as pd
import requests

from nfl_forecast.availability_2025_reconstruction import (
    NFLVERSE_EXPECTED_SHA256,
    REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1,
    build_canonical_reconstruction,
    git_blob_sha1,
    parse_nfl_postseason_page,
    sha256_bytes,
    summarize_reconstruction,
    validate_nflverse_payload,
)

NFLVERSE_URL = "https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_2025.csv"
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
REGULAR_MIRROR_URL = "https://raw.githubusercontent.com/Zinkelburger/Fantasy-Football-Tool/44d48a9afc33130897030ac1c47eb6ad32b14513/research/injury_predictor/nfl_injuries_2021_2025.csv"
NFL_REG_URL = "https://www.nfl.com/injuries/league/2025/reg{week}"
NFL_POST_URL = "https://www.nfl.com/injuries/league/2025/post{page_week}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; LevLineResearch/1.0; historical-source-audit)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
TARGET_GAME_TYPES = {"REG", "WC", "DIV", "CON", "SB"}


def _fetch(session: requests.Session, url: str, *, attempts: int = 4) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            response = session.get(url, headers=HEADERS, timeout=45, allow_redirects=True)
            response.raise_for_status()
            return response.content
        except Exception as exc:  # pragma: no cover - live-network behavior
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"failed to fetch {url}: {last_error}")


def _write_bytes(path: Path, payload: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {
        "path": str(path),
        "bytes": len(payload),
        "sha256": sha256_bytes(payload),
        "git_blob_sha1": git_blob_sha1(payload),
    }


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _collect_auxiliary_regular_mirror(session: requests.Session, raw_dir: Path, manifest: dict) -> None:
    """Preserve the pinned mirror as supplemental evidence; it is not a completeness gate."""
    record: dict = {
        "source": "footballdb_regular_github_mirror_supplemental",
        "url": REGULAR_MIRROR_URL,
        "expected_git_blob_sha1": REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1,
        "qualification_dependency": False,
    }
    try:
        payload = _fetch(session, REGULAR_MIRROR_URL)
        record.update(_write_bytes(raw_dir / "footballdb_mirror" / "nfl_injuries_2021_2025.csv", payload))
        record["git_blob_identity_matches"] = record["git_blob_sha1"] == REGULAR_MIRROR_EXPECTED_GIT_BLOB_SHA1
        frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
        season = frame[pd.to_numeric(frame.get("season"), errors="coerce").eq(2025)].copy()
        record["observed_2025_weeks"] = sorted(pd.to_numeric(season.get("week"), errors="coerce").dropna().astype(int).unique().tolist())
        record["observed_2025_rows"] = int(len(season))
    except Exception as exc:  # supplemental evidence must never masquerade as primary coverage
        record["collection_error"] = str(exc)
    manifest["sources"].append(record)


def collect(output_dir: Path) -> dict:
    session = requests.Session()
    raw_dir = output_dir / "raw"
    manifest: dict = {
        "contract": "research/availability/2025_reconstruction_contract.json",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "season": 2025,
        "production_authorized": False,
        "probability_feature_authorized": False,
        "historical_game_status_feature_authorized": False,
        "completed_2026_outcomes_used": False,
        "sources": [],
    }

    nflverse_payload = _fetch(session, NFLVERSE_URL)
    nflverse_record = _write_bytes(raw_dir / "nflverse" / "injuries_2025.csv", nflverse_payload)
    nflverse_record.update({"source": "nflverse_injuries_2025", "url": NFLVERSE_URL})
    manifest["sources"].append(nflverse_record)
    if nflverse_record["sha256"] != NFLVERSE_EXPECTED_SHA256:
        _write_json(output_dir / "source_manifest.json", manifest)
        raise RuntimeError("nflverse 2025 injury source digest no longer matches the preregistered asset")
    nflverse = validate_nflverse_payload(nflverse_payload)

    schedule_payload = _fetch(session, SCHEDULE_URL)
    schedule_record = _write_bytes(raw_dir / "nflverse" / "games.csv", schedule_payload)
    schedule_record.update({"source": "nflverse_schedule", "url": SCHEDULE_URL})
    manifest["sources"].append(schedule_record)
    schedules = pd.read_csv(raw_dir / "nflverse" / "games.csv", low_memory=False)
    if "game_type" in schedules.columns:
        schedules = schedules[schedules["game_type"].isin(TARGET_GAME_TYPES)].copy()

    _collect_auxiliary_regular_mirror(session, raw_dir, manifest)

    official_frames: list[pd.DataFrame] = []
    official_pages = 0
    for week in range(1, 19):
        url = NFL_REG_URL.format(week=week)
        payload = _fetch(session, url)
        record = _write_bytes(raw_dir / "nfl_com" / f"reg_{week:02d}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "nfl_week": week})
        manifest["sources"].append(record)
        official_frames.append(parse_nfl_postseason_page(payload.decode("utf-8", errors="replace"), nfl_week=week, source_url=url))
        official_pages += 1
        time.sleep(0.10)

    for page_week, nfl_week in {1: 19, 2: 20, 3: 21, 4: 22}.items():
        url = NFL_POST_URL.format(page_week=page_week)
        payload = _fetch(session, url)
        record = _write_bytes(raw_dir / "nfl_com" / f"post_{page_week}.html", payload)
        record.update({"source": "nfl_com_official_injury_page", "url": url, "nfl_week": nfl_week})
        manifest["sources"].append(record)
        official_frames.append(parse_nfl_postseason_page(payload.decode("utf-8", errors="replace"), nfl_week=nfl_week, source_url=url))
        official_pages += 1
        time.sleep(0.10)

    if official_pages != 22:
        raise RuntimeError(f"expected 22 official NFL injury pages, collected {official_pages}")
    external = pd.concat(official_frames, ignore_index=True)
    external.to_csv(output_dir / "official_nfl_report_crosscheck_2025.csv", index=False)

    canonical = build_canonical_reconstruction(nflverse, external, schedules)
    canonical.to_csv(output_dir / "availability_2025_canonical.csv", index=False)
    unresolved = canonical[~canonical["fully_qualified_practice_state"]].copy()
    unresolved.to_csv(output_dir / "availability_2025_unresolved.csv", index=False)
    game_disagreements = canonical[canonical["identity_matched"] & ~canonical["game_status_agrees"]].copy()
    game_disagreements.to_csv(output_dir / "game_status_disagreements_diagnostic.csv", index=False)

    # Existing summary requires 18 regular weeks plus four postseason pages, which is exactly
    # the preregistered all-22-page official coverage gate in contract v3.
    summary = summarize_reconstruction(canonical, external, postseason_pages=4)
    _write_json(output_dir / "qualification.json", summary.as_dict())
    _write_json(output_dir / "source_manifest.json", manifest)

    result = summary.as_dict()
    result.update({
        "official_nfl_pages_collected": official_pages,
        "unresolved_practice_state_rows": int(len(unresolved)),
        "game_status_disagreement_rows": int(len(game_disagreements)),
        "nflverse_sha256": nflverse_record["sha256"],
        "schedule_sha256": schedule_record["sha256"],
    })
    print(json.dumps(result, indent=2, sort_keys=True))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/availability_2025_reconstruction")
    parser.add_argument("--require-qualified", action="store_true")
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    result = collect(output)
    if args.require_qualified and not result["qualified"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
