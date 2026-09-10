from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import json
import numpy as np
import pandas as pd

LOCK_WINDOW_MINUTES = 120.0

CURRENT_COLUMNS = [
    "game_id","season","week","gameday","gametime","away_team","home_team",
    "sujar_home_prob","pure_home_prob","market_home_prob","final_home_prob","pick",
    "fair_home_moneyline","expected_margin","margin_sigma","margin_low_80","margin_high_80",
    "expected_total","total_sigma","total_low_80","total_high_80","projected_score",
    "spread_line","total_line","model_edge","cover_home_prob","over_prob","confidence",
    "model_disagreement","consistency_flag","market_available","data_state","snapshot_type",
    "model_version","prediction_timestamp_utc",
    # Append-only legacy diagnostics retained for backward-compatible consumers.
    "logistic_home_prob","extra_trees_home_prob","xgboost_home_prob","catboost_home_prob",
    "elo_home_prob","home_elo","away_elo",
    # Append-only F-ST accountability fields. Old locked rows remain null here.
    "legacy_pure_home_prob","legacy_final_home_prob","fst_pure_home_prob",
    "final_probability_strategy","fst_artifact_id","fst_artifact_training_data_sha256",
    "fst_artifact_freeze_implementation_sha","fst_fallback","fst_fallback_reason",
    "fst_vs_market_delta","fst_vs_legacy_delta","legacy_confidence",
    "legacy_consistency_flag","confidence_diagnostic_scope",
]

LOCK_META_COLUMNS = [
    "kickoff_utc","lock_timestamp_utc","minutes_to_kickoff_at_lock","lock_status",
    "actual_home_score","actual_away_score","actual_margin","actual_total","winner_correct",
    "margin_abs_error","total_abs_error","actual_home_cover","actual_over",
]

BOOLEAN_GRADE_COLUMNS = ["winner_correct", "actual_home_cover", "actual_over"]


def kickoff_utc(gameday, gametime) -> datetime:
    """nflverse gametime is Eastern time; convert the scheduled kickoff to UTC."""
    text = f"{str(gameday)[:10]} {str(gametime)[:5]}"
    dt = datetime.strptime(text, "%Y-%m-%d %H:%M")
    return dt.replace(tzinfo=ZoneInfo("America/New_York")).astimezone(timezone.utc)


def _available_current_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in CURRENT_COLUMNS if c in df.columns]


def _empty_official(columns: list[str]) -> pd.DataFrame:
    frame = pd.DataFrame(columns=columns + [c for c in LOCK_META_COLUMNS if c not in columns])
    for c in BOOLEAN_GRADE_COLUMNS:
        if c in frame.columns:
            frame[c] = pd.Series(dtype="boolean")
    return frame


def _coerce_grade_dtypes(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy()
    for c in BOOLEAN_GRADE_COLUMNS:
        if c not in frame.columns:
            frame[c] = pd.Series(pd.NA, index=frame.index, dtype="boolean")
        else:
            frame[c] = pd.array(frame[c], dtype="boolean")
    return frame


def _load_official(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return _empty_official(columns)
    try:
        old = pd.read_csv(path)
    except Exception:
        return _empty_official(columns)
    if "lock_status" not in old.columns:
        return _empty_official(columns)
    old = old[old["lock_status"].eq("LOCKED")].copy()
    for c in columns + LOCK_META_COLUMNS:
        if c not in old.columns:
            old[c] = pd.NA if c in BOOLEAN_GRADE_COLUMNS else np.nan
    old = old[columns + [c for c in LOCK_META_COLUMNS if c not in columns]]
    return _coerce_grade_dtypes(old)


def _append_run_history(p: pd.DataFrame, path: Path, columns: list[str]) -> None:
    audit = p[columns].copy()
    audit["prediction_id"] = (
        audit["game_id"].astype(str) + "__" + audit.get("snapshot_type", "RUN").astype(str)
        + "__" + audit.get("prediction_timestamp_utc", "").astype(str)
    )
    if path.exists():
        try:
            old = pd.read_csv(path)
            audit = pd.concat([old, audit], ignore_index=True)
        except Exception:
            pass
    audit = audit.drop_duplicates("prediction_id", keep="last")
    audit.to_csv(path, index=False)


def _write_power_ratings(power: pd.DataFrame, path: Path) -> None:
    current = power.copy()
    if current.empty:
        current.to_csv(path, index=False)
        return
    previous = None
    if path.exists():
        try:
            old = pd.read_csv(path)
            if {"team", "rank"}.issubset(old.columns):
                previous = old[["team", "rank"]].drop_duplicates("team", keep="last").rename(columns={"rank": "previous_rank"})
        except Exception:
            previous = None
    if previous is not None:
        current = current.merge(previous, on="team", how="left")
    else:
        current["previous_rank"] = np.nan
    current["rank_change"] = current["previous_rank"] - current["rank"]

    def movement(row) -> str:
        if pd.isna(row.get("previous_rank")):
            return "NEW"
        change = int(row.get("rank_change", 0))
        if change > 0:
            return f"▲{change}"
        if change < 0:
            return f"▼{abs(change)}"
        return "→"

    current["movement"] = current.apply(movement, axis=1)
    order = [
        "rank","team","elo_plus","off_epa","def_epa_allowed","pass_epa","recent_win_pct",
        "rank_change","movement","as_of",
    ]
    current[[c for c in order if c in current.columns]].to_csv(path, index=False)


def _lock_new_games(
    official: pd.DataFrame,
    p: pd.DataFrame,
    columns: list[str],
    now_utc: datetime,
    lock_window_minutes: float,
) -> pd.DataFrame:
    already = set(official["game_id"].astype(str)) if len(official) else set()
    new_rows = []
    for _, row in p.iterrows():
        gid = str(row.get("game_id"))
        if gid in already:
            continue
        try:
            ko = kickoff_utc(row.get("gameday"), row.get("gametime"))
        except Exception:
            continue
        minutes = (ko - now_utc).total_seconds() / 60.0
        if not (0.0 < minutes <= lock_window_minutes):
            continue
        locked = {c: row.get(c, np.nan) for c in columns}
        locked.update({
            "kickoff_utc": ko.isoformat(),
            "lock_timestamp_utc": now_utc.isoformat(),
            "minutes_to_kickoff_at_lock": float(minutes),
            "lock_status": "LOCKED",
            "actual_home_score": np.nan,
            "actual_away_score": np.nan,
            "actual_margin": np.nan,
            "actual_total": np.nan,
            "winner_correct": pd.NA,
            "margin_abs_error": np.nan,
            "total_abs_error": np.nan,
            "actual_home_cover": pd.NA,
            "actual_over": pd.NA,
        })
        new_rows.append(locked)
        already.add(gid)
    if new_rows:
        official = pd.concat([official, pd.DataFrame(new_rows)], ignore_index=True)
    return _coerce_grade_dtypes(official)


def _grade_locked_games(official: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    if official.empty or games is None or "game_id" not in games.columns:
        return official
    official = _coerce_grade_dtypes(official)
    result_cols = [c for c in ["game_id","home_team","away_team","home_score","away_score"] if c in games.columns]
    if not {"game_id","home_score","away_score"}.issubset(result_cols):
        return official
    results = games[result_cols].drop_duplicates("game_id", keep="last").set_index("game_id")
    for i, row in official.iterrows():
        gid = row["game_id"]
        if gid not in results.index:
            continue
        res = results.loc[gid]
        hs = pd.to_numeric(res.get("home_score"), errors="coerce")
        aw = pd.to_numeric(res.get("away_score"), errors="coerce")
        if pd.isna(hs) or pd.isna(aw):
            continue
        margin = float(hs - aw)
        total = float(hs + aw)
        official.at[i, "actual_home_score"] = float(hs)
        official.at[i, "actual_away_score"] = float(aw)
        official.at[i, "actual_margin"] = margin
        official.at[i, "actual_total"] = total
        actual_winner = row.get("home_team") if margin > 0 else row.get("away_team")
        official.at[i, "winner_correct"] = bool(str(row.get("pick")) == str(actual_winner))
        pred_margin = pd.to_numeric(row.get("expected_margin"), errors="coerce")
        pred_total = pd.to_numeric(row.get("expected_total"), errors="coerce")
        if pd.notna(pred_margin):
            official.at[i, "margin_abs_error"] = abs(float(pred_margin) - margin)
        if pd.notna(pred_total):
            official.at[i, "total_abs_error"] = abs(float(pred_total) - total)
        spread = pd.to_numeric(row.get("spread_line"), errors="coerce")
        line_total = pd.to_numeric(row.get("total_line"), errors="coerce")
        if pd.notna(spread):
            official.at[i, "actual_home_cover"] = bool(margin > float(spread)) if margin != float(spread) else pd.NA
        if pd.notna(line_total):
            official.at[i, "actual_over"] = bool(total > float(line_total)) if total != float(line_total) else pd.NA
    return official


def write_outputs(
    artifacts,
    output_dir="outputs",
    now_utc: datetime | None = None,
    lock_window_minutes: float = LOCK_WINDOW_MINUTES,
) -> None:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    now_utc = now_utc or datetime.now(timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    else:
        now_utc = now_utc.astimezone(timezone.utc)

    p = artifacts.predictions.copy()
    cols = _available_current_columns(p)
    p[cols].to_csv(out / "this_week.csv", index=False)
    _append_run_history(p, out / "run_history.csv", cols)

    if hasattr(artifacts, "power_ratings"):
        _write_power_ratings(artifacts.power_ratings, out / "power_ratings.csv")
    if hasattr(artifacts, "leaderboard") and artifacts.leaderboard is not None:
        artifacts.leaderboard.to_csv(out / "model_leaderboard.csv", index=False)

    official_path = out / "prediction_history.csv"
    official = _load_official(official_path, cols)
    official = _lock_new_games(official, p, cols, now_utc, lock_window_minutes)
    official = _grade_locked_games(official, artifacts.games)
    official.to_csv(official_path, index=False)

    next_kickoff = None
    if len(p):
        kos = []
        for _, r in p.iterrows():
            try:
                kos.append(kickoff_utc(r.get("gameday"), r.get("gametime")))
            except Exception:
                pass
        future = [x for x in kos if x > now_utc]
        if future:
            next_kickoff = min(future).isoformat()
    market_available = p.get("market_available", pd.Series(False, index=p.index)).fillna(False).astype(bool)
    fallback = p.get("fst_fallback", pd.Series(False, index=p.index)).fillna(False).astype(bool)
    status = {
        "status": "healthy",
        "generated_utc": now_utc.isoformat(),
        "games": int(len(p)),
        "locked_official_predictions": int(len(official)),
        "power_rating_teams": int(len(getattr(artifacts, "power_ratings", []))),
        "next_kickoff_utc": next_kickoff,
        "model_version": str(p["model_version"].iloc[0]) if len(p) and "model_version" in p else None,
        "final_probability_strategy": str(p["final_probability_strategy"].iloc[0]) if len(p) and "final_probability_strategy" in p else None,
        "fst_artifact_id": str(p["fst_artifact_id"].iloc[0]) if len(p) and "fst_artifact_id" in p else None,
        "fst_artifact_training_data_sha256": str(p["fst_artifact_training_data_sha256"].iloc[0]) if len(p) and "fst_artifact_training_data_sha256" in p else None,
        "market_available_games": int(market_available.sum()),
        "market_missing_or_invalid_games": int((~market_available).sum()),
        "fst_fallback_count": int(fallback.sum()),
        "data_state": str(p["data_state"].iloc[0]) if len(p) and "data_state" in p else None,
    }
    (out / "status.json").write_text(json.dumps(status, indent=2), encoding="utf-8")
