"""One-shot read-only 2026 nflverse PBP availability/coverage probe.

CI-only research diagnostic. No credential, no persistent raw bytes, no stored
model features and NO prospective qualified source_verifier output.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
from io import BytesIO, StringIO
import json
import sys
from urllib.request import Request, urlopen

from research.post_week4_phase4.nflverse_epa_adapter import acquisition_evidence

RELEASE_API = "https://api.github.com/repos/nflverse/nflverse-data/releases/tags/pbp"
SCHEDULE_URL = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ASSET = "play_by_play_2026.parquet"


def get_bytes(url: str) -> tuple[bytes, str]:
    req = Request(url, headers={"User-Agent": "LevLine-research-PBP-audit/1",
                                "Accept": "application/octet-stream"})
    with urlopen(req, timeout=90) as response:
        data = response.read()
    observed = datetime.now(timezone.utc).isoformat()
    if not data:
        raise RuntimeError("No bytes acquired")
    return data, observed


def probe() -> dict:
    from pyarrow import parquet as pq  # Optional, isolated research-CI dependency only.
    metadata_raw, metadata_at = get_bytes(RELEASE_API)
    release = json.loads(metadata_raw)
    assets = [a for a in release["assets"] if a.get("name") == ASSET]
    if len(assets) != 1:
        raise RuntimeError("Current 2026 PBP release not uniquely identifiable")
    asset = assets[0]
    if asset["state"] != "uploaded" or not asset.get("digest", "").startswith("sha256:"):
        raise RuntimeError("Unpublished or unhashable release asset")
    raw, fetched_at = get_bytes(asset["browser_download_url"])
    evidence = acquisition_evidence(raw, received_utc=fetched_at,
                                   asset_id=str(asset["id"]),
                                   claimed_asset_updated_utc=asset["updated_at"])
    if len(raw) != asset["size"] or "sha256:" + evidence["payload_sha256"] != asset["digest"]:
        raise RuntimeError("Mutable asset or mismatch between released and acquired PBP")
    # pyarrow in-memory: no copy of licensed raw football data committed or archived.
    obj = pq.read_table(BytesIO(raw))
    needed = ("game_id","season","week","home_team","away_team",
              "posteam","defteam","epa","play_id")
    if not set(needed).issubset(obj.column_names):
        raise RuntimeError(f"Missing PBP schema: {sorted(set(needed)-set(obj.column_names))}")
    data = obj.select(needed).to_pydict()
    games, valid_epa = Counter(), Counter()
    team_presence = {}
    for i,gid in enumerate(data["game_id"]):
        if data["season"][i] != 2026:
            raise RuntimeError("Prior/future season leakage in 2026 PBP asset")
        if gid is None:
            continue
        games[gid] += 1
        h,a = data["home_team"][i], data["away_team"][i]
        if not h or not a or h == a:
            raise RuntimeError("Malformed PBP team identity")
        key = (h,a,data["week"][i])
        if gid in team_presence and team_presence[gid] != key:
            raise RuntimeError("Mixed game/team/week identity")
        team_presence[gid] = key
        if data["posteam"][i] is not None and data["defteam"][i] is not None and data["epa"][i] is not None:
            valid_epa[gid] += 1
    if not games:
        raise RuntimeError("No 2026 PBP games in released asset")
    schedule_raw, schedule_at = get_bytes(SCHEDULE_URL)
    schedule = list(csv.DictReader(StringIO(schedule_raw.decode("utf-8-sig"))))
    completed = {x["game_id"] for x in schedule
                 if x.get("season")=="2026" and x.get("game_type")=="REG"
                 and x.get("home_score") not in ("",None) and x.get("away_score") not in ("",None)}
    missing = sorted(completed - set(games))
    without_valid_epa = sorted(g for g in completed if valid_epa[g] == 0)
    report = {
      "status": "RELEASE_BYTES_VERIFIED_COVERAGE_CHECK" if not missing and not without_valid_epa else "INCOMPLETE_RELEASE_COVERAGE",
      "asset_name": ASSET, "asset_id":asset["id"],"asset_size":len(raw),
      "asset_sha256":evidence["payload_sha256"],"asset_updated_utc":asset["updated_at"],
      "metadata_received_utc":metadata_at,"download_completed_utc":fetched_at,
      "schedule_received_utc":schedule_at,
      "schedule_sha256":hashlib.sha256(schedule_raw).hexdigest(),
      "observed_schedule_completed_games":len(completed),
      "pbp_distinct_game_ids":len(games),
      "pbp_games_missing_from_completed_schedule":missing,
      "completed_games_without_valid_epa":without_valid_epa,
      "minimum_recorded_plays_in_pbp":min(games.values()),
      "maximum_recorded_plays_in_pbp":max(games.values()),
      "complete_source_play_manifest_independently_verified":False,
      "original_release_first_availability_verified":False,
      "source_rights_independently_cleared":False,
      "independent_acquisition_clock_verified":False,
      "prospective_qualified":False,
      "training_or_production_modified":False,
    }
    return report


if __name__ == "__main__":
    try:
        report = probe()
        print(json.dumps(report, sort_keys=True, indent=2))
        if report["status"] != "RELEASE_BYTES_VERIFIED_COVERAGE_CHECK":
            sys.exit(2)
    except Exception as exc:
        print(json.dumps({"status":"FAIL_CLOSED","error_type":type(exc).__name__,
                          "error":str(exc),"prospective_qualified":False}))
        sys.exit(1)
