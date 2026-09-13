from __future__ import annotations

"""Diagnostic-only DNP/weekly-roster reconciliation for V09B.

This module deliberately has no qualification authority. It treats the NFL Game Book
"Did Not Play" section as ambiguous and asks only whether an independently sourced
weekly-roster row can identify the player and describe the source's roster status.
"""

from dataclasses import dataclass
import gzip
import hashlib
from io import StringIO
import json
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Iterable, Mapping

import pandas as pd
import requests


TARGET_SEASONS = (2017, 2018, 2019, 2020, 2021)
WEEKLY_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "weekly_rosters/roster_weekly_{season}.csv"
)
TEAM_ALIASES = {
    "JAC": "JAX",
    "LAR": "LA",
    "STL": "LA",
    "SD": "LAC",
    "SDG": "LAC",
    "WSH": "WAS",
}
CATEGORY_HEADINGS = ("Lineups", "Substitutions", "Did Not Play", "Not Active")
TOKEN_RE = re.compile(
    r"(?<!\S)(?P<jersey>\d{1,2})\s+"
    r"(?P<name>(?:[A-Z][a-z]{0,3}\.)?[A-Z][A-Za-z'’.\-]+)"
)
NAME_PART_RE = re.compile(r"[A-Za-z]+")


@dataclass(frozen=True)
class DnpToken:
    season: int
    week: int
    game_id: str
    team: str
    side: str
    jersey_number: str
    gamebook_name: str


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_team(value: object) -> str:
    text = str(value or "").strip().upper()
    return TEAM_ALIASES.get(text, text)


def normalize_letters(value: object) -> str:
    return "".join(NAME_PART_RE.findall(str(value or ""))).lower()


def gamebook_name_parts(value: object) -> tuple[str, str]:
    text = str(value or "").strip().replace("’", "'")
    if "." not in text:
        return "", normalize_letters(text)
    first, last = text.split(".", 1)
    return normalize_letters(first), normalize_letters(last)


def _candidate_first_values(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("first_name", "football_name", "full_name", "display_name"):
        raw = str(row.get(key, "") or "").strip()
        if not raw:
            continue
        first = raw.split()[0]
        first_norm = normalize_letters(first)
        if first_norm and first_norm not in values:
            values.append(first_norm)
    return values


def _candidate_last_values(row: Mapping[str, Any]) -> list[str]:
    values: list[str] = []
    for key in ("last_name", "full_name", "display_name", "football_name"):
        raw = str(row.get(key, "") or "").strip()
        if not raw:
            continue
        last = raw.split()[-1]
        last_norm = normalize_letters(last)
        if last_norm and last_norm not in values:
            values.append(last_norm)
    return values


def name_compatible(gamebook_name: str, row: Mapping[str, Any]) -> bool:
    prefix, last = gamebook_name_parts(gamebook_name)
    if not last:
        return False
    if last not in _candidate_last_values(row):
        return False
    if not prefix:
        return True
    first_values = _candidate_first_values(row)
    return any(first.startswith(prefix) for first in first_values)


def normalize_jersey(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        return str(int(float(text)))
    except (TypeError, ValueError):
        return text.lstrip("0") or "0"


def resolve_dnp_token(token: DnpToken, weekly: pd.DataFrame) -> dict[str, Any]:
    subset = weekly[
        weekly["season"].eq(token.season)
        & weekly["week"].eq(token.week)
        & weekly["team_norm"].eq(normalize_team(token.team))
        & weekly["jersey_norm"].eq(normalize_jersey(token.jersey_number))
    ].copy()
    candidates: list[dict[str, Any]] = []
    for row in subset.to_dict("records"):
        if name_compatible(token.gamebook_name, row):
            candidates.append(row)

    gsis = {
        str(row.get("gsis_id") or "").strip()
        for row in candidates
        if str(row.get("gsis_id") or "").strip()
        not in {"", "nan", "None", "<NA>"}
    }
    if len(gsis) == 1:
        state = "unique"
        resolved_gsis = next(iter(gsis))
        chosen = [row for row in candidates if str(row.get("gsis_id") or "").strip() == resolved_gsis]
        statuses = sorted(
            {str(row.get("status") or "").strip() for row in chosen if str(row.get("status") or "").strip()}
        )
        status_desc = sorted(
            {
                str(row.get("status_description_abbr") or "").strip()
                for row in chosen
                if str(row.get("status_description_abbr") or "").strip()
            }
        )
        full_names = sorted(
            {str(row.get("full_name") or "").strip() for row in chosen if str(row.get("full_name") or "").strip()}
        )
    elif len(gsis) > 1:
        state = "ambiguous"
        resolved_gsis = ""
        statuses = sorted(
            {str(row.get("status") or "").strip() for row in candidates if str(row.get("status") or "").strip()}
        )
        status_desc = sorted(
            {
                str(row.get("status_description_abbr") or "").strip()
                for row in candidates
                if str(row.get("status_description_abbr") or "").strip()
            }
        )
        full_names = sorted(
            {str(row.get("full_name") or "").strip() for row in candidates if str(row.get("full_name") or "").strip()}
        )
    else:
        state = "unresolved"
        resolved_gsis = ""
        statuses = []
        status_desc = []
        full_names = []

    return {
        "identity_state": state,
        "gsis_id": resolved_gsis,
        "candidate_rows": int(len(candidates)),
        "candidate_gsis_ids": int(len(gsis)),
        "weekly_statuses": "|".join(statuses),
        "weekly_status_description_abbrs": "|".join(status_desc),
        "weekly_full_names": "|".join(full_names),
    }


def validate_weekly_roster_frame(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    required = {
        "season",
        "week",
        "team",
        "jersey_number",
        "status",
        "full_name",
        "first_name",
        "last_name",
        "gsis_id",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{season} weekly roster asset missing fields: {sorted(missing)}")
    if "status_description_abbr" not in frame.columns:
        frame = frame.copy()
        frame["status_description_abbr"] = ""
    if "football_name" not in frame.columns:
        frame = frame.copy()
        frame["football_name"] = ""
    if "display_name" not in frame.columns:
        frame = frame.copy()
        frame["display_name"] = frame["full_name"]

    out = frame.copy()
    out["season"] = pd.to_numeric(out["season"], errors="coerce")
    out["week"] = pd.to_numeric(out["week"], errors="coerce")
    out = out[out["season"].eq(season) & out["week"].between(1, 18)].copy()
    if out.empty:
        raise ValueError(f"{season} weekly roster asset has no regular-season rows")
    out["season"] = out["season"].astype(int)
    out["week"] = out["week"].astype(int)
    out["team_norm"] = out["team"].map(normalize_team)
    out["jersey_norm"] = out["jersey_number"].map(normalize_jersey)
    return out


def fetch_weekly_rosters(
    output_root: Path,
    *,
    seasons: Iterable[int] = TARGET_SEASONS,
    session: requests.Session | None = None,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    session = session or requests.Session()
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (compatible; LevLine4Research/1.0; dnp-roster-diagnostic)",
            "Accept": "text/csv,text/plain,*/*",
        }
    )
    frames: list[pd.DataFrame] = []
    manifest: list[dict[str, Any]] = []
    raw_dir = output_root / "raw" / "weekly_rosters"
    raw_dir.mkdir(parents=True, exist_ok=True)
    for season in seasons:
        url = WEEKLY_URL.format(season=int(season))
        response = session.get(url, timeout=90, allow_redirects=True)
        response.raise_for_status()
        payload = bytes(response.content)
        digest = sha256_bytes(payload)
        raw_path = raw_dir / f"roster_weekly_{season}.csv"
        raw_path.write_bytes(payload)
        frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
        qualified = validate_weekly_roster_frame(frame, int(season))
        frames.append(qualified)
        manifest.append(
            {
                "season": int(season),
                "url": url,
                "final_url": str(response.url),
                "sha256": digest,
                "bytes": len(payload),
                "full_asset_rows": int(len(frame)),
                "regular_season_rows": int(len(qualified)),
                "hash_pinned_before_run": False,
                "source_qualification_authority": False,
            }
        )
    return pd.concat(frames, ignore_index=True, sort=False), manifest


def read_archive_manifest(archive_root: Path, season: int) -> list[dict[str, Any]]:
    path = archive_root / "manifests" / f"{season}.jsonl"
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def extract_pdf_text(raw_pdf: bytes) -> str:
    with tempfile.TemporaryDirectory(prefix="v09b-dnp-") as tmp:
        pdf = Path(tmp) / "gamebook.pdf"
        txt = Path(tmp) / "gamebook.txt"
        pdf.write_bytes(raw_pdf)
        proc = subprocess.run(
            ["pdftotext", "-layout", str(pdf), str(txt)],
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode != 0 or not txt.exists():
            raise RuntimeError(f"pdftotext failed: {proc.stderr.strip()}")
        return txt.read_text(encoding="utf-8", errors="replace")


def _heading_positions(line: str, heading: str) -> list[int]:
    return [m.start() for m in re.finditer(re.escape(heading), line, flags=re.IGNORECASE)]


def _find_roster_page(lines: list[str]) -> tuple[int, int, int]:
    starts: list[tuple[int, int]] = []
    for i, line in enumerate(lines):
        positions = _heading_positions(line, "Lineups")
        if len(positions) >= 2:
            starts.append((i, positions[1]))
    if not starts:
        for i, line in enumerate(lines):
            positions = _heading_positions(line, "Did Not Play")
            if len(positions) >= 2:
                starts.append((max(0, i - 20), positions[1]))
                break
    if not starts:
        raise ValueError("could not locate two-column Game Book roster section")
    start, split_at = starts[0]
    end = min(len(lines), start + 120)
    return start, end, split_at


def _split_column(line: str, split_at: int, side: str) -> str:
    if side == "left":
        return line[:split_at]
    return line[split_at:]


def _category_blocks(
    lines: list[str], start: int, end: int, split_at: int, side: str
) -> dict[str, str]:
    region = lines[start:end]
    blocks: dict[str, list[str]] = {heading: [] for heading in CATEGORY_HEADINGS}
    current: str | None = None
    for raw in region:
        col = _split_column(raw, split_at, side)
        found: str | None = None
        for heading in CATEGORY_HEADINGS:
            if re.search(rf"\b{re.escape(heading)}\b", col, flags=re.IGNORECASE):
                found = heading
                break
        if found is not None:
            current = found
            match = re.search(re.escape(found), col, flags=re.IGNORECASE)
            tail = col[match.end():] if match else ""
            if tail.strip():
                blocks[current].append(tail)
            continue
        if current is not None:
            if re.search(r"\b(?:Officials|Weather|Coin Toss|Scoring Drive|Game Statistics)\b", col):
                current = None
                continue
            blocks[current].append(col)
    return {key: " ".join(value) for key, value in blocks.items()}


def parse_dnp_tokens_from_text(
    text: str,
    *,
    season: int,
    week: int,
    game_id: str,
    away_team: str,
    home_team: str,
) -> list[DnpToken]:
    lines = text.splitlines()
    start, end, split_at = _find_roster_page(lines)
    tokens: list[DnpToken] = []
    for side, team in (("left", away_team), ("right", home_team)):
        blocks = _category_blocks(lines, start, end, split_at, side)
        seen: set[tuple[str, str]] = set()
        for match in TOKEN_RE.finditer(blocks.get("Did Not Play", "")):
            jersey = normalize_jersey(match.group("jersey"))
            name = match.group("name").strip()
            key = (jersey, name)
            if key in seen:
                continue
            seen.add(key)
            tokens.append(
                DnpToken(
                    season=int(season),
                    week=int(week),
                    game_id=str(game_id),
                    team=normalize_team(team),
                    side=side,
                    jersey_number=jersey,
                    gamebook_name=name,
                )
            )
    return tokens


def parse_all_dnp_tokens(archive_root: Path) -> tuple[list[DnpToken], list[dict[str, Any]]]:
    all_tokens: list[DnpToken] = []
    errors: list[dict[str, Any]] = []
    for season in TARGET_SEASONS:
        for row in read_archive_manifest(archive_root, season):
            try:
                gz_path = archive_root / str(row["raw_object_relpath"])
                raw_pdf = gzip.decompress(gz_path.read_bytes())
                if sha256_bytes(raw_pdf) != str(row["raw_pdf_sha256"]):
                    raise ValueError("raw PDF SHA mismatch against qualified archive manifest")
                text = extract_pdf_text(raw_pdf)
                all_tokens.extend(
                    parse_dnp_tokens_from_text(
                        text,
                        season=season,
                        week=int(row["week"]),
                        game_id=str(row["game_id"]),
                        away_team=str(row["away_team"]),
                        home_team=str(row["home_team"]),
                    )
                )
            except Exception as exc:
                errors.append(
                    {
                        "season": season,
                        "week": row.get("week"),
                        "game_id": row.get("game_id"),
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
    return all_tokens, errors


def _status_summary(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["identity_state", "weekly_statuses", "weekly_status_description_abbrs", "rows"])
    return (
        frame.groupby(
            ["identity_state", "weekly_statuses", "weekly_status_description_abbrs"],
            dropna=False,
        )
        .size()
        .reset_index(name="rows")
        .sort_values(["rows", "identity_state"], ascending=[False, True], kind="stable")
    )


def evaluate_sentinels(resolved: pd.DataFrame, sentinels: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    for item in sentinels:
        mask = (
            resolved["season"].eq(int(item["season"]))
            & resolved["week"].eq(int(item["week"]))
            & resolved["team"].eq(normalize_team(item["team"]))
            & resolved["game_id"].eq(str(item["game_id"]))
            & resolved["gamebook_name"].eq(str(item["gamebook_name"]))
        )
        rows = resolved.loc[mask]
        observations.append(
            {
                **dict(item),
                "matching_dnp_rows": int(len(rows)),
                "identity_states": sorted(set(rows["identity_state"].astype(str))) if len(rows) else [],
                "weekly_statuses": sorted(set(rows["weekly_statuses"].astype(str))) if len(rows) else [],
                "weekly_status_description_abbrs": sorted(set(rows["weekly_status_description_abbrs"].astype(str))) if len(rows) else [],
                "gsis_ids": sorted(set(rows["gsis_id"].astype(str))) if len(rows) else [],
                "diagnostic_only": True,
            }
        )
    return observations


def run_diagnostic(
    *,
    archive_root: Path,
    output_root: Path,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    weekly, source_manifest = fetch_weekly_rosters(output_root)
    tokens, parse_errors = parse_all_dnp_tokens(archive_root)

    token_rows: list[dict[str, Any]] = []
    for token in tokens:
        row = {
            "season": token.season,
            "week": token.week,
            "game_id": token.game_id,
            "team": token.team,
            "side": token.side,
            "jersey_number": token.jersey_number,
            "gamebook_name": token.gamebook_name,
        }
        row.update(resolve_dnp_token(token, weekly))
        token_rows.append(row)

    resolved = pd.DataFrame(token_rows)
    if resolved.empty:
        resolved = pd.DataFrame(
            columns=[
                "season", "week", "game_id", "team", "side", "jersey_number",
                "gamebook_name", "identity_state", "gsis_id", "candidate_rows",
                "candidate_gsis_ids", "weekly_statuses",
                "weekly_status_description_abbrs", "weekly_full_names",
            ]
        )
    resolved.to_csv(output_root / "dnp_weekly_roster_resolution.csv", index=False)
    _status_summary(resolved).to_csv(output_root / "dnp_status_summary.csv", index=False)
    pd.DataFrame(parse_errors).to_csv(output_root / "gamebook_parse_errors.csv", index=False)

    if len(resolved):
        team_game = (
            resolved.groupby(["season", "week", "game_id", "team"], dropna=False)
            .agg(
                dnp_rows=("gamebook_name", "size"),
                unique_identity_rows=("identity_state", lambda s: int((s == "unique").sum())),
                ambiguous_identity_rows=("identity_state", lambda s: int((s == "ambiguous").sum())),
                unresolved_identity_rows=("identity_state", lambda s: int((s == "unresolved").sum())),
            )
            .reset_index()
        )
    else:
        team_game = pd.DataFrame()
    team_game.to_csv(output_root / "team_game_dnp_summary.csv", index=False)

    sentinels = evaluate_sentinels(resolved, list(contract["predeclared_sentinels"]))
    (output_root / "sentinel_observations.json").write_text(
        json.dumps(sentinels, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_root / "weekly_roster_source_manifest.json").write_text(
        json.dumps(source_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    identity_counts = resolved["identity_state"].value_counts(dropna=False).to_dict() if len(resolved) else {}
    report = {
        "record_version": 1,
        "contract_id": contract["contract_id"],
        "status": "DIAGNOSTIC_COMPLETE" if not parse_errors else "DIAGNOSTIC_COMPLETE_WITH_PARSE_ERRORS",
        "target_seasons": list(TARGET_SEASONS),
        "canonical_gamebooks_expected": int(contract["gamebook_dependency"]["canonical_games"]),
        "gamebook_parse_error_rows": int(len(parse_errors)),
        "dnp_tokens_parsed": int(len(resolved)),
        "identity_state_counts": {str(k): int(v) for k, v in identity_counts.items()},
        "unique_identity_rate": float((resolved["identity_state"] == "unique").mean()) if len(resolved) else 0.0,
        "source_manifest": source_manifest,
        "sentinel_observations": sentinels,
        "interpretation": {
            "weekly_roster_source_qualified": False,
            "game_day_membership_qualified": False,
            "dnp_active_semantics_qualified": False,
            "training_label_semantics_qualified": False,
            "training_source_chronology_qualified": False,
            "v09b_execution_authorized": False,
            "same_version_hash_pinning_authorized": False,
            "next_permitted_step": (
                "Inspect this first-run diagnostic. A separate V2 contract may pin exact source "
                "hashes and preregister qualification gates before any qualification execution."
            ),
        },
        "governance": {
            "diagnostic_only": True,
            "qualification_authority": False,
            "probability_model_built": False,
            "probability_feature_authorized": False,
            "production_dependency_authorized": False,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
            "actual_current_game_snaps_used": 0,
            "postgame_participation_used": 0,
        },
    }
    (output_root / "diagnostic_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


__all__ = [
    "DnpToken",
    "TARGET_SEASONS",
    "fetch_weekly_rosters",
    "gamebook_name_parts",
    "name_compatible",
    "normalize_jersey",
    "normalize_team",
    "parse_dnp_tokens_from_text",
    "resolve_dnp_token",
    "run_diagnostic",
    "validate_weekly_roster_frame",
]
