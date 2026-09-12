from __future__ import annotations

"""Deterministic identity-only bridge for strict regular-season availability research.

This is a direct research-port of the previously preregistered V2 identity design. It
may translate an exact official-name alias to stable GSIS identity, but it cannot use
team status, position, injury/practice/game status, snaps, participation, or outcomes
to choose a player. A matched GSIS must already exist in the same historical
season/week/team injury rows.
"""

from collections import defaultdict
import hashlib
from io import StringIO

import pandas as pd

from nfl_forecast.availability_2025_reconstruction import (
    attach_stable_identity as attach_stable_identity_v1,
    normalize_name_token,
    normalize_team,
)


PLAYER_MASTER_URL = "https://github.com/nflverse/nflverse-data/releases/download/players/players.csv"
PLAYER_MASTER_ASSET_ID = 559182453
PLAYER_MASTER_EXPECTED_SHA256 = "b2fd8b7a384d6fc521c1832dba93878435554f1a4c4800d571edaa4ddd309134"
PLAYER_MASTER_REQUIRED = {
    "gsis_id",
    "display_name",
    "common_first_name",
    "first_name",
    "last_name",
    "short_name",
    "football_name",
}


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def validate_player_master_payload(payload: bytes) -> pd.DataFrame:
    digest = sha256_bytes(payload)
    if digest != PLAYER_MASTER_EXPECTED_SHA256:
        raise ValueError(
            "nflverse players identity asset digest changed: "
            f"expected {PLAYER_MASTER_EXPECTED_SHA256}, got {digest}"
        )
    frame = pd.read_csv(StringIO(payload.decode("utf-8")), low_memory=False)
    missing = PLAYER_MASTER_REQUIRED - set(frame.columns)
    if missing:
        raise ValueError(f"nflverse players identity asset missing fields: {sorted(missing)}")
    keyed = frame[frame["gsis_id"].notna() & frame["gsis_id"].astype(str).str.strip().ne("")].copy()
    if keyed.empty:
        raise ValueError("nflverse players identity asset contains no GSIS-keyed rows")
    duplicate = keyed["gsis_id"].astype(str).duplicated(keep=False)
    if duplicate.any():
        ids = sorted(keyed.loc[duplicate, "gsis_id"].astype(str).unique())[:10]
        raise ValueError(f"nflverse players identity asset has duplicate GSIS primary keys: {ids}")
    return keyed


def _join_name(first: object, last: object) -> str:
    first_text = "" if pd.isna(first) else str(first).strip()
    last_text = "" if pd.isna(last) else str(last).strip()
    return f"{first_text} {last_text}".strip()


def build_player_alias_lookup(player_master: pd.DataFrame) -> dict[str, tuple[str, ...]]:
    aliases: dict[str, set[str]] = defaultdict(set)
    for row in player_master.itertuples(index=False):
        gsis_id = str(getattr(row, "gsis_id", "") or "").strip()
        if not gsis_id:
            continue
        raw_aliases = [
            getattr(row, "display_name", ""),
            getattr(row, "football_name", ""),
            _join_name(getattr(row, "first_name", ""), getattr(row, "last_name", "")),
            _join_name(getattr(row, "common_first_name", ""), getattr(row, "last_name", "")),
        ]
        for raw in raw_aliases:
            alias = normalize_name_token(raw)
            if alias:
                aliases[alias].add(gsis_id)
    return {key: tuple(sorted(values)) for key, values in aliases.items()}


def attach_stable_identity_v2(
    external: pd.DataFrame,
    nflverse: pd.DataFrame,
    player_master: pd.DataFrame,
) -> pd.DataFrame:
    out = attach_stable_identity_v1(external, nflverse)
    alias_lookup = build_player_alias_lookup(player_master)

    canonical = nflverse.copy()
    canonical["team"] = canonical["team"].map(normalize_team)
    canonical["season"] = pd.to_numeric(canonical["season"], errors="raise").astype(int)
    canonical["week"] = pd.to_numeric(canonical["week"], errors="raise").astype(int)
    team_week_ids = (
        canonical.groupby(["season", "week", "team"], dropna=False)["gsis_id"]
        .agg(lambda values: frozenset(str(v) for v in values if pd.notna(v) and str(v).strip()))
        .to_dict()
    )

    for idx, row in out.iterrows():
        if str(row.get("identity_match_state", "")) != "unmatched":
            continue
        alias = normalize_name_token(row.get("external_player", ""))
        if not alias:
            continue
        alias_candidates = set(alias_lookup.get(alias, ()))
        if not alias_candidates:
            out.at[idx, "identity_match_method"] = "player_master_alias_no_match"
            continue
        key = (int(row["season"]), int(row["week"]), normalize_team(row["team"]))
        historical_ids = set(team_week_ids.get(key, frozenset()))
        candidates = sorted(alias_candidates & historical_ids)
        if len(candidates) == 1:
            out.at[idx, "gsis_id"] = candidates[0]
            out.at[idx, "identity_match_state"] = "unique"
            out.at[idx, "identity_match_method"] = "player_master_alias_team_week"
        elif len(candidates) > 1:
            out.at[idx, "gsis_id"] = ""
            out.at[idx, "identity_match_state"] = "ambiguous"
            out.at[idx, "identity_match_method"] = "player_master_alias_team_week"
        else:
            out.at[idx, "identity_match_method"] = "player_master_alias_not_in_historical_team_week"
    return out
