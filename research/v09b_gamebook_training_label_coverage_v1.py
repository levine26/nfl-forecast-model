from __future__ import annotations

"""Fail-closed source-only coverage audit for V09B historical active/inactive labels.

This module does not construct P(active) labels and does not fit a model. It asks a
narrower prerequisite question: can every 2012-2021 regular-season game be mapped
reproducibly to an archived official NFL Game Book source using the historical GSIS
identifier and home-team Gamebook filename convention?

The audit intentionally separates archive/source coverage from target semantics. Even a
QUALIFIED coverage result does not authorize V09B fitting; the independent semantic
crosscheck remains mandatory under V09B-TRAINING-ACTIVE-LABEL-SOURCE-V1.
"""

import argparse
from collections import defaultdict
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import re
from typing import Any, Iterable

import pandas as pd
import requests

CONTRACT_PATH = Path(
    "research/availability/v09b_gamebook_training_label_coverage_contract_v1.json"
)
OUTPUT_DIR_DEFAULT = Path("research_outputs/v09b_gamebook_training_label_coverage_v1")
TRAINING_SEASONS = tuple(range(2012, 2022))
CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
CDX_PREFIX = "www.nfl.com/liveupdate/gamecenter/"
GAMEBOOK_RE = re.compile(
    r"/liveupdate/gamecenter/(?P<gsis>\d+)/(?P<team>[A-Za-z0-9]+)_Gamebook\.pdf(?:$|[?#])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ArchiveSource:
    timestamp: str
    original: str
    statuscode: str
    digest: str
    mimetype: str
    length: str
    gsis: str
    team_code: str


def _load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _stable_schedule_hash(frame: pd.DataFrame) -> str:
    columns = ["season", "week", "game_type", "game_id", "gsis", "home_team", "away_team"]
    out = frame[columns].copy().sort_values(
        ["season", "week", "game_id"], kind="stable", na_position="last"
    )
    for column in columns:
        out[column] = out[column].fillna("").astype(str)
    return _sha256_bytes(out.to_csv(index=False, lineterminator="\n").encode("utf-8"))


def normalize_gsis(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    if re.fullmatch(r"\d+\.0", text):
        text = text[:-2]
    return text if text.isdigit() else ""


def home_code_candidates(home_team: str, contract: dict[str, Any]) -> list[str]:
    home = str(home_team or "").strip().upper()
    aliases = contract.get("legacy_home_code_aliases", {}).get(home, [home])
    out: list[str] = []
    for value in aliases:
        code = str(value or "").strip().upper()
        if code and code not in out:
            out.append(code)
    if home and home not in out:
        out.insert(0, home)
    return out


def parse_cdx_json(payload: Any) -> list[ArchiveSource]:
    if not isinstance(payload, list) or not payload:
        return []
    header = payload[0]
    if not isinstance(header, list):
        raise ValueError("CDX JSON header is not a list")
    required = ["timestamp", "original", "statuscode", "digest", "mimetype", "length"]
    missing = [field for field in required if field not in header]
    if missing:
        raise ValueError(f"CDX response missing fields: {missing}")
    index = {name: header.index(name) for name in required}
    sources: list[ArchiveSource] = []
    for row in payload[1:]:
        if not isinstance(row, list) or len(row) < len(header):
            continue
        original = str(row[index["original"]] or "")
        match = GAMEBOOK_RE.search(original)
        if not match:
            continue
        sources.append(
            ArchiveSource(
                timestamp=str(row[index["timestamp"]] or ""),
                original=original,
                statuscode=str(row[index["statuscode"]] or ""),
                digest=str(row[index["digest"]] or ""),
                mimetype=str(row[index["mimetype"]] or ""),
                length=str(row[index["length"]] or ""),
                gsis=match.group("gsis"),
                team_code=match.group("team").upper(),
            )
        )
    return sources


def fetch_cdx_index(
    session: Any = requests,
    *,
    timeout_seconds: int = 120,
) -> tuple[list[ArchiveSource], dict[str, Any]]:
    params: list[tuple[str, str]] = [
        ("url", CDX_PREFIX),
        ("matchType", "prefix"),
        ("output", "json"),
        ("fl", "timestamp,original,statuscode,digest,mimetype,length"),
        ("filter", "statuscode:200"),
        ("filter", r"original:.*_Gamebook\.pdf"),
        ("collapse", "urlkey"),
        ("limit", "150000"),
    ]
    response = session.get(
        CDX_ENDPOINT,
        params=params,
        timeout=timeout_seconds,
        headers={"User-Agent": "nfl-forecast-model research source audit/1.0"},
    )
    response.raise_for_status()
    raw = response.content
    payload = response.json()
    sources = parse_cdx_json(payload)
    metadata = {
        "endpoint": str(getattr(response, "url", CDX_ENDPOINT)),
        "http_status": int(getattr(response, "status_code", 200)),
        "response_sha256": _sha256_bytes(raw),
        "response_bytes": len(raw),
        "parsed_gamebook_urls": len(sources),
    }
    return sources, metadata


def index_sources(sources: Iterable[ArchiveSource]) -> dict[tuple[str, str], list[ArchiveSource]]:
    out: dict[tuple[str, str], list[ArchiveSource]] = defaultdict(list)
    for source in sources:
        out[(source.gsis, source.team_code)].append(source)
    for key in out:
        out[key] = sorted(out[key], key=lambda item: (item.timestamp, item.original))
    return dict(out)


def resolve_game_source(
    *,
    gsis: str,
    home_team: str,
    source_index: dict[tuple[str, str], list[ArchiveSource]],
    contract: dict[str, Any],
) -> tuple[ArchiveSource | None, list[ArchiveSource]]:
    candidates: list[ArchiveSource] = []
    for code in home_code_candidates(home_team, contract):
        candidates.extend(source_index.get((gsis, code), []))
    unique: dict[str, ArchiveSource] = {}
    for source in candidates:
        unique.setdefault(source.original, source)
    ordered = sorted(
        unique.values(),
        key=lambda item: (
            home_code_candidates(home_team, contract).index(item.team_code)
            if item.team_code in home_code_candidates(home_team, contract)
            else 999,
            item.timestamp,
            item.original,
        ),
    )
    return (ordered[0] if ordered else None), ordered


def _load_schedule() -> pd.DataFrame:
    import nflreadpy as nfl

    schedule = nfl.load_schedules(list(TRAINING_SEASONS)).to_pandas()
    required = {"season", "week", "game_type", "game_id", "gsis", "home_team", "away_team"}
    missing = required - set(schedule.columns)
    if missing:
        raise ValueError(f"schedule missing required fields: {sorted(missing)}")
    frame = schedule.loc[schedule["game_type"].astype(str).eq("REG"), sorted(required)].copy()
    frame["season"] = pd.to_numeric(frame["season"], errors="raise").astype(int)
    frame["week"] = pd.to_numeric(frame["week"], errors="raise").astype(int)
    frame = frame.loc[frame["season"].isin(TRAINING_SEASONS)].copy()
    frame["gsis_normalized"] = frame["gsis"].map(normalize_gsis)
    return frame.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)


def build_source_map(
    schedule: pd.DataFrame,
    sources: list[ArchiveSource],
    contract: dict[str, Any],
) -> pd.DataFrame:
    source_index = index_sources(sources)
    rows: list[dict[str, Any]] = []
    for record in schedule.to_dict(orient="records"):
        gsis = str(record["gsis_normalized"])
        chosen, candidates = resolve_game_source(
            gsis=gsis,
            home_team=str(record["home_team"]),
            source_index=source_index,
            contract=contract,
        )
        rows.append(
            {
                "season": int(record["season"]),
                "week": int(record["week"]),
                "game_id": str(record["game_id"]),
                "gsis": gsis,
                "away_team": str(record["away_team"]),
                "home_team": str(record["home_team"]),
                "home_code_candidates": "|".join(
                    home_code_candidates(str(record["home_team"]), contract)
                ),
                "archive_found": chosen is not None,
                "archive_candidate_count": len(candidates),
                "archive_ambiguous": len(candidates) > 1,
                "archive_timestamp": chosen.timestamp if chosen else "",
                "archive_original": chosen.original if chosen else "",
                "archive_digest": chosen.digest if chosen else "",
                "archive_mimetype": chosen.mimetype if chosen else "",
                "archive_length": chosen.length if chosen else "",
            }
        )
    return pd.DataFrame(rows)


def _select_sample(source_map: pd.DataFrame, per_season: int) -> pd.DataFrame:
    selected: list[pd.DataFrame] = []
    for season in TRAINING_SEASONS:
        group = source_map.loc[
            (source_map["season"] == season) & source_map["archive_found"]
        ].sort_values(["week", "game_id"], kind="stable")
        if group.empty:
            continue
        if per_season <= 1:
            positions = [0]
        elif per_season == 2:
            positions = [0, len(group) - 1]
        else:
            positions = [0, len(group) // 2, len(group) - 1]
            if per_season > 3:
                positions.extend(
                    round(i * (len(group) - 1) / (per_season - 1)) for i in range(1, per_season - 1)
                )
        deduped: list[int] = []
        for position in positions:
            value = int(max(0, min(len(group) - 1, position)))
            if value not in deduped:
                deduped.append(value)
        selected.append(group.iloc[deduped[:per_season]])
    if not selected:
        return source_map.iloc[0:0].copy()
    return pd.concat(selected, ignore_index=True)


def _pdf_text(data: bytes, max_pages: int = 4) -> str:
    from pypdf import PdfReader

    reader = PdfReader(BytesIO(data), strict=False)
    chunks: list[str] = []
    for page in reader.pages[:max_pages]:
        chunks.append(page.extract_text() or "")
    return "\n".join(chunks)


def replay_url(timestamp: str, original: str) -> str:
    return f"https://web.archive.org/web/{timestamp}id_/{original}"


def evaluate_sample_semantics(
    sample: pd.DataFrame,
    *,
    session: Any = requests,
    timeout_seconds: int = 60,
    max_pdf_bytes: int = 20_000_000,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in sample.to_dict(orient="records"):
        url = replay_url(str(row["archive_timestamp"]), str(row["archive_original"]))
        result: dict[str, Any] = {
            "season": int(row["season"]),
            "week": int(row["week"]),
            "game_id": str(row["game_id"]),
            "gsis": str(row["gsis"]),
            "archive_timestamp": str(row["archive_timestamp"]),
            "archive_original": str(row["archive_original"]),
            "replay_url": url,
            "download_ok": False,
            "not_active_structure": False,
            "did_not_play_structure": False,
            "pdf_sha256": "",
            "bytes": 0,
            "error": "",
        }
        try:
            response = session.get(
                url,
                timeout=timeout_seconds,
                headers={"User-Agent": "nfl-forecast-model research source audit/1.0"},
            )
            response.raise_for_status()
            data = bytes(response.content)
            if len(data) > max_pdf_bytes:
                raise ValueError(f"archived PDF exceeds max_pdf_bytes={max_pdf_bytes}")
            if not data.startswith(b"%PDF"):
                raise ValueError("archive replay did not return PDF bytes")
            text = " ".join(_pdf_text(data).upper().split())
            result.update(
                {
                    "download_ok": True,
                    "not_active_structure": "NOT ACTIVE" in text,
                    "did_not_play_structure": "DID NOT PLAY" in text,
                    "pdf_sha256": _sha256_bytes(data),
                    "bytes": len(data),
                }
            )
        except Exception as exc:  # source failures are evidence, not CI exceptions
            result["error"] = str(exc)[:1000]
        results.append(result)
    return results


def summarize(
    *,
    schedule: pd.DataFrame,
    source_map: pd.DataFrame,
    sample_results: list[dict[str, Any]],
    cdx_metadata: dict[str, Any],
    contract: dict[str, Any],
) -> dict[str, Any]:
    expected = {
        int(k): int(v)
        for k, v in contract["source_universe"]["expected_regular_season_games_by_season"].items()
    }
    metrics_by_season: dict[str, Any] = {}
    blockers: list[str] = []

    for season in TRAINING_SEASONS:
        sched = schedule.loc[schedule["season"] == season]
        mapped = source_map.loc[source_map["season"] == season]
        expected_games = expected[season]
        found = int(mapped["archive_found"].sum()) if len(mapped) else 0
        ambiguous = int(mapped["archive_ambiguous"].sum()) if len(mapped) else 0
        missing_gsis = int((sched["gsis_normalized"] == "").sum()) if len(sched) else expected_games
        coverage = found / len(mapped) if len(mapped) else 0.0
        metrics_by_season[str(season)] = {
            "expected_games_contract": expected_games,
            "schedule_games": int(len(sched)),
            "missing_gsis": missing_gsis,
            "archive_games_found": found,
            "archive_games_missing": int(len(mapped) - found),
            "archive_coverage_rate": coverage,
            "ambiguous_game_source_mappings": ambiguous,
        }
        if len(sched) != expected_games:
            blockers.append(
                f"schedule expected-game-count gate failed: {season} expected {expected_games} got {len(sched)}"
            )
        if missing_gsis:
            blockers.append(f"schedule GSIS gate failed: {season} missing {missing_gsis}")
        if coverage != 1.0:
            blockers.append(
                f"archive coverage gate failed: {season} {found}/{len(mapped)} = {coverage:.6f}"
            )
        if ambiguous:
            blockers.append(f"archive mapping ambiguity gate failed: {season} {ambiguous}")

    matched = source_map.loc[source_map["archive_found"]]
    missing_timestamp = int((matched["archive_timestamp"].astype(str).str.len() == 0).sum())
    missing_digest = int((matched["archive_digest"].astype(str).str.len() == 0).sum())
    if missing_timestamp:
        blockers.append(f"archive provenance timestamp gate failed: {missing_timestamp}")
    if missing_digest:
        blockers.append(f"archive provenance digest gate failed: {missing_digest}")

    required_sample = int(contract["frozen_qualification_gates"]["sample_games_per_season"]) * len(
        TRAINING_SEASONS
    )
    downloads = sum(bool(row.get("download_ok")) for row in sample_results)
    not_active = sum(bool(row.get("not_active_structure")) for row in sample_results)
    did_not_play = sum(bool(row.get("did_not_play_structure")) for row in sample_results)
    sample_count = len(sample_results)
    if sample_count != required_sample:
        blockers.append(f"sample cardinality gate failed: required {required_sample} got {sample_count}")
    if sample_count == 0 or downloads != sample_count:
        blockers.append(f"sample PDF download gate failed: {downloads}/{sample_count}")
    if sample_count == 0 or not_active != sample_count:
        blockers.append(f"sample Not Active structure gate failed: {not_active}/{sample_count}")
    if sample_count == 0 or did_not_play != sample_count:
        blockers.append(f"sample Did Not Play structure gate failed: {did_not_play}/{sample_count}")

    total_schedule = len(schedule)
    total_found = int(source_map["archive_found"].sum()) if len(source_map) else 0
    total_coverage = total_found / len(source_map) if len(source_map) else 0.0
    expected_total = int(contract["source_universe"]["expected_regular_season_games_total"])
    if total_schedule != expected_total:
        blockers.append(
            f"total schedule expected-game-count gate failed: expected {expected_total} got {total_schedule}"
        )
    if total_coverage != 1.0:
        blockers.append(
            f"total archive coverage gate failed: {total_found}/{len(source_map)} = {total_coverage:.6f}"
        )

    coverage_qualified = not blockers
    return {
        "contract_id": contract["contract_id"],
        "technical_status": "QUALIFIED" if coverage_qualified else "BLOCKED",
        "historical_gamebook_coverage_qualified": coverage_qualified,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "schedule_source": "nflreadpy.load_schedules",
        "schedule_subset_sha256": _stable_schedule_hash(schedule),
        "cdx_index": cdx_metadata,
        "metrics": {
            "expected_games_contract": expected_total,
            "schedule_games": total_schedule,
            "archive_games_found": total_found,
            "archive_games_missing": int(len(source_map) - total_found),
            "archive_coverage_rate": total_coverage,
            "ambiguous_game_source_mappings": int(source_map["archive_ambiguous"].sum()),
            "matched_rows_missing_timestamp": missing_timestamp,
            "matched_rows_missing_digest": missing_digest,
            "sample_games": sample_count,
            "sample_pdf_downloads_ok": downloads,
            "sample_not_active_structure_ok": not_active,
            "sample_did_not_play_structure_ok": did_not_play,
        },
        "metrics_by_season": metrics_by_season,
        "hard_blockers": blockers,
        "interpretation": {
            "coverage_result_scope": "source addressability, archive provenance, and sampled document structure only",
            "coverage_pass_does_not_qualify_target_semantics": True,
            "additional_semantic_crosschecks_required": True,
            "full_player_identity_audit_required_before_labels": True,
        },
        "governance": {
            "source_only_audit": True,
            "model_fit_performed": False,
            "labels_constructed": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
            "production_dependency_authorized": False,
            "candidate_promotion_authorized": False,
        },
    }


def execute(
    *,
    output_dir: Path,
    session: Any = requests,
    run_sample_downloads: bool = True,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = _load_contract()
    schedule = _load_schedule()

    try:
        sources, cdx_metadata = fetch_cdx_index(session=session)
        cdx_error = ""
    except Exception as exc:
        sources = []
        cdx_metadata = {
            "endpoint": CDX_ENDPOINT,
            "http_status": None,
            "response_sha256": "",
            "response_bytes": 0,
            "parsed_gamebook_urls": 0,
        }
        cdx_error = str(exc)[:1000]

    source_map = build_source_map(schedule, sources, contract)
    sample_per_season = int(contract["frozen_qualification_gates"]["sample_games_per_season"])
    sample = _select_sample(source_map, sample_per_season)
    sample_results = (
        evaluate_sample_semantics(sample, session=session) if run_sample_downloads else []
    )
    report = summarize(
        schedule=schedule,
        source_map=source_map,
        sample_results=sample_results,
        cdx_metadata=cdx_metadata,
        contract=contract,
    )
    if cdx_error:
        report["hard_blockers"] = [f"CDX source index fetch failed: {cdx_error}"] + list(
            report["hard_blockers"]
        )
        report["technical_status"] = "BLOCKED"
        report["historical_gamebook_coverage_qualified"] = False
        report["cdx_index"]["error"] = cdx_error

    source_map.to_csv(output_dir / "game_source_map.csv", index=False)
    (output_dir / "sample_semantics.json").write_text(
        json.dumps(sample_results, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output_dir / "qualification.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR_DEFAULT)
    parser.add_argument(
        "--skip-sample-downloads",
        action="store_true",
        help="Unit/debug mode only; production research audit must not use this flag.",
    )
    args = parser.parse_args()
    report = execute(
        output_dir=args.output_dir,
        run_sample_downloads=not args.skip_sample_downloads,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
