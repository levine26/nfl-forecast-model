from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

import polars as pl

from research.levline4_prospective_inactive_execution_v1 import (
    CONTRACT_ID,
    audit_resolver_rows,
    build_resolver_observations,
    execute,
    select_matching_article,
)


def _html(*, ari_name: str = "Kyler Murray", lac_name: str = "Justin Herbert") -> bytes:
    return f"""
    <html><body>
      <h3>Cardinals</h3><ul><li>QB {ari_name}</li></ul>
      <h3>Chargers</h3><ul><li>QB {lac_name} (Emergency Third QB)</li></ul>
    </body></html>
    """.encode("utf-8")


def _archive(tmp_path: Path, *, include_matching_article: bool = True, duplicate_url: bool = False) -> tuple[Path, str]:
    root = tmp_path / "archive"
    raw_dir = root / "raw"
    raw_dir.mkdir(parents=True)
    raw = _html()
    sha = hashlib.sha256(raw).hexdigest()
    relpath = f"raw/{sha}.html.gz"
    with gzip.open(root / relpath, "wb", mtime=0) as handle:
        handle.write(raw)
    sources = [
        {
            "source_kind": "nfl_news_index",
            "url": "https://www.nfl.com/news/",
            "http_status": 200,
            "raw_body_sha256": "0" * 64,
            "raw_object_relpath": "raw/index.html.gz",
        }
    ]
    if include_matching_article:
        sources.append(
            {
                "source_kind": "nfl_inactives_news_article",
                "url": "https://www.nfl.com/news/2026-nfl-season-week-2-inactives/",
                "http_status": 200,
                "raw_body_sha256": sha,
                "raw_object_relpath": relpath,
            }
        )
        if duplicate_url:
            sources.append(
                {
                    "source_kind": "nfl_inactives_news_article",
                    "url": "https://www.nfl.com/news/aaa-duplicate-current-body/",
                    "http_status": 200,
                    "raw_body_sha256": sha,
                    "raw_object_relpath": relpath,
                }
            )
    observation = {
        "archive_id": "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1",
        "captured_at_utc": "2026-09-20T16:00:00Z",
        "due_games": [
            {
                "game_id": "2026_02_ARI_LAC",
                "away_team": "ARI",
                "home_team": "LAC",
                "kickoff_utc": "2026-09-20T17:05:00+00:00",
                "minutes_to_kickoff": 65.0,
            }
        ],
        "sources": sources,
    }
    (root / "observations.jsonl").write_text(json.dumps(observation) + "\n", encoding="utf-8")
    return root, sha


def _weekly_projection(path: Path) -> str:
    frame = pl.DataFrame(
        [
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "ARI",
                "gsis_id": "00-ARI-QB",
                "jersey_number": "1",
                "first_name": "Kyler",
                "football_name": "Kyler",
                "last_name": "Murray",
            },
            {
                "season": 2026,
                "game_type": "REG",
                "week": 2,
                "team": "LAC",
                "gsis_id": "00-LAC-QB",
                "jersey_number": "10",
                "first_name": "Justin",
                "football_name": "Justin",
                "last_name": "Herbert",
            },
        ]
    )
    frame.write_parquet(path, compression="zstd", statistics=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _global_projection(path: Path, *, contradiction: bool = False) -> str:
    frame = pl.DataFrame(
        [
            {
                "gsis_id": "00-WRONG" if contradiction else "00-ARI-QB",
                "display_name": "Kyler Murray",
                "common_first_name": "Kyler",
                "first_name": "Kyler",
                "last_name": "Murray",
                "position_group": "QB",
                "position": "QB",
            },
            {
                "gsis_id": "00-LAC-QB",
                "display_name": "Justin Herbert",
                "common_first_name": "Justin",
                "first_name": "Justin",
                "last_name": "Herbert",
                "position_group": "QB",
                "position": "QB",
            },
        ]
    )
    frame.write_parquet(path, compression="zstd", statistics=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_matching_article_deduplicates_identical_bodies(tmp_path: Path) -> None:
    archive, sha = _archive(tmp_path, duplicate_url=True)
    observation = json.loads((archive / "observations.jsonl").read_text().splitlines()[0])
    selected, matches = select_matching_article(archive_dir=archive, observation=observation)
    assert selected is not None
    assert selected["raw_sha256"] == sha
    assert len(matches) == 2
    assert selected["source"]["url"].endswith("aaa-duplicate-current-body/")


def test_resolver_input_excludes_position_and_emergency_semantics() -> None:
    rows = [
        {
            "team": "ARI",
            "player_name_rendered": "Kyler Murray",
            "position_rendered": "QB",
            "emergency_third_qb": True,
        }
    ]
    observations = build_resolver_observations(
        cohort_rows=rows,
        week=2,
        raw_sha256="a" * 64,
        source_known_by_utc="2026-09-20T16:00:00Z",
    )
    assert len(observations) == 1
    assert "position_rendered" not in observations[0]
    assert "emergency_third_qb" not in observations[0]
    assert observations[0]["observation_id"]


def test_execute_preserves_waiting_attempt_without_reading_identity_sources(tmp_path: Path) -> None:
    archive, _ = _archive(tmp_path, include_matching_article=False)
    receipt = execute(
        archive_dir=archive,
        weekly_projection_path=tmp_path / "missing-weekly.parquet",
        global_projection_path=tmp_path / "missing-global.parquet",
        output_dir=tmp_path / "out",
    )
    assert receipt["status"] == "WAITING_FOR_MATCHING_OFFICIAL_ARTICLE"
    assert receipt["resolver_executed"] is False
    assert receipt["production_authorized"] is False
    assert (tmp_path / "out" / "attempts.jsonl").exists()


def test_first_real_execution_resolves_and_cross_source_corroborates_without_authority(tmp_path: Path) -> None:
    archive, raw_sha = _archive(tmp_path)
    weekly = tmp_path / "weekly.parquet"
    global_source = tmp_path / "global.parquet"
    weekly_sha = _weekly_projection(weekly)
    global_sha = _global_projection(global_source)
    out = tmp_path / "out"
    receipt = execute(
        archive_dir=archive,
        weekly_projection_path=weekly,
        global_projection_path=global_source,
        output_dir=out,
        expected_weekly_projection_sha256=weekly_sha,
        expected_global_projection_sha256=global_sha,
    )
    assert receipt["status"] == "PASS_EVIDENCE_CAPTURED"
    assert receipt["selected_raw_html_sha256"] == raw_sha
    assert receipt["resolver_receipt"]["resolution_counts"]["RESOLVED_EXACT_UNIQUE"] == 2
    assert receipt["cross_source_audit_counts"] == {"CROSS_SOURCE_CORROBORATED": 2}
    assert receipt["cross_source_contradictions"] == 0
    assert receipt["global_source_used_as_fallback"] is False
    assert receipt["real_execution_is_self_qualifying"] is False
    assert receipt["player_identity_to_gsis_qualified"] is False
    assert receipt["production_authorized"] is False
    assert (out / "dependencies" / f"weekly-identity-{weekly_sha}.parquet").exists()
    assert (out / "dependencies" / f"global-identity-{global_sha}.parquet").exists()


def test_global_unique_disagreement_is_preserved_as_contradiction(tmp_path: Path) -> None:
    global_source = tmp_path / "global.parquet"
    global_sha = _global_projection(global_source, contradiction=True)
    resolver_rows = [
        {
            "observation_id": "obs-1",
            "week": 2,
            "team": "ARI",
            "player_name_rendered": "Kyler Murray",
            "normalized_name": "kyler murray",
            "resolution_state": "RESOLVED_EXACT_UNIQUE",
            "resolved_gsis_id": "00-ARI-QB",
        }
    ]
    rows, counts = audit_resolver_rows(
        resolver_rows,
        global_projection_path=global_source,
        expected_global_projection_sha256=global_sha,
    )
    assert counts == {"CROSS_SOURCE_CONTRADICTION": 1}
    assert rows[0]["global_display_name_candidate_gsis_ids"] == ["00-WRONG"]
    assert rows[0]["global_source_used_as_fallback"] is False
    assert rows[0]["player_identity_to_gsis_qualified"] is False


def test_contract_identity_is_stable() -> None:
    assert CONTRACT_ID == "LEVLINE-4-2026-PROSPECTIVE-INACTIVE-EXECUTION-V1"
