from __future__ import annotations

"""Diagnostic-only comparison of weekly-roster status values to Game Book sections.

Identity resolution is performed exclusively from the immutable status-free identity
projection. Source-native weekly-roster status values are read only after a Game Book
identity resolves uniquely. No status value is interpreted as game-day active/inactive
truth and this module has no membership, label, chronology, or model-fit authority.
"""

import argparse
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import polars as pl

from research import v09b_legacy_gamebook_raw_archive_v1 as raw_helpers
from research import v09b_legacy_gamebook_roster_universe_v2 as gamebook_parser
from research import v09b_modern_gamebook_roster_universe_v1 as modern_archive_guard
from research import v09b_modern_identity_source_capture_v1 as identity_capture

CONTRACT_ID = "V09B-MODERN-WEEKLY-STATUS-SEMANTICS-DIAGNOSTIC-V1"
SEASONS = (2017, 2018, 2019, 2020, 2021)
EXPECTED_GAMES = {2017: 256, 2018: 256, 2019: 256, 2020: 256, 2021: 272}
EXPECTED_TEAM_PARTITIONS = {season: games * 2 for season, games in EXPECTED_GAMES.items()}
RAW_SHA256 = {
    2017: "2f633cf331f561ea5346238a1808e8a68811eb280084e75f0dd09880535c5012",
    2018: "0fcd3c3f098dbb5350be2095959acf38202602c6b3c71475e883fabda23077a8",
    2019: "08ef64996cecdff2f4631ca26b21ed9a39bf5fba0b3379d902e531facf81e5c4",
    2020: "8d601bf5c5d669465481421ad5cd1a1470d51792054e84bdc04f3620785f7530",
    2021: "3e9f67569e940b54b3778ef2c9150850920b5bf93143bad3bd158e649825cf6b",
}
PROJECTION_SHA256 = {
    2017: "1ade2f94b602f52f53046f9efb868c441edf4f5f64ef1e205fa716327b9d4db0",
    2018: "237a75521207ea59be030fdf1d469ce04440e35cf8302fa8edbfabab506e45d2",
    2019: "ebc3e761749b956e809dfbb3e8d3556d65df22f3dcd8d7e103c70807077df7b7",
    2020: "49f770d6293cfab446165e5571274e44c2be61c3dfc4ee7321139006ce50ce1a",
    2021: "29860c837236401e1750f4902eda15ae809a62c62236ff17f16b75ca58b33fac",
}
SECTIONS = ("lineup", "substitutions", "did_not_play", "not_active")
STATUS_FIELDS = ("status", "status_description_abbr", "status_short_description")
TEAM_ALIASES = {
    "JAC": "JAX",
    "LAR": "LA",
    "STL": "LA",
    "WSH": "WAS",
    "SD": "LAC",
}
SUFFIXES = {"JR", "SR", "II", "III", "IV", "V"}
NON_ALNUM = re.compile(r"[^A-Z0-9]+")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalize_team(value: object) -> str:
    team = str(value or "").strip().upper()
    return TEAM_ALIASES.get(team, team)


def normalize_jersey(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if text.isdigit():
        return str(int(text))
    return text.upper()


def _clean_tokens(value: object) -> list[str]:
    text = str(value or "").strip().upper().replace("’", "'")
    tokens = [token for token in NON_ALNUM.split(text) if token]
    while tokens and tokens[-1] in SUFFIXES:
        tokens.pop()
    return tokens


def normalize_last_name(value: object) -> str:
    return "".join(_clean_tokens(value))


def gamebook_name_signature(display_name: object) -> tuple[str, str] | None:
    text = str(display_name or "").strip().upper().replace("’", "'")
    if not text or "." not in text:
        return None
    first, rest = text.split(".", 1)
    first_letters = NON_ALNUM.sub("", first)
    last = normalize_last_name(rest)
    if not first_letters or not last:
        return None
    return first_letters[0], last


def source_initials(row: dict[str, object]) -> set[str]:
    initials: set[str] = set()
    for field in ("first_name", "football_name"):
        tokens = _clean_tokens(row.get(field))
        if tokens and tokens[0]:
            initials.add(tokens[0][0])
    return initials


def resolve_identity(
    *,
    display_name: object,
    candidates: list[dict[str, object]],
) -> dict[str, object]:
    """Resolve from identity-only candidate rows; status fields must never be present."""
    if any(any(field in row for field in STATUS_FIELDS) for row in candidates):
        raise ValueError("status field leaked into identity resolver")
    signature = gamebook_name_signature(display_name)
    if signature is None:
        return {"resolution": "unresolved", "gsis_id": None, "matching_gsis_ids": []}
    initial, last = signature
    matched: set[str] = set()
    for row in candidates:
        gsis = str(row.get("gsis_id") or "").strip()
        if not gsis:
            continue
        if normalize_last_name(row.get("last_name")) != last:
            continue
        if initial not in source_initials(row):
            continue
        matched.add(gsis)
    ordered = sorted(matched)
    if len(ordered) == 1:
        return {"resolution": "resolved", "gsis_id": ordered[0], "matching_gsis_ids": ordered}
    if len(ordered) > 1:
        return {"resolution": "ambiguous", "gsis_id": None, "matching_gsis_ids": ordered}
    return {"resolution": "unresolved", "gsis_id": None, "matching_gsis_ids": []}


def _projection_index(frame: pl.DataFrame, *, season: int) -> dict[tuple[int, str, str], list[dict[str, object]]]:
    if tuple(frame.columns) != identity_capture.ALLOWED_FIELDS:
        raise RuntimeError("status-free projection fields do not exactly match the frozen allowlist")
    if any(field in frame.columns for field in STATUS_FIELDS):
        raise RuntimeError("status field present in status-free identity projection")
    index: dict[tuple[int, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in frame.to_dicts():
        if int(row.get("season") or -1) != season or str(row.get("game_type") or "") != "REG":
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = normalize_team(row.get("team"))
        jersey = normalize_jersey(row.get("jersey_number"))
        if not team or not jersey:
            continue
        index[(week, team, jersey)].append(row)
    return index


def _status_lookup(frame: pl.DataFrame, *, season: int) -> dict[tuple[int, str, str], Counter[tuple[str, str]]]:
    required = {"season", "game_type", "week", "team", "gsis_id", "status_description_abbr"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise RuntimeError(f"raw weekly roster missing required status fields: {missing}")
    lookup: dict[tuple[int, str, str], Counter[tuple[str, str]]] = defaultdict(Counter)
    for row in frame.to_dicts():
        if int(row.get("season") or -1) != season or str(row.get("game_type") or "") != "REG":
            continue
        try:
            week = int(row.get("week"))
        except (TypeError, ValueError):
            continue
        team = normalize_team(row.get("team"))
        gsis = str(row.get("gsis_id") or "").strip()
        if not team or not gsis:
            continue
        abbr = "<NULL>" if row.get("status_description_abbr") is None else str(row.get("status_description_abbr")).strip() or "<BLANK>"
        short = "<NULL>" if "status_short_description" not in frame.columns or row.get("status_short_description") is None else str(row.get("status_short_description")).strip() or "<BLANK>"
        lookup[(week, team, gsis)][(abbr, short)] += 1
    return lookup


def _bounded_append(values: list[dict[str, object]], row: dict[str, object], *, limit: int = 100) -> None:
    if len(values) < limit:
        values.append(row)


def _load_identity_sources(identity_root: Path, season: int) -> tuple[pl.DataFrame, pl.DataFrame, dict[str, object]]:
    raw_sha = RAW_SHA256[season]
    projection_sha = PROJECTION_SHA256[season]
    raw_path = identity_root / "raw" / f"{raw_sha}.parquet"
    projection_path = identity_root / "projections" / f"{season}-{projection_sha}.parquet"
    receipt_path = identity_root / "receipts" / f"{season}.json"
    if not raw_path.exists() or not projection_path.exists() or not receipt_path.exists():
        raise RuntimeError("immutable identity-source capture is incomplete")
    if _sha256_file(raw_path) != raw_sha:
        raise RuntimeError("raw weekly-roster SHA does not match frozen receipt")
    if _sha256_file(projection_path) != projection_sha:
        raise RuntimeError("status-free projection SHA does not match frozen receipt")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not (
        receipt.get("contract_id") == identity_capture.CONTRACT_ID
        and int(receipt.get("season")) == season
        and receipt.get("raw_source_sha256") == raw_sha
        and receipt.get("projection_sha256") == projection_sha
        and receipt.get("capture_gate_pass") is True
        and receipt.get("status_fields_selected") is False
        and receipt.get("status_fields_read_for_resolution") is False
    ):
        raise RuntimeError("identity-source capture receipt failed frozen upstream checks")
    return pl.read_parquet(projection_path), pl.read_parquet(raw_path), receipt


def audit_season(season: int, *, archive_root: Path, identity_root: Path) -> dict[str, Any]:
    if season not in SEASONS:
        raise ValueError(f"season must be one of {SEASONS}")

    upstream = modern_archive_guard.validate_upstream_archive(archive_root, season)
    projection, raw_roster, identity_receipt = _load_identity_sources(identity_root, season)
    projection_index = _projection_index(projection, season=season)
    status_lookup = _status_lookup(raw_roster, season=season)

    manifest_path = archive_root / "manifests" / f"{season}.jsonl"
    manifest = [json.loads(line) for line in manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    section_totals = Counter()
    resolution_counts = Counter()
    section_resolution_counts: dict[str, Counter[str]] = {section: Counter() for section in SECTIONS}
    cross_tab: dict[str, Counter[str]] = {section: Counter() for section in SECTIONS}
    source_errors: list[dict[str, object]] = []
    unresolved_examples: list[dict[str, object]] = []
    ambiguous_examples: list[dict[str, object]] = []
    missing_status_examples: list[dict[str, object]] = []
    multi_status_examples: list[dict[str, object]] = []
    parsed_games = 0
    parsed_partitions = 0
    marker_exact_games = 0
    repeated_within_section_occurrences = 0

    for source_row in manifest:
        try:
            raw_path = archive_root / str(source_row["raw_object_relpath"])
            with gzip.open(raw_path, "rb") as handle:
                text = raw_helpers._extract_pdf_text(handle.read())
            marker_left, sections_left = gamebook_parser._section_entries(text, side=0)
            marker_right, sections_right = gamebook_parser._section_entries(text, side=1)
            if marker_left != marker_right or not all(marker_left.get(name) == 1 for name in ("lineups", "substitutions", "did_not_play", "not_active")):
                raise ValueError("Game Book semantic marker counts are not exact")
            marker_exact_games += 1
            parsed_games += 1

            for team, sections in ((str(source_row["away_team"]), sections_left), (str(source_row["home_team"]), sections_right)):
                parsed_partitions += 1
                week = int(source_row["week"])
                team_norm = normalize_team(team)
                for section in SECTIONS:
                    entries = sections[section]
                    counts = Counter(entry.parser_identity for entry in entries)
                    repeated_within_section_occurrences += sum(max(0, count - 1) for count in counts.values())
                    for jersey, display_name in sorted(counts):
                        section_totals[section] += 1
                        candidates = projection_index.get((week, team_norm, normalize_jersey(jersey)), [])
                        resolved = resolve_identity(display_name=display_name, candidates=candidates)
                        resolution = str(resolved["resolution"])
                        resolution_counts[resolution] += 1
                        section_resolution_counts[section][resolution] += 1
                        base_example = {
                            "season": season,
                            "week": week,
                            "game_id": str(source_row["game_id"]),
                            "team": team_norm,
                            "section": section,
                            "jersey_number": normalize_jersey(jersey),
                            "display_name": display_name,
                        }
                        if resolution == "unresolved":
                            _bounded_append(unresolved_examples, {**base_example, "candidate_count": len(candidates)})
                            continue
                        if resolution == "ambiguous":
                            _bounded_append(ambiguous_examples, {**base_example, "matching_gsis_ids": resolved["matching_gsis_ids"]})
                            continue

                        gsis = str(resolved["gsis_id"])
                        variants = status_lookup.get((week, team_norm, gsis), Counter())
                        if not variants:
                            resolution_counts["resolved_missing_status"] += 1
                            section_resolution_counts[section]["resolved_missing_status"] += 1
                            _bounded_append(missing_status_examples, {**base_example, "gsis_id": gsis})
                            continue
                        if len(variants) != 1:
                            resolution_counts["resolved_multi_status_variant"] += 1
                            section_resolution_counts[section]["resolved_multi_status_variant"] += 1
                            _bounded_append(
                                multi_status_examples,
                                {
                                    **base_example,
                                    "gsis_id": gsis,
                                    "status_variants": [
                                        {"status_description_abbr": abbr, "status_short_description": short, "rows": count}
                                        for (abbr, short), count in sorted(variants.items())
                                    ],
                                },
                            )
                            continue
                        (abbr, _short), _count = next(iter(variants.items()))
                        cross_tab[section][abbr] += 1
                        resolution_counts["resolved_single_status"] += 1
                        section_resolution_counts[section]["resolved_single_status"] += 1
        except Exception as exc:
            source_errors.append({
                "game_id": str(source_row.get("game_id")),
                "error": f"{type(exc).__name__}: {exc}",
            })

    expected_games = EXPECTED_GAMES[season]
    expected_partitions = EXPECTED_TEAM_PARTITIONS[season]
    integrity_gate_pass = bool(
        upstream.get("upstream_passed") is True
        and len(manifest) == expected_games
        and len({str(row["game_id"]) for row in manifest}) == expected_games
        and parsed_games == expected_games
        and marker_exact_games == expected_games
        and parsed_partitions == expected_partitions
        and not source_errors
        and tuple(projection.columns) == identity_capture.ALLOWED_FIELDS
        and not any(field in projection.columns for field in STATUS_FIELDS)
        and identity_receipt.get("capture_gate_pass") is True
    )

    total_section_identities = sum(section_totals.values())
    resolved_identity = int(resolution_counts["resolved"])
    result = {
        "diagnostic_version": 1,
        "contract_id": CONTRACT_ID,
        "season": season,
        "upstream_gamebook_archive_qualified": upstream.get("upstream_passed") is True,
        "identity_source_capture_gate_pass": identity_receipt.get("capture_gate_pass") is True,
        "raw_weekly_roster_sha256": RAW_SHA256[season],
        "status_free_projection_sha256": PROJECTION_SHA256[season],
        "projection_fields": list(projection.columns),
        "status_fields_present_in_identity_projection": any(field in projection.columns for field in STATUS_FIELDS),
        "status_used_during_identity_resolution": False,
        "canonical_games": len(manifest),
        "expected_games": expected_games,
        "parsed_games": parsed_games,
        "marker_exact_games": marker_exact_games,
        "parsed_team_partitions": parsed_partitions,
        "expected_team_partitions": expected_partitions,
        "source_error_count": len(source_errors),
        "source_errors": source_errors[:100],
        "section_unique_identity_counts": {section: section_totals[section] for section in SECTIONS},
        "total_section_unique_identities": total_section_identities,
        "identity_resolution_counts": dict(sorted(resolution_counts.items())),
        "unique_identity_resolution_rate": resolved_identity / total_section_identities if total_section_identities else 0.0,
        "section_resolution_counts": {
            section: dict(sorted(section_resolution_counts[section].items())) for section in SECTIONS
        },
        "section_by_status_description_abbr": {
            section: dict(sorted(cross_tab[section].items())) for section in SECTIONS
        },
        "repeated_within_section_occurrences": repeated_within_section_occurrences,
        "unresolved_examples": unresolved_examples,
        "ambiguous_examples": ambiguous_examples,
        "resolved_missing_status_examples": missing_status_examples,
        "resolved_multi_status_variant_examples": multi_status_examples,
        "integrity_gate_pass": integrity_gate_pass,
        "observed_status_pattern_has_qualification_authority": False,
        "status_value_semantics_qualified": False,
        "weekly_roster_game_day_membership_qualified": False,
        "modern_game_day_roster_universe_qualified": False,
        "modern_player_team_game_identity_qualified": False,
        "training_label_semantics_qualified": False,
        "training_source_chronology_qualified": False,
        "v09b_model_fit_authorized": False,
        "postgame_participation_used": False,
        "model_fit_performed": False,
        "game_outcomes_used": 0,
        "completed_2026_outcomes_used": 0,
        "production_dependency_authorized": False,
    }
    return result


def main(argv: Iterable[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, required=True, choices=SEASONS)
    parser.add_argument("--archive-root", type=Path, required=True)
    parser.add_argument("--identity-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(list(argv) if argv is not None else None)
    result = audit_season(args.season, archive_root=args.archive_root, identity_root=args.identity_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if not k.endswith("_examples") and k != "source_errors"}, indent=2, sort_keys=True))
    if result["integrity_gate_pass"] is not True:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
