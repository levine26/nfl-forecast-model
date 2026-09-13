from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

CONTRACT_ID = "V09B-MODERN-GAMEBOOK-LOCATOR-SNAPSHOT-V1"
EXPECTED_BY_SEASON = {2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272}
EXPECTED_SHA256 = "d26b2cab8bdd05c223de0239cfaf70b09b75b6487c8ba2c353bd7749d1730351"
EXPECTED_BYTES = 154920
EXPECTED_V1_FAILURES = {"2017_01_ARI_DET", "2019_15_BUF_PIT", "2021_13_BAL_PIT"}


def load_qualified_artifact(path: Path, season: int) -> list[dict[str, object]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["season"] == season
    assert payload["canonical_games"] == EXPECTED_BY_SEASON[season]
    assert payload["expected_games"] == EXPECTED_BY_SEASON[season]
    assert payload["qualified_gamebook_locators"] == EXPECTED_BY_SEASON[season]
    assert payload["locator_coverage_rate"] == 1.0
    assert payload["all_gamebook_locators_qualified"] is True
    assert payload["game_outcomes_used"] == 0
    assert payload["completed_2026_outcomes_used"] == 0
    rows = payload["rows"]
    assert len(rows) == EXPECTED_BY_SEASON[season]
    return rows


def build_snapshot(artifact_dir: Path) -> tuple[bytes, dict[str, object]]:
    rows: list[dict[str, object]] = []
    for season in EXPECTED_BY_SEASON:
        rows.extend(load_qualified_artifact(artifact_dir / f"{season}.json", season))
    assert len(rows) == 1296
    assert len({str(r["game_id"]) for r in rows}) == 1296
    assert all(r["qualified_locator"] is True for r in rows)
    assert all(r["gamebook_extraction_method"] == "download_anchor" for r in rows)

    ordered = sorted(rows, key=lambda r: (int(r["season"]), int(r["week"]), str(r["game_id"])))
    game_ids: list[str] = []
    urls: list[str] = []
    lines: list[str] = []
    gc_methods: Counter[str] = Counter()
    for row in ordered:
        game_id = str(row["game_id"])
        url = str(row["gamebook_url"])
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.hostname == "static.www.nfl.com"
        game_ids.append(game_id)
        urls.append(url)
        lines.append(f"{game_id}\t{url}\n")
        gc_methods[str(row["game_center_resolution_method"])] += 1

    assert len(set(game_ids)) == 1296
    assert len(set(urls)) == 1296
    assert gc_methods == Counter({"deterministic_slug": 1295, "first_party_week_schedule_fallback": 1})
    raw = "".join(lines).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    assert digest == EXPECTED_SHA256, digest
    assert len(raw) == EXPECTED_BYTES
    frozen = {line.split("\t", 1)[0] for line in raw.decode().splitlines()}
    assert EXPECTED_V1_FAILURES <= frozen
    receipt = {
        "receipt_version": 1,
        "contract_id": CONTRACT_ID,
        "snapshot_sha256": digest,
        "snapshot_bytes": len(raw),
        "snapshot_rows": len(rows),
        "unique_game_ids": len(set(game_ids)),
        "unique_gamebook_urls": len(set(urls)),
        "qualified_locator_rows": 1296,
        "gamebook_extraction_method_counts": {"download_anchor": 1296},
        "game_center_resolution_method_counts": dict(sorted(gc_methods.items())),
        "v1_failed_live_rediscovery_games_present": sorted(EXPECTED_V1_FAILURES),
        "snapshot_is_downstream_discovery_authority": True,
        "snapshot_is_label_authority": False,
        "modern_raw_source_bytes_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
    }
    return raw, receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    raw, receipt = build_snapshot(args.artifact_dir)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "locator_snapshot.tsv").write_bytes(raw)
    (args.output_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
