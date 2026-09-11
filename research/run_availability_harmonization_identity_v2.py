from __future__ import annotations

"""Deterministic v2 identity bridge for the chronology-safe availability audit.

PR #145 established that the v1 reverse-identity rule failed the frozen 99.5% gate in
2022 because official NFL player names and nflverse injury-row names sometimes use
different deterministic aliases. This module does not change the gate. It adds one
preregistered identity-only bridge: exact normalized aliases from the pinned nflverse
player master may resolve an otherwise-unmatched official row only when the resulting
GSIS ID is also present in the nflverse injury table for the same season/week/team.

No fuzzy matching, manual aliases, outcome information, availability inference, model
fitting, or production behavior is introduced here.
"""

import argparse
import hashlib
import json
from io import StringIO
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests

from nfl_forecast.availability_2025_reconstruction import normalize_name_token, normalize_team
from research import run_availability_harmonization_repaired_v1 as repaired


CONTRACT_PATH = Path("research/availability/2022_2025_identity_bridge_contract_v2.json")
PLAYER_MASTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
PLAYER_MASTER_SHA256 = "6f896e1134757efe09761ae81280f89d9604d8ce611a888a56d9e7d49e80eeb9"
PLAYER_MASTER_REQUIRED = {
    "gsis_id", "display_name", "football_name", "common_first_name", "first_name", "last_name"
}
LEGACY_SEASONS = {2022, 2023, 2024}
_ORIGINAL_REVERSE_IDENTITY = repaired.reverse_identity_audit
_PLAYER_MASTER: pd.DataFrame | None = None
_PLAYER_MASTER_PAYLOAD: bytes | None = None


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def load_player_master(payload: bytes) -> pd.DataFrame:
    digest = _sha256(payload)
    if digest != PLAYER_MASTER_SHA256:
        raise ValueError(
            f"nflverse player master digest changed: expected {PLAYER_MASTER_SHA256}, got {digest}"
        )
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = PLAYER_MASTER_REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"nflverse player master missing identity fields: {sorted(missing)}")
    frame = frame.copy()
    frame["gsis_id"] = frame["gsis_id"].fillna("").astype(str).str.strip()
    frame = frame[frame["gsis_id"].ne("")].copy()
    if frame.empty:
        raise ValueError("nflverse player master contains no GSIS-keyed rows")
    return frame


def _candidate_aliases(row: pd.Series) -> Iterable[str]:
    last = "" if pd.isna(row.get("last_name")) else str(row.get("last_name")).strip()
    values = [row.get("display_name"), row.get("football_name")]
    for first_field in ("first_name", "common_first_name"):
        first = "" if pd.isna(row.get(first_field)) else str(row.get(first_field)).strip()
        if first and last:
            values.append(f"{first} {last}")
    for value in values:
        if value is None or pd.isna(value):
            continue
        key = normalize_name_token(value)
        if key:
            yield key


def build_alias_lookup(player_master: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    lookup: dict[str, set[str]] = {}
    for _, row in player_master.iterrows():
        gsis_id = str(row["gsis_id"]).strip()
        for alias in _candidate_aliases(row):
            lookup.setdefault(alias, set()).add(gsis_id)
    return {key: tuple(sorted(ids)) for key, ids in lookup.items()}


def deterministic_alias_reverse_identity_audit(
    official: pd.DataFrame,
    nflverse: pd.DataFrame,
    *,
    season: int,
    player_master: pd.DataFrame,
) -> tuple[dict, pd.DataFrame]:
    metrics, unresolved = _ORIGINAL_REVERSE_IDENTITY(official, nflverse, season=season)
    metrics = dict(metrics)
    metrics.update({
        "identity_bridge_version": "v2_exact_player_master_alias",
        "identity_bridge_attempted_rows": 0,
        "identity_bridge_resolved_rows": 0,
        "identity_bridge_ambiguous_rows": 0,
        "identity_bridge_unmatched_rows": int(len(unresolved)),
    })
    if season not in LEGACY_SEASONS or unresolved.empty:
        return metrics, unresolved

    alias_lookup = build_alias_lookup(player_master)
    base = repaired._identity_base(nflverse, season=season).copy()
    base["team"] = base["team"].map(normalize_team)
    allowed_by_key = (
        base.groupby(["season", "week", "team"], dropna=False)["gsis_id"]
        .agg(lambda values: set(map(str, values)))
        .to_dict()
    )

    resolved_index: list[int] = []
    ambiguous = 0
    still_unmatched = 0
    for idx, row in unresolved.iterrows():
        metrics["identity_bridge_attempted_rows"] += 1
        alias = normalize_name_token(row.get("external_player", ""))
        candidates = set(alias_lookup.get(alias, ()))
        same_game_ids = allowed_by_key.get(
            (int(row["season"]), int(row["week"]), normalize_team(row["team"])), set()
        )
        candidates &= same_game_ids
        if len(candidates) == 1:
            gsis_id = next(iter(candidates))
            unresolved.at[idx, "gsis_id"] = gsis_id
            unresolved.at[idx, "identity_match_state"] = "unique"
            unresolved.at[idx, "identity_match_method"] = "player_master_exact_alias_same_team_week"
            resolved_index.append(idx)
        elif len(candidates) > 1:
            unresolved.at[idx, "identity_match_state"] = "ambiguous"
            unresolved.at[idx, "identity_match_method"] = "player_master_exact_alias_same_team_week"
            ambiguous += 1
        else:
            still_unmatched += 1

    resolved_by_bridge = len(resolved_index)
    remaining = unresolved.drop(index=resolved_index).copy()
    original_resolved = int(metrics["official_unique_stable_identity_rows"])
    total = int(metrics["official_distinct_rows"])
    total_resolved = original_resolved + resolved_by_bridge
    metrics.update({
        "official_unique_stable_identity_rows": total_resolved,
        "official_unresolved_identity_rows": int(len(remaining)),
        "official_identity_resolution_rate": float(total_resolved / total) if total else 0.0,
        "identity_bridge_resolved_rows": resolved_by_bridge,
        "identity_bridge_ambiguous_rows": ambiguous,
        "identity_bridge_unmatched_rows": still_unmatched,
    })
    return metrics, remaining


def _reverse_identity_v2(official: pd.DataFrame, nflverse: pd.DataFrame, *, season: int):
    if season == 2025:
        return _ORIGINAL_REVERSE_IDENTITY(official, nflverse, season=season)
    if _PLAYER_MASTER is None:
        raise RuntimeError("v2 player master was not initialized before reverse-identity audit")
    return deterministic_alias_reverse_identity_audit(
        official, nflverse, season=season, player_master=_PLAYER_MASTER
    )


def _fetch_player_master() -> bytes:
    response = requests.get(
        PLAYER_MASTER_URL,
        headers={"User-Agent": "Mozilla/5.0 (compatible; LevLineResearch/1.0)"},
        timeout=60,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response.content


def _parse_output_dir() -> Path:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument(
        "--output-dir", default="research_outputs/availability_2022_2025_harmonization"
    )
    args, _ = parser.parse_known_args()
    return Path(args.output_dir)


def main() -> int:
    global _PLAYER_MASTER, _PLAYER_MASTER_PAYLOAD
    contract = _load_contract()
    if contract["qualification_policy"]["threshold_changed_from_v1"] is not False:
        raise RuntimeError("v2 identity bridge may not change the v1 threshold")
    if contract["firewall"]["game_outcomes_allowed"] is not False:
        raise RuntimeError("v2 identity bridge may not use game outcomes")
    if contract["firewall"]["completed_2026_outcomes_allowed"] is not False:
        raise RuntimeError("v2 identity bridge may not use completed-2026 outcomes")

    output_dir = _parse_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)
    _PLAYER_MASTER_PAYLOAD = _fetch_player_master()
    _PLAYER_MASTER = load_player_master(_PLAYER_MASTER_PAYLOAD)
    raw_path = output_dir / "raw" / "nflverse" / "players.csv"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(_PLAYER_MASTER_PAYLOAD)
    repaired._write_json(
        output_dir / "identity_bridge_v2_source.json",
        {
            "candidate_id": contract["candidate_id"],
            "player_master_url": PLAYER_MASTER_URL,
            "player_master_sha256": _sha256(_PLAYER_MASTER_PAYLOAD),
            "player_master_rows": int(len(_PLAYER_MASTER)),
            "manual_alias_overrides_used": 0,
            "fuzzy_matching_used": 0,
            "game_outcomes_used": 0,
            "completed_2026_outcomes_used": 0,
        },
    )

    repaired.reverse_identity_audit = _reverse_identity_v2
    try:
        return repaired.main()
    finally:
        repaired.reverse_identity_audit = _ORIGINAL_REVERSE_IDENTITY


if __name__ == "__main__":
    raise SystemExit(main())
