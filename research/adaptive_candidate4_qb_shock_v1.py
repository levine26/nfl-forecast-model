from __future__ import annotations

"""Prospective QB information-shock extraction for Adaptive Candidate 4.

This module does not estimate player value. It freezes each team's QB1 from timestamped
nflverse depth-chart state at or before T-120 and checks whether that exact QB1 appears in
qualified official NFL inactive-article evidence known by T-60.
"""

from datetime import datetime, timedelta, timezone
import gzip
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

import pandas as pd

from research.inactive_article_player_parser_v1 import parse_inactive_article_html

CONTRACT_ID = "ADAPTIVE-CANDIDATE4-QB-SHOCK-SOURCE-V1"
SOURCE_ARCHIVE_ID = "NFL-INACTIVE-ARTICLE-SOURCE-2026-V1"
CANDIDATE_SOURCE_KIND = "nfl_inactives_news_article"
TEAM_NORMALIZATION = {"JAC": "JAX"}
SUFFIXES = {"jr", "sr", "ii", "iii", "iv"}


def _utc(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value is not None else None


def normalize_name(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    pieces = [part for part in text.split() if part]
    while pieces and pieces[-1] in SUFFIXES:
        pieces.pop()
    return " ".join(pieces)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
    return out


def _due_teams(games: list[dict[str, Any]]) -> set[str]:
    teams = {
        TEAM_NORMALIZATION.get(str(game.get(side) or "").strip().upper(), str(game.get(side) or "").strip().upper())
        for game in games
        for side in ("away_team", "home_team")
    }
    teams.discard("")
    if len(teams) != 2 * len(games):
        raise ValueError("due cohort contains missing or duplicate team identities")
    return teams


def _kickoff(games: list[dict[str, Any]]) -> datetime:
    kickoffs = {_utc(game.get("kickoff_utc")) for game in games}
    if None in kickoffs or len(kickoffs) != 1:
        raise ValueError("QB shock cohort must share one valid kickoff timestamp")
    return next(iter(kickoffs))  # type: ignore[arg-type]


def prepare_depth(depth: pd.DataFrame) -> pd.DataFrame:
    required = {"dt", "team", "player_name", "gsis_id", "pos_abb", "pos_rank"}
    missing = required - set(depth.columns)
    if missing:
        raise ValueError(f"depth charts missing fields: {sorted(missing)}")
    frame = depth.copy()
    frame["snapshot_utc"] = pd.to_datetime(frame["dt"], errors="coerce", utc=True)
    frame["team_norm"] = (
        frame["team"].astype("string").fillna("").str.upper().str.strip().replace(TEAM_NORMALIZATION)
    )
    frame["pos_abb_norm"] = frame["pos_abb"].astype("string").fillna("").str.upper().str.strip()
    frame["pos_rank_num"] = pd.to_numeric(frame["pos_rank"], errors="coerce")
    frame["player_name_norm"] = frame["player_name"].map(normalize_name)
    frame["gsis_norm"] = frame["gsis_id"].astype("string").fillna("").str.strip()
    return frame


def select_t120_qb1(
    depth: pd.DataFrame,
    *,
    team: str,
    kickoff_utc: datetime,
) -> tuple[dict[str, Any] | None, list[str]]:
    reasons: list[str] = []
    frame = prepare_depth(depth)
    team_norm = TEAM_NORMALIZATION.get(str(team).upper(), str(team).upper())
    target = kickoff_utc - timedelta(minutes=120)
    candidates = frame[
        frame["team_norm"].eq(team_norm)
        & frame["snapshot_utc"].notna()
        & frame["snapshot_utc"].le(target)
    ].copy()
    if candidates.empty:
        return None, ["missing_depth_state_by_t120"]

    snapshot_time = candidates["snapshot_utc"].max()
    snapshot = candidates[candidates["snapshot_utc"].eq(snapshot_time)].copy()
    qb = snapshot[
        snapshot["pos_abb_norm"].eq("QB")
        & snapshot["pos_rank_num"].eq(1)
    ].copy()
    qb = qb[
        qb["gsis_norm"].ne("")
        & qb["player_name_norm"].ne("")
    ]
    identities = qb[["gsis_norm", "player_name", "player_name_norm"]].drop_duplicates()
    if len(identities) != 1:
        return None, ["ambiguous_or_missing_rank1_qb"]

    row = identities.iloc[0]
    return {
        "team": team_norm,
        "player_name": str(row["player_name"]).strip(),
        "player_name_norm": str(row["player_name_norm"]),
        "gsis_id": str(row["gsis_norm"]),
        "depth_timestamp_utc": _iso(snapshot_time.to_pydatetime()),
        "t120_target_utc": _iso(target),
    }, reasons


def _raw_bytes(archive_dir: Path, source: dict[str, Any]) -> bytes:
    relpath = str(source.get("raw_object_relpath") or "")
    expected = str(source.get("raw_body_sha256") or "").lower()
    if not relpath or len(expected) != 64:
        raise ValueError("inactive source lacks content-addressed raw identity")
    path = archive_dir / relpath
    if not path.exists():
        raise FileNotFoundError(path)
    with gzip.open(path, "rb") as handle:
        raw = handle.read()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise RuntimeError(f"inactive article SHA mismatch: {observed} != {expected}")
    return raw


def select_inactive_evidence(
    *,
    archive_dir: Path,
    games: list[dict[str, Any]],
    t60_target_utc: datetime,
    t120_target_utc: datetime,
) -> dict[str, Any] | None:
    """Select the latest qualifying archived article state no later than T-60."""
    due_game_ids = {str(game.get("game_id") or "") for game in games}
    due_teams = _due_teams(games)
    observations = _read_jsonl(archive_dir / "observations.jsonl")
    eligible: list[dict[str, Any]] = []
    for observation in observations:
        if observation.get("archive_id") != SOURCE_ARCHIVE_ID:
            continue
        captured = _utc(observation.get("captured_at_utc"))
        if captured is None or captured <= t120_target_utc or captured > t60_target_utc:
            continue
        observed_ids = {str(game.get("game_id") or "") for game in observation.get("due_games") or []}
        if not due_game_ids.issubset(observed_ids):
            continue
        copy = dict(observation)
        copy["_captured_dt"] = captured
        eligible.append(copy)

    for observation in sorted(eligible, key=lambda row: row["_captured_dt"], reverse=True):
        matches: list[dict[str, Any]] = []
        for source in observation.get("sources") or []:
            if source.get("source_kind") != CANDIDATE_SOURCE_KIND:
                continue
            if int(source.get("http_status", 999)) >= 400:
                continue
            raw = _raw_bytes(archive_dir, source)
            parsed = parse_inactive_article_html(
                raw,
                source_url=str(source.get("url") or ""),
                captured_at_utc=_iso(observation["_captured_dt"]) or "",
                raw_html_sha256=str(source.get("raw_body_sha256") or ""),
            )
            observed_teams = {str(row["team"]) for row in parsed.rows}
            if due_teams.issubset(observed_teams):
                matches.append(
                    {
                        "source": source,
                        "parsed": parsed,
                        "raw_sha256": str(source.get("raw_body_sha256") or ""),
                    }
                )
        shas = sorted({row["raw_sha256"] for row in matches})
        if len(shas) > 1:
            raise RuntimeError(f"multiple distinct inactive article bodies match due cohort: {shas}")
        if len(shas) == 1:
            chosen = sorted(matches, key=lambda row: str(row["source"].get("url") or ""))[0]
            cohort_rows = [
                row for row in chosen["parsed"].rows if str(row["team"]) in due_teams
            ]
            if {str(row["team"]) for row in cohort_rows} != due_teams:
                continue
            return {
                "captured_at_utc": _iso(observation["_captured_dt"]),
                "source_url": str(chosen["source"].get("url") or ""),
                "raw_sha256": shas[0],
                "cohort_rows": cohort_rows,
                "parser_audit": chosen["parsed"].audit,
            }
    return None


def build_qb_shock_rows(
    depth: pd.DataFrame,
    *,
    archive_dir: Path,
    games: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build one Candidate 4 QB-state row per game in one kickoff cohort."""
    kickoff = _kickoff(games)
    t120 = kickoff - timedelta(minutes=120)
    t60 = kickoff - timedelta(minutes=60)
    evidence = select_inactive_evidence(
        archive_dir=archive_dir,
        games=games,
        t60_target_utc=t60,
        t120_target_utc=t120,
    )
    snapshots: dict[str, tuple[dict[str, Any] | None, list[str]]] = {}
    for team in sorted(_due_teams(games)):
        snapshots[team] = select_t120_qb1(depth, team=team, kickoff_utc=kickoff)

    inactive_by_team: dict[str, set[str]] = {}
    if evidence is not None:
        for row in evidence["cohort_rows"]:
            team = str(row["team"])
            inactive_by_team.setdefault(team, set()).add(normalize_name(row["player_name_rendered"]))

    output: list[dict[str, Any]] = []
    for game in games:
        home = TEAM_NORMALIZATION.get(str(game["home_team"]).upper(), str(game["home_team"]).upper())
        away = TEAM_NORMALIZATION.get(str(game["away_team"]).upper(), str(game["away_team"]).upper())
        home_qb, home_reasons = snapshots[home]
        away_qb, away_reasons = snapshots[away]
        reasons = [f"home_{reason}" for reason in home_reasons] + [
            f"away_{reason}" for reason in away_reasons
        ]
        if evidence is None:
            reasons.append("no_qualified_inactive_article_by_t60")

        home_inactive = False
        away_inactive = False
        if home_qb is not None and evidence is not None:
            home_inactive = home_qb["player_name_norm"] in inactive_by_team.get(home, set())
        if away_qb is not None and evidence is not None:
            away_inactive = away_qb["player_name_norm"] in inactive_by_team.get(away, set())
        if home_inactive and away_inactive:
            reasons.append("both_t120_qbs_inactive_direction_ambiguous")

        if reasons:
            direction: int | None = None
        elif home_inactive:
            direction = -1
        elif away_inactive:
            direction = 1
        else:
            direction = 0

        complete = not reasons
        row = {
            "schema_version": "adaptive-candidate4-qb-shock-v1",
            "contract_id": CONTRACT_ID,
            "depth_source": "nflverse_depth_charts_via_nflreadpy",
            "game_id": str(game["game_id"]),
            "home_team": home,
            "away_team": away,
            "kickoff_utc": _iso(kickoff),
            "t120_target_utc": _iso(kickoff - timedelta(minutes=120)),
            "t60_target_utc": _iso(t60),
            "home_t120_qb1_player_name": home_qb["player_name"] if home_qb else None,
            "home_t120_qb1_gsis_id": home_qb["gsis_id"] if home_qb else None,
            "home_t120_depth_timestamp_utc": home_qb["depth_timestamp_utc"] if home_qb else None,
            "away_t120_qb1_player_name": away_qb["player_name"] if away_qb else None,
            "away_t120_qb1_gsis_id": away_qb["gsis_id"] if away_qb else None,
            "away_t120_depth_timestamp_utc": away_qb["depth_timestamp_utc"] if away_qb else None,
            "home_t120_qb1_inactive": home_inactive if complete else None,
            "away_t120_qb1_inactive": away_inactive if complete else None,
            "qb_shock_direction": direction,
            "qb_shock_known_by_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_capture_timestamp_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_source_url": evidence["source_url"] if evidence else None,
            "inactive_raw_sha256": evidence["raw_sha256"] if evidence else None,
            "qb_state_complete": complete,
            "source_qualified": evidence is not None,
            "incomplete_reasons": "|".join(sorted(set(reasons))),
            "research_only": True,
            "production_authorized": False,
            "player_value_magnitude_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        digest_basis = {
            key: value
            for key, value in row.items()
            if key not in {"qb_state_sha256"}
        }
        row["qb_state_sha256"] = hashlib.sha256(
            json.dumps(digest_basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        output.append(row)
    return pd.DataFrame(output)



def append_immutable_qb_state(
    existing: pd.DataFrame | None,
    new_rows: pd.DataFrame,
) -> pd.DataFrame:
    """Append first-seen QB states; any scientific rewrite fails closed."""
    if existing is None or existing.empty:
        return new_rows.copy().reset_index(drop=True)
    required = {"game_id", "qb_state_sha256"}
    if not required.issubset(existing.columns):
        raise ValueError("existing Candidate 4 QB ledger lacks immutable identity fields")
    if existing["game_id"].astype(str).duplicated().any():
        raise ValueError("existing Candidate 4 QB ledger has duplicate game_id")

    out = existing.copy()
    known = {
        str(row["game_id"]): str(row["qb_state_sha256"])
        for row in out.to_dict("records")
    }
    additions: list[dict[str, Any]] = []
    for row in new_rows.to_dict("records"):
        game_id = str(row["game_id"])
        digest = str(row["qb_state_sha256"])
        if game_id in known:
            if known[game_id] != digest:
                raise ValueError(
                    f"immutable Candidate 4 QB-state rewrite attempted for {game_id}"
                )
            continue
        additions.append(row)
        known[game_id] = digest
    if additions:
        out = pd.concat([out, pd.DataFrame(additions)], ignore_index=True, sort=False)
    return out.reset_index(drop=True)



def _validated_frozen_qb1_snapshot(
    row: dict[str, Any] | None,
    *,
    game: dict[str, Any],
    kickoff: datetime,
) -> tuple[dict[str, Any] | None, list[str]]:
    """Validate the immutable T-120 QB1 evidence for one game."""
    if row is None:
        return None, ["missing_t120_qb1_snapshot"]

    reasons: list[str] = []
    home = TEAM_NORMALIZATION.get(str(game.get("home_team") or "").upper(), str(game.get("home_team") or "").upper())
    away = TEAM_NORMALIZATION.get(str(game.get("away_team") or "").upper(), str(game.get("away_team") or "").upper())
    target = kickoff - timedelta(minutes=120)
    captured = _utc(row.get("captured_at_utc"))
    row_target = _utc(row.get("t120_target_utc"))
    row_kickoff = _utc(row.get("kickoff_utc"))

    if str(row.get("candidate_id") or "") != "ADAPTIVE-CONDITIONAL-INFORMATION-ARRIVAL-V1":
        reasons.append("qb1_snapshot_candidate_mismatch")
    if str(row.get("preregistration_sha") or "") != "74ecd303545c09f57593546472d27438e3d8a204":
        reasons.append("qb1_snapshot_preregistration_mismatch")
    if not bool(row.get("qb1_snapshot_complete")):
        reasons.append("qb1_snapshot_incomplete")
    if not bool(row.get("research_only")):
        reasons.append("qb1_snapshot_not_research_only")
    if bool(row.get("production_authorized")):
        reasons.append("qb1_snapshot_production_authorized")
    if str(row.get("home_team") or "").upper() != home:
        reasons.append("qb1_snapshot_home_team_mismatch")
    if str(row.get("away_team") or "").upper() != away:
        reasons.append("qb1_snapshot_away_team_mismatch")
    if row_kickoff is None or row_kickoff != kickoff:
        reasons.append("qb1_snapshot_kickoff_mismatch")
    if row_target is None or abs((row_target - target).total_seconds()) > 1.0:
        reasons.append("qb1_snapshot_target_mismatch")
    if captured is None:
        reasons.append("qb1_snapshot_capture_missing")
    else:
        timing_error = (captured - target).total_seconds() / 60.0
        if timing_error < -7.5 or timing_error > 0.0:
            reasons.append("qb1_snapshot_capture_outside_t120_window")

    required = (
        "home_t120_qb1_player_name",
        "home_t120_qb1_gsis_id",
        "away_t120_qb1_player_name",
        "away_t120_qb1_gsis_id",
        "qb1_snapshot_sha256",
    )
    for field in required:
        if not str(row.get(field) or "").strip():
            reasons.append(f"missing_{field}")

    for side in ("home", "away"):
        depth_time = _utc(row.get(f"{side}_t120_depth_timestamp_utc"))
        if depth_time is None:
            reasons.append(f"missing_{side}_t120_depth_timestamp")
            continue
        if depth_time > target:
            reasons.append(f"{side}_depth_state_after_t120")
        if captured is not None and depth_time > captured:
            reasons.append(f"{side}_depth_state_not_observed_by_snapshot_capture")

    return (dict(row) if not reasons else None), reasons


def build_qb_shock_rows_from_snapshots(
    qb1_snapshots: pd.DataFrame,
    *,
    archive_dir: Path,
    games: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build T-60 QB shocks using only immutable T-120 QB1 snapshots.

    This is the live Candidate 4 path. No depth-chart source is queried or re-derived here.
    """
    kickoff = _kickoff(games)
    t120 = kickoff - timedelta(minutes=120)
    t60 = kickoff - timedelta(minutes=60)
    evidence = select_inactive_evidence(
        archive_dir=archive_dir,
        games=games,
        t60_target_utc=t60,
        t120_target_utc=t120,
    )

    if qb1_snapshots.empty:
        snapshot_by_game: dict[str, dict[str, Any]] = {}
    else:
        if "game_id" not in qb1_snapshots.columns:
            raise ValueError("QB1 snapshot ledger missing game_id")
        if qb1_snapshots["game_id"].astype(str).duplicated().any():
            raise ValueError("QB1 snapshot ledger contains duplicate game_id")
        snapshot_by_game = {
            str(row["game_id"]): dict(row)
            for row in qb1_snapshots.to_dict("records")
        }

    inactive_by_team: dict[str, set[str]] = {}
    if evidence is not None:
        for row in evidence["cohort_rows"]:
            team = str(row["team"])
            inactive_by_team.setdefault(team, set()).add(
                normalize_name(row["player_name_rendered"])
            )

    output: list[dict[str, Any]] = []
    for game in games:
        game_id = str(game.get("game_id") or "")
        home = TEAM_NORMALIZATION.get(
            str(game.get("home_team") or "").upper(),
            str(game.get("home_team") or "").upper(),
        )
        away = TEAM_NORMALIZATION.get(
            str(game.get("away_team") or "").upper(),
            str(game.get("away_team") or "").upper(),
        )
        snapshot, reasons = _validated_frozen_qb1_snapshot(
            snapshot_by_game.get(game_id),
            game=game,
            kickoff=kickoff,
        )
        if evidence is None:
            reasons.append("no_qualified_inactive_article_by_t60")

        home_name = str((snapshot or {}).get("home_t120_qb1_player_name") or "")
        away_name = str((snapshot or {}).get("away_t120_qb1_player_name") or "")
        home_inactive = bool(
            snapshot is not None
            and normalize_name(home_name) in inactive_by_team.get(home, set())
        )
        away_inactive = bool(
            snapshot is not None
            and normalize_name(away_name) in inactive_by_team.get(away, set())
        )
        if home_inactive and away_inactive:
            reasons.append("both_t120_qbs_inactive_direction_ambiguous")

        complete = not reasons
        if not complete:
            direction: int | None = None
        elif home_inactive:
            direction = -1
        elif away_inactive:
            direction = 1
        else:
            direction = 0

        row = {
            "schema_version": "adaptive-candidate4-qb-shock-v1",
            "contract_id": CONTRACT_ID,
            "depth_source": "immutable_candidate4_t120_qb1_snapshot",
            "game_id": game_id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": _iso(kickoff),
            "t120_target_utc": _iso(t120),
            "t60_target_utc": _iso(t60),
            "qb1_snapshot_sha256": (snapshot or {}).get("qb1_snapshot_sha256"),
            "qb1_snapshot_captured_at_utc": (snapshot or {}).get("captured_at_utc"),
            "home_t120_qb1_player_name": (snapshot or {}).get("home_t120_qb1_player_name"),
            "home_t120_qb1_gsis_id": (snapshot or {}).get("home_t120_qb1_gsis_id"),
            "home_t120_depth_timestamp_utc": (snapshot or {}).get("home_t120_depth_timestamp_utc"),
            "away_t120_qb1_player_name": (snapshot or {}).get("away_t120_qb1_player_name"),
            "away_t120_qb1_gsis_id": (snapshot or {}).get("away_t120_qb1_gsis_id"),
            "away_t120_depth_timestamp_utc": (snapshot or {}).get("away_t120_depth_timestamp_utc"),
            "home_t120_qb1_inactive": home_inactive if complete else None,
            "away_t120_qb1_inactive": away_inactive if complete else None,
            "qb_shock_direction": direction,
            "qb_shock_known_by_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_capture_timestamp_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_source_url": evidence["source_url"] if evidence else None,
            "inactive_raw_sha256": evidence["raw_sha256"] if evidence else None,
            "qb_state_complete": bool(complete),
            "source_qualified": bool(snapshot is not None and evidence is not None),
            "incomplete_reasons": "|".join(sorted(set(reasons))),
            "research_only": True,
            "production_authorized": False,
            "player_value_magnitude_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        digest_basis = {
            key: value for key, value in row.items() if key != "qb_state_sha256"
        }
        row["qb_state_sha256"] = hashlib.sha256(
            json.dumps(
                digest_basis,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ).hexdigest()
        output.append(row)
    return pd.DataFrame(output)


def build_qb_shock_rows_from_snapshot(
    qb1_snapshots: pd.DataFrame,
    *,
    archive_dir: Path,
    games: list[dict[str, Any]],
) -> pd.DataFrame:
    """Build Candidate 4 QB shock rows only from frozen T-120 QB1 snapshots."""
    kickoff = _kickoff(games)
    t120 = kickoff - timedelta(minutes=120)
    t60 = kickoff - timedelta(minutes=60)
    evidence = select_inactive_evidence(
        archive_dir=archive_dir,
        games=games,
        t60_target_utc=t60,
        t120_target_utc=t120,
    )

    if qb1_snapshots.empty or "game_id" not in qb1_snapshots.columns:
        snapshot_by_game: dict[str, dict[str, Any]] = {}
    else:
        if qb1_snapshots["game_id"].astype(str).duplicated().any():
            raise ValueError("QB1 snapshot ledger contains duplicate game_id")
        snapshot_by_game = {
            str(row["game_id"]): dict(row)
            for row in qb1_snapshots.to_dict("records")
        }

    inactive_by_team: dict[str, set[str]] = {}
    if evidence is not None:
        for row in evidence["cohort_rows"]:
            team = str(row["team"])
            inactive_by_team.setdefault(team, set()).add(normalize_name(row["player_name_rendered"]))

    output: list[dict[str, Any]] = []
    for game in games:
        game_id = str(game["game_id"])
        home = TEAM_NORMALIZATION.get(str(game["home_team"]).upper(), str(game["home_team"]).upper())
        away = TEAM_NORMALIZATION.get(str(game["away_team"]).upper(), str(game["away_team"]).upper())
        snapshot = snapshot_by_game.get(game_id)
        reasons: list[str] = []

        if snapshot is None:
            reasons.append("missing_frozen_t120_qb1_snapshot")
        else:
            if str(snapshot.get("home_team") or "").upper() != home:
                reasons.append("home_team_snapshot_identity_mismatch")
            if str(snapshot.get("away_team") or "").upper() != away:
                reasons.append("away_team_snapshot_identity_mismatch")
            if not bool(snapshot.get("qb1_snapshot_complete")):
                reasons.append("frozen_t120_qb1_snapshot_incomplete")
            if str(snapshot.get("research_only") or "").lower() not in {"true", "1"}:
                reasons.append("qb1_snapshot_not_research_only")
            if str(snapshot.get("production_authorized") or "").lower() in {"true", "1"}:
                reasons.append("qb1_snapshot_production_authorized")
            captured = _utc(snapshot.get("captured_at_utc"))
            target = _utc(snapshot.get("t120_target_utc"))
            if captured is None or target is None or captured > target:
                reasons.append("qb1_snapshot_not_captured_by_t120")
            elif (captured - target).total_seconds() / 60.0 < -7.5:
                reasons.append("qb1_snapshot_outside_frozen_t120_window")

        if evidence is None:
            reasons.append("no_qualified_inactive_article_by_t60")

        home_name = str((snapshot or {}).get("home_t120_qb1_player_name") or "").strip()
        away_name = str((snapshot or {}).get("away_t120_qb1_player_name") or "").strip()
        home_gsis = str((snapshot or {}).get("home_t120_qb1_gsis_id") or "").strip()
        away_gsis = str((snapshot or {}).get("away_t120_qb1_gsis_id") or "").strip()
        if not home_name or not home_gsis:
            reasons.append("missing_home_frozen_qb1_identity")
        if not away_name or not away_gsis:
            reasons.append("missing_away_frozen_qb1_identity")

        home_inactive = bool(
            home_name and evidence is not None
            and normalize_name(home_name) in inactive_by_team.get(home, set())
        )
        away_inactive = bool(
            away_name and evidence is not None
            and normalize_name(away_name) in inactive_by_team.get(away, set())
        )
        if home_inactive and away_inactive:
            reasons.append("both_t120_qbs_inactive_direction_ambiguous")

        if reasons:
            direction: int | None = None
        elif home_inactive:
            direction = -1
        elif away_inactive:
            direction = 1
        else:
            direction = 0

        complete = not reasons
        row = {
            "schema_version": "adaptive-candidate4-qb-shock-v1",
            "contract_id": CONTRACT_ID,
            "game_id": game_id,
            "home_team": home,
            "away_team": away,
            "kickoff_utc": _iso(kickoff),
            "t120_target_utc": _iso(t120),
            "t60_target_utc": _iso(t60),
            "home_t120_qb1_player_name": home_name or None,
            "home_t120_qb1_gsis_id": home_gsis or None,
            "home_t120_depth_timestamp_utc": (snapshot or {}).get("home_t120_depth_timestamp_utc"),
            "away_t120_qb1_player_name": away_name or None,
            "away_t120_qb1_gsis_id": away_gsis or None,
            "away_t120_depth_timestamp_utc": (snapshot or {}).get("away_t120_depth_timestamp_utc"),
            "home_t120_qb1_inactive": home_inactive if complete else None,
            "away_t120_qb1_inactive": away_inactive if complete else None,
            "qb_shock_direction": direction,
            "qb_shock_known_by_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_capture_timestamp_utc": evidence["captured_at_utc"] if evidence else None,
            "inactive_source_url": evidence["source_url"] if evidence else None,
            "inactive_raw_sha256": evidence["raw_sha256"] if evidence else None,
            "qb1_snapshot_sha256": (snapshot or {}).get("qb1_snapshot_sha256"),
            "qb1_snapshot_captured_at_utc": (snapshot or {}).get("captured_at_utc"),
            "qb_state_complete": complete,
            "source_qualified": evidence is not None and snapshot is not None and not reasons,
            "incomplete_reasons": "|".join(sorted(set(reasons))),
            "research_only": True,
            "production_authorized": False,
            "player_value_magnitude_authorized": False,
            "completed_2026_outcomes_used": 0,
        }
        digest_basis = {key: value for key, value in row.items() if key != "qb_state_sha256"}
        row["qb_state_sha256"] = hashlib.sha256(
            json.dumps(digest_basis, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        output.append(row)
    return pd.DataFrame(output)
