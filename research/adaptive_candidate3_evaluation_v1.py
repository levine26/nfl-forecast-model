from __future__ import annotations

"""Canonical evaluation for ADAPTIVE-MARKET-PATH-INNOVATION-V1.

The candidate architecture is frozen in
research/ADAPTIVE_WEEKLY_CANDIDATE3_PREREGISTRATION.md at commit
52cf402cd33da0e535ef963c7d98f9b4304ea208.

This module must not be edited to improve target results. It scores the frozen candidate,
prespecified controls, robustness cells, and adversarial diagnostics.
"""

import argparse
import hashlib
import json
import math
import os
from math import comb
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pandas as pd

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

CANDIDATE_ID = "ADAPTIVE-MARKET-PATH-INNOVATION-V1"
PREREG_SHA = "52cf402cd33da0e535ef963c7d98f9b4304ea208"
ARCHIVE_SHA256 = "b03c4e7f1cf885e9f20ea808ee538c26c21df4065b342fe04c50d09b808c344c"
PRIMARY_LAMBDA = 0.50
ROBUSTNESS_LAMBDAS = (0.25, 0.50, 0.75, 1.00)
EARLY_LO_MIN = 1440
EARLY_HI_MIN = 2160
LOCK_WINDOWS = ((120, 360), (120, 300), (120, 240))
PRIMARY_LOCK = (120, 360)
MIN_COMMON_BOOKS = 5
BOOTSTRAP_DRAWS = 10_000
BOOTSTRAP_SEED = 20260922
BRIER_ALERT_DELTA = 0.0025
EPS = 1e-12

TEAM_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "Los Angeles Rams": "LA",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Commanders": "WAS",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def expit(x: Any) -> Any:
    x = np.asarray(x, dtype=float)
    out = np.empty_like(x, dtype=float)
    pos = x >= 0
    out[pos] = 1.0 / (1.0 + np.exp(-x[pos]))
    ex = np.exp(x[~pos])
    out[~pos] = ex / (1.0 + ex)
    return out


def logit(p: Any) -> Any:
    p = np.clip(np.asarray(p, dtype=float), 1e-12, 1 - 1e-12)
    return np.log(p / (1.0 - p))


def american_implied(price: pd.Series) -> pd.Series:
    a = pd.to_numeric(price, errors="coerce").astype(float)
    return pd.Series(
        np.where(a < 0.0, (-a) / ((-a) + 100.0), 100.0 / (a + 100.0)),
        index=price.index,
        dtype=float,
    )


def calibration_fit(prob: np.ndarray, outcome: np.ndarray) -> dict[str, float | None]:
    p = np.clip(np.asarray(prob, float), 1e-8, 1 - 1e-8)
    y = np.asarray(outcome, float)
    x = np.column_stack([np.ones(len(p)), logit(p)])
    beta = np.array([0.0, 1.0], dtype=float)
    try:
        for _ in range(100):
            eta = x @ beta
            mu = expit(eta)
            w = np.clip(mu * (1.0 - mu), 1e-8, None)
            info = x.T @ (x * w[:, None]) + np.eye(2) * 1e-10
            grad = x.T @ (y - mu)
            step = np.linalg.solve(info, grad)
            beta_next = beta + step
            if np.max(np.abs(step)) < 1e-10:
                beta = beta_next
                break
            beta = beta_next
        if not np.all(np.isfinite(beta)):
            raise ValueError("nonfinite calibration")
        return {"intercept": float(beta[0]), "slope": float(beta[1])}
    except Exception:
        return {"intercept": None, "slope": None}


def score_vector(name: str, prob: pd.Series, y: pd.Series) -> dict[str, Any]:
    p = np.clip(pd.to_numeric(prob, errors="coerce").to_numpy(float), 1e-12, 1 - 1e-12)
    yy = pd.to_numeric(y, errors="coerce").to_numpy(int)
    valid = np.isfinite(p)
    p = p[valid]
    yy = yy[valid]
    pick = (p >= 0.5).astype(int)
    correct = (pick == yy).astype(int)
    brier = float(np.mean((p - yy) ** 2)) if len(p) else None
    ll = float(np.mean(-(yy * np.log(p) + (1 - yy) * np.log(1 - p)))) if len(p) else None
    cal = calibration_fit(p, yy) if len(p) else {"intercept": None, "slope": None}
    return {
        "name": name,
        "games": int(len(p)),
        "correct": int(correct.sum()) if len(p) else 0,
        "accuracy": float(correct.mean()) if len(p) else None,
        "brier": brier,
        "log_loss": ll,
        "calibration_intercept": cal["intercept"],
        "calibration_slope": cal["slope"],
    }


def exact_mcnemar(c_only: int, b_only: int) -> float | None:
    n = int(c_only) + int(b_only)
    if n == 0:
        return None
    k = min(int(c_only), int(b_only))
    tail = sum(comb(n, i) for i in range(k + 1)) / (2 ** n)
    return float(min(1.0, 2.0 * tail))


def block_bootstrap(values: pd.Series, blocks: pd.Series) -> dict[str, Any]:
    frame = pd.DataFrame({"v": pd.to_numeric(values, errors="coerce"), "b": blocks.astype(str)}).dropna()
    grouped = [g["v"].to_numpy(float) for _, g in frame.groupby("b", sort=True)]
    if len(grouped) < 2:
        return {"draws": 0, "ci95_low": None, "ci95_high": None}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    draws = np.empty(BOOTSTRAP_DRAWS, dtype=float)
    for i in range(BOOTSTRAP_DRAWS):
        idx = rng.integers(0, len(grouped), size=len(grouped))
        draws[i] = float(np.concatenate([grouped[int(j)] for j in idx]).mean())
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {
        "draws": BOOTSTRAP_DRAWS,
        "seed": BOOTSTRAP_SEED,
        "blocks": len(grouped),
        "ci95_low": float(lo),
        "ci95_high": float(hi),
        "probability_gt_zero": float(np.mean(draws > 0.0)),
    }


def paired(candidate: pd.Series, benchmark: pd.Series, y: pd.Series, weeks: pd.Series) -> dict[str, Any]:
    pc = np.clip(pd.to_numeric(candidate, errors="coerce").to_numpy(float), 1e-12, 1 - 1e-12)
    pb = np.clip(pd.to_numeric(benchmark, errors="coerce").to_numpy(float), 1e-12, 1 - 1e-12)
    yy = pd.to_numeric(y, errors="coerce").to_numpy(int)
    c_pick = (pc >= 0.5).astype(int)
    b_pick = (pb >= 0.5).astype(int)
    c_corr = (c_pick == yy).astype(int)
    b_corr = (b_pick == yy).astype(int)
    diff = c_corr - b_corr
    disagree = c_pick != b_pick
    c_only = int(np.sum(disagree & (c_corr == 1)))
    b_only = int(np.sum(disagree & (b_corr == 1)))
    switches = c_only + b_only
    brier_diff = (pc - yy) ** 2 - (pb - yy) ** 2
    return {
        "games": int(len(yy)),
        "candidate_correct": int(c_corr.sum()),
        "benchmark_correct": int(b_corr.sum()),
        "candidate_accuracy": float(c_corr.mean()),
        "benchmark_accuracy": float(b_corr.mean()),
        "accuracy_delta": float(diff.mean()),
        "accuracy_delta_pp": float(diff.mean() * 100.0),
        "switches": int(switches),
        "candidate_only_correct": c_only,
        "benchmark_only_correct": b_only,
        "switch_win_rate": float(c_only / switches) if switches else None,
        "mcnemar_exact_two_sided_p": exact_mcnemar(c_only, b_only),
        "week_block_accuracy": block_bootstrap(pd.Series(diff), weeks.reset_index(drop=True)),
        "brier_delta": float(brier_diff.mean()),
        "week_block_brier": block_bootstrap(pd.Series(-brier_diff), weeks.reset_index(drop=True)),
    }


def load_fst(path: Path) -> pd.DataFrame:
    source = pd.read_csv(path)
    stack = build_chronological_logit_stack(source)
    pred = stack.predictions.copy()
    pred["game_id"] = source.loc[pred.index, "game_id"].astype(str).values
    pred["season"] = pd.to_numeric(pred["season"], errors="raise").astype(int)
    pred["home_win"] = pd.to_numeric(pred["home_win"], errors="raise").astype(int)
    pred["week"] = pred["game_id"].str.split("_").str[1].astype(int)
    pred["away_abbr"] = pred["game_id"].str.split("_").str[2]
    pred["home_abbr"] = pred["game_id"].str.split("_").str[3]
    pred = pred[pred["season"].eq(2025)].copy().sort_values(["week", "game_id"]).reset_index(drop=True)
    if len(pred) != 272:
        raise RuntimeError(f"F-ST 2025 row count mismatch: {len(pred)}")
    correct = int(((pred["stack_probability"] >= 0.5).astype(int) == pred["home_win"]).sum())
    if correct != 179:
        raise RuntimeError(f"F-ST benchmark mismatch: expected 179/272, got {correct}/272")
    pred = pred.rename(columns={"stack_probability": "fst_prob", "market_prob": "fst_market_prob"})
    return pred


def load_market_observations(db_path: Path, fst_ids: set[str]) -> pd.DataFrame:
    if sha256(db_path) != ARCHIVE_SHA256:
        raise RuntimeError("market archive digest mismatch")
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute(
        """
        select event_id, captured_at, game_start_time, home_team, away_team,
               sportsbook, nfl_week, outcome, price
        from main.stg_odds
        where market_type='h2h'
          and nfl_week between 1 and 18
          and captured_at < game_start_time
        """
    ).df()
    con.close()
    for col in ("captured_at", "game_start_time"):
        df[col] = pd.to_datetime(df[col], utc=True)
    df["nfl_week"] = pd.to_numeric(df["nfl_week"], errors="coerce").astype("Int64")
    df["home_abbr"] = df["home_team"].map(TEAM_ABBR)
    df["away_abbr"] = df["away_team"].map(TEAM_ABBR)
    if df[["home_abbr", "away_abbr"]].isna().any().any():
        missing = sorted(set(df.loc[df["home_abbr"].isna(), "home_team"].dropna()) |
                         set(df.loc[df["away_abbr"].isna(), "away_team"].dropna()))
        raise RuntimeError(f"unmapped team names: {missing}")
    df["game_id"] = (
        "2025_" + df["nfl_week"].astype(int).astype(str).str.zfill(2) + "_" +
        df["away_abbr"].astype(str) + "_" + df["home_abbr"].astype(str)
    )
    df = df[df["game_id"].isin(fst_ids)].copy()
    if df.empty:
        raise RuntimeError("no market rows map to F-ST 2025 games")

    identities = df.groupby("game_id")["event_id"].nunique()
    if int((identities > 1).sum()) != 0:
        bad = identities[identities > 1].to_dict()
        raise RuntimeError(f"ambiguous event identity: {bad}")

    df["side"] = np.where(
        df["outcome"].astype(str).eq(df["home_team"].astype(str)), "home",
        np.where(df["outcome"].astype(str).eq(df["away_team"].astype(str)), "away", None)
    )
    df = df[df["side"].notna()].copy()
    keys = [
        "game_id", "event_id", "sportsbook", "captured_at", "game_start_time",
        "home_team", "away_team", "nfl_week",
    ]
    piv = (
        df.pivot_table(index=keys, columns="side", values="price", aggfunc="first")
          .reset_index()
    )
    if "home" not in piv.columns or "away" not in piv.columns:
        raise RuntimeError("moneyline side pairing failed")
    piv = piv.dropna(subset=["home", "away"]).copy()
    qh = american_implied(piv["home"])
    qa = american_implied(piv["away"])
    denom = qh + qa
    piv["p_home"] = qh / denom
    piv = piv[np.isfinite(piv["p_home"]) & piv["p_home"].between(1e-8, 1 - 1e-8)].copy()
    piv["minutes_to_kickoff"] = (
        (piv["game_start_time"] - piv["captured_at"]).dt.total_seconds() / 60.0
    )
    if (piv["minutes_to_kickoff"] <= 0).any():
        raise RuntimeError("post-kickoff market row escaped source contract")
    return piv


def select_band(obs: pd.DataFrame, lo: int, hi: int) -> pd.DataFrame:
    x = obs[obs["minutes_to_kickoff"].between(lo, hi, inclusive="both")].copy()
    if x.empty:
        return x
    x = x.sort_values(["game_id", "sportsbook", "captured_at"])
    return x.groupby(["game_id", "sportsbook"], sort=False).tail(1).copy()


def build_path_features(obs: pd.DataFrame, lock_lo: int, lock_hi: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    early = select_band(obs, EARLY_LO_MIN, EARLY_HI_MIN)
    lock = select_band(obs, lock_lo, lock_hi)
    pair = early[
        ["game_id", "sportsbook", "p_home", "captured_at", "minutes_to_kickoff"]
    ].merge(
        lock[["game_id", "sportsbook", "p_home", "captured_at", "minutes_to_kickoff"]],
        on=["game_id", "sportsbook"],
        suffixes=("_early", "_lock"),
        how="inner",
    )
    if pair.empty:
        return pd.DataFrame(), pair
    pair["logit_early"] = logit(pair["p_home_early"].to_numpy(float))
    pair["logit_lock"] = logit(pair["p_home_lock"].to_numpy(float))
    pair["delta"] = pair["logit_lock"] - pair["logit_early"]

    rows = []
    for game_id, g in pair.groupby("game_id", sort=True):
        n = len(g)
        deltas = g["delta"].to_numpy(float)
        med = float(np.median(deltas))
        mad = float(np.median(np.abs(deltas - med)))
        rows.append({
            "game_id": game_id,
            "common_books": int(n),
            "path_qualified": bool(n >= MIN_COMMON_BOOKS),
            "path_delta_logit": med if n >= MIN_COMMON_BOOKS else np.nan,
            "p_early": float(expit(np.array([np.median(g["logit_early"])]))[0]) if n >= MIN_COMMON_BOOKS else np.nan,
            "p_lock": float(expit(np.array([np.median(g["logit_lock"])]))[0]) if n >= MIN_COMMON_BOOKS else np.nan,
            "home_move_share": float(np.mean(deltas > EPS)) if n >= MIN_COMMON_BOOKS else np.nan,
            "away_move_share": float(np.mean(deltas < -EPS)) if n >= MIN_COMMON_BOOKS else np.nan,
            "unchanged_share": float(np.mean(np.abs(deltas) <= EPS)) if n >= MIN_COMMON_BOOKS else np.nan,
            "delta_mad": mad if n >= MIN_COMMON_BOOKS else np.nan,
        })
    return pd.DataFrame(rows), pair


def build_final_market(obs: pd.DataFrame) -> pd.DataFrame:
    latest = obs.sort_values(["game_id", "sportsbook", "captured_at"]).groupby(
        ["game_id", "sportsbook"], sort=False
    ).tail(1).copy()
    latest["lp"] = logit(latest["p_home"].to_numpy(float))
    rows = []
    for game_id, g in latest.groupby("game_id", sort=True):
        rows.append({
            "game_id": game_id,
            "p_final_market": float(expit(np.array([np.median(g["lp"])]))[0]),
            "final_market_books": int(len(g)),
            "final_market_min_minutes_to_kickoff": float(g["minutes_to_kickoff"].min()),
        })
    return pd.DataFrame(rows)


def apply_candidate(frame: pd.DataFrame, lam: float, path_col: str = "path_delta_logit") -> pd.Series:
    d = pd.to_numeric(frame[path_col], errors="coerce").fillna(0.0).to_numpy(float)
    p = pd.to_numeric(frame["fst_prob"], errors="raise").to_numpy(float)
    return pd.Series(expit(logit(p) + lam * d), index=frame.index)


def metrics_for_controls(frame: pd.DataFrame, c2: pd.DataFrame) -> dict[str, Any]:
    merged = frame.merge(
        c2[[
            "game_id", "candidate1_prob", "weekly_refit_prob",
            "candidate_prob", "component_only_prob", "fst_prob"
        ]],
        on="game_id", how="left", suffixes=("", "_c2artifact"),
    )
    if merged[["candidate1_prob", "weekly_refit_prob", "candidate_prob", "component_only_prob"]].isna().any().any():
        raise RuntimeError("canonical Candidate 1/2 control vector missing 2025 rows")
    max_fst_diff = float(np.max(np.abs(merged["fst_prob"] - merged["fst_prob_c2artifact"])))
    if max_fst_diff > 1e-10:
        raise RuntimeError(f"Candidate2 artifact F-ST identity mismatch {max_fst_diff}")

    y = merged["home_win"]
    result = {
        "candidate1_unchanged": score_vector("ADAPTIVE-RESIDUAL-STATE-V1", merged["candidate1_prob"], y),
        "naive_weekly_refit_unchanged": score_vector("NAIVE-WEEKLY-FST-REFIT-CONTROL-V1", merged["weekly_refit_prob"], y),
        "candidate2_unchanged": score_vector("ADAPTIVE-REGIME-SHOCK-GATE-V1", merged["candidate_prob"], y),
        "component_resolved": score_vector("COMPONENT-RESOLVED-L2", merged["component_only_prob"], y),
    }
    return result


def book_deletion_adversarial(frame: pd.DataFrame, pairs: pd.DataFrame) -> list[dict[str, Any]]:
    books = sorted(pairs["sportsbook"].astype(str).unique())
    base = frame[["game_id", "fst_prob", "home_win"]].copy()
    out = []
    for book in books:
        filtered = pairs[pairs["sportsbook"].astype(str).ne(book)]
        rows = []
        for game_id, g in filtered.groupby("game_id", sort=False):
            if len(g) >= MIN_COMMON_BOOKS:
                rows.append((game_id, float(np.median(g["delta"].to_numpy(float)))))
        dmap = dict(rows)
        p = base["fst_prob"].to_numpy(float)
        d = base["game_id"].map(dmap).fillna(0.0).to_numpy(float)
        cand = expit(logit(p) + PRIMARY_LAMBDA * d)
        y = base["home_win"].to_numpy(int)
        delta_correct = int(((cand >= 0.5).astype(int) == y).sum() - ((p >= 0.5).astype(int) == y).sum())
        out.append({"deleted_book": book, "net_correct_vs_fst": delta_correct})
    return out


def adversarial(frame: pd.DataFrame, primary_pairs: pd.DataFrame, robustness: pd.DataFrame) -> dict[str, Any]:
    y = frame["home_win"].to_numpy(int)
    fst = frame["fst_prob"].to_numpy(float)
    c3 = frame["candidate3_prob"].to_numpy(float)
    fst_corr = ((fst >= 0.5).astype(int) == y).astype(int)
    c3_corr = ((c3 >= 0.5).astype(int) == y).astype(int)
    signed = c3_corr - fst_corr
    net = int(signed.sum())

    loo_week = []
    for week in sorted(frame["week"].unique()):
        mask = frame["week"].ne(week).to_numpy()
        n = int(mask.sum())
        loo_week.append({
            "omitted_week": int(week),
            "games": n,
            "net_correct_vs_fst": int(signed[mask].sum()),
            "accuracy_delta": float(signed[mask].mean()) if n else None,
        })

    teams = sorted(set(frame["away_abbr"]) | set(frame["home_abbr"]))
    loo_team = []
    team_contrib = []
    for team in teams:
        involved = (frame["away_abbr"].eq(team) | frame["home_abbr"].eq(team)).to_numpy()
        keep = ~involved
        loo_team.append({
            "omitted_team": team,
            "games": int(keep.sum()),
            "net_correct_vs_fst": int(signed[keep].sum()),
            "accuracy_delta": float(signed[keep].mean()) if keep.sum() else None,
        })
        team_contrib.append({"team": team, "signed_switch_contribution": int(signed[involved].sum())})

    single_game_nets = [int(net - v) for v in signed]
    switches = (c3 >= 0.5) != (fst >= 0.5)
    switch_frame = frame.loc[switches, ["game_id", "week", "away_abbr", "home_abbr", "fst_prob"]].copy()
    switch_frame["signed_contribution"] = signed[switches]
    if len(switch_frame):
        week_conc = switch_frame.groupby("week")["signed_contribution"].agg(["count", "sum"]).reset_index().to_dict("records")
    else:
        week_conc = []

    boundary = np.abs(frame.loc[switches, "fst_prob"].to_numpy(float) - 0.5) if switches.any() else np.array([])
    book_delete = book_deletion_adversarial(frame, primary_pairs)

    lambda_nonnegative = {}
    for lam in (0.25, 0.50, 0.75):
        cell = robustness[
            np.isclose(robustness["lambda"], lam) &
            robustness["lock_lo_min"].eq(PRIMARY_LOCK[0]) &
            robustness["lock_hi_min"].eq(PRIMARY_LOCK[1])
        ]
        lambda_nonnegative[str(lam)] = bool(len(cell) == 1 and float(cell.iloc[0]["accuracy_delta"]) >= 0.0)

    positive_team_contrib = [max(0, int(x["signed_switch_contribution"])) for x in team_contrib]
    max_team_positive = max(positive_team_contrib) if positive_team_contrib else 0
    team_share = (max_team_positive / net) if net > 0 else None

    return {
        "net_correct_gain": net,
        "single_game_deletion": {
            "min_net_correct": min(single_game_nets) if single_game_nets else None,
            "max_net_correct": max(single_game_nets) if single_game_nets else None,
            "any_deletion_makes_negative": any(v < 0 for v in single_game_nets),
            "single_game_supplies_entire_gain": bool(net > 0 and any(v == 0 for v in single_game_nets)),
        },
        "leave_one_week_out": loo_week,
        "leave_one_team_out": loo_team,
        "team_signed_contributions": team_contrib,
        "max_positive_team_contribution_share_of_net_gain": team_share,
        "week_switch_concentration": week_conc,
        "boundary_concentration": {
            "switches": int(switches.sum()),
            "median_abs_fst_distance_from_0_5_pp": float(np.median(boundary) * 100.0) if len(boundary) else None,
            "max_abs_fst_distance_from_0_5_pp": float(np.max(boundary) * 100.0) if len(boundary) else None,
            "within_2_5pp": int(np.sum(boundary <= 0.025)) if len(boundary) else 0,
            "within_5pp": int(np.sum(boundary <= 0.05)) if len(boundary) else 0,
            "within_7_5pp": int(np.sum(boundary <= 0.075)) if len(boundary) else 0,
        },
        "single_book_deletion": book_delete,
        "lambda_0_25_0_50_0_75_all_nonnegative": all(lambda_nonnegative.values()),
        "lambda_nonnegative_detail": lambda_nonnegative,
        "post_lock_timestamp_leakage_detected": False,
        "completed_2026_season_outcomes_loaded": 0,
    }


def disposition(primary_pair: dict[str, Any], primary_score: dict[str, Any], fst_score: dict[str, Any],
                level_pair: dict[str, Any], adv: dict[str, Any]) -> dict[str, Any]:
    net = primary_pair["candidate_only_correct"] - primary_pair["benchmark_only_correct"]
    ci_low = primary_pair["week_block_accuracy"]["ci95_low"]
    loo_weeks_nonnegative = all(x["net_correct_vs_fst"] >= 0 for x in adv["leave_one_week_out"])
    team_share = adv["max_positive_team_contribution_share_of_net_gain"]
    prob_ok = (
        primary_pair["brier_delta"] <= BRIER_ALERT_DELTA
        and primary_score["brier"] < 0.25
        and primary_score["log_loss"] < math.log(2.0)
    )
    conditions = {
        "accuracy_delta_positive": primary_pair["accuracy_delta"] > 0,
        "at_least_10_switches": primary_pair["switches"] >= 10,
        "candidate_only_gt_fst_only": primary_pair["candidate_only_correct"] > primary_pair["benchmark_only_correct"],
        "week_block_ci_lower_nonnegative": ci_low is not None and ci_low >= 0.0,
        "no_single_game_supplies_entire_gain": not adv["single_game_deletion"]["single_game_supplies_entire_gain"],
        "leave_one_week_never_negative": loo_weeks_nonnegative,
        "no_single_team_over_half_net_gain": bool(team_share is not None and team_share <= 0.5),
        "lambda_025_05_075_nonnegative": adv["lambda_0_25_0_50_0_75_all_nonnegative"],
        "level_only_does_not_reproduce_net_gain": (
            (primary_pair["candidate_only_correct"] - primary_pair["benchmark_only_correct"])
            > (level_pair["candidate_only_correct"] - level_pair["benchmark_only_correct"])
        ),
        "probability_quality_not_pathological": prob_ok,
    }
    if primary_pair["accuracy_delta"] < 0:
        label = "REJECTED"
    elif (
        primary_pair["switches"] >= 10
        and primary_pair["switch_win_rate"] is not None
        and primary_pair["switch_win_rate"] <= 0.5
        and not (primary_score["brier"] < fst_score["brier"] and primary_score["log_loss"] < fst_score["log_loss"])
    ):
        label = "REJECTED"
    elif all(conditions.values()):
        label = "PROMISING / REQUIRES PROSPECTIVE VALIDATION"
    else:
        label = "INCONCLUSIVE"
    return {"label": label, "success_conditions": conditions, "net_correct_gain": net}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", type=Path, required=True)
    ap.add_argument("--training-frame", type=Path, required=True)
    ap.add_argument("--candidate2-scored", type=Path, required=True)
    ap.add_argument("--output-dir", type=Path, required=True)
    args = ap.parse_args()

    outdir = args.output_dir
    outdir.mkdir(parents=True, exist_ok=True)

    fst = load_fst(args.training_frame)
    obs = load_market_observations(args.db, set(fst["game_id"]))
    final_market = build_final_market(obs)

    robustness_rows = []
    primary_frame = None
    primary_pairs = None
    for lock_lo, lock_hi in LOCK_WINDOWS:
        features, pairs = build_path_features(obs, lock_lo, lock_hi)
        base = fst.merge(features, on="game_id", how="left")
        base["path_qualified"] = base["path_qualified"].fillna(False)
        for lam in ROBUSTNESS_LAMBDAS:
            prob = apply_candidate(base, lam)
            cmp = paired(prob, base["fst_prob"], base["home_win"], base["week"])
            robustness_rows.append({
                "lock_lo_min": lock_lo,
                "lock_hi_min": lock_hi,
                "lambda": lam,
                "path_qualified_games": int(base["path_qualified"].sum()),
                "fail_closed_games": int((~base["path_qualified"]).sum()),
                **{k: cmp[k] for k in (
                    "candidate_correct", "benchmark_correct", "candidate_accuracy",
                    "benchmark_accuracy", "accuracy_delta", "accuracy_delta_pp",
                    "switches", "candidate_only_correct", "benchmark_only_correct",
                    "switch_win_rate",
                )},
            })
            if (lock_lo, lock_hi) == PRIMARY_LOCK and math.isclose(lam, PRIMARY_LAMBDA):
                base["candidate3_prob"] = prob
                primary_frame = base.copy()
                primary_pairs = pairs.copy()

    if primary_frame is None or primary_pairs is None:
        raise RuntimeError("primary Candidate 3 cell was not built")

    robustness = pd.DataFrame(robustness_rows)
    pf = primary_frame.merge(final_market, on="game_id", how="left")
    y = pf["home_win"]

    fst_score = score_vector("F-ST-01-FROZEN-2026", pf["fst_prob"], y)
    c3_score = score_vector(CANDIDATE_ID, pf["candidate3_prob"], y)
    primary_pair = paired(pf["candidate3_prob"], pf["fst_prob"], y, pf["week"])

    eligible = pf["path_qualified"].fillna(False)
    eligible_frame = pf.loc[eligible].copy()
    if eligible_frame.empty:
        raise RuntimeError("no qualified Candidate 3 path rows")

    external_controls = {
        "early_market_complete_case": score_vector("EARLY-MARKET-CONSENSUS", eligible_frame["p_early"], eligible_frame["home_win"]),
        "lock_market_complete_case": score_vector("LOCK-MARKET-CONSENSUS", eligible_frame["p_lock"], eligible_frame["home_win"]),
        "final_market_complete_case_later_info": score_vector("LATEST-PREGAME-MARKET-LATER-INFO", eligible_frame["p_final_market"], eligible_frame["home_win"]),
        "fst_on_path_eligible_rows": score_vector("F-ST-PATH-ELIGIBLE", eligible_frame["fst_prob"], eligible_frame["home_win"]),
    }

    pf["level_only_prob"] = pf["fst_prob"]
    lock_valid = pf["path_qualified"].fillna(False)
    pf.loc[lock_valid, "level_only_prob"] = expit(
        logit(pf.loc[lock_valid, "fst_prob"].to_numpy(float))
        + PRIMARY_LAMBDA * (
            logit(pf.loc[lock_valid, "p_lock"].to_numpy(float))
            - logit(pf.loc[lock_valid, "fst_market_prob"].to_numpy(float))
        )
    )
    level_score = score_vector("LEVEL-ONLY-CONTROL-V1", pf["level_only_prob"], y)
    level_pair = paired(pf["level_only_prob"], pf["fst_prob"], y, pf["week"])

    trend_prob = expit(
        logit(eligible_frame["p_lock"].to_numpy(float))
        + PRIMARY_LAMBDA * eligible_frame["path_delta_logit"].to_numpy(float)
    )
    external_controls["market_trend_complete_case"] = score_vector(
        "MARKET-TREND-CONTROL-V1", pd.Series(trend_prob), eligible_frame["home_win"].reset_index(drop=True)
    )
    external_controls["level_only_all_rows_fail_closed"] = level_score

    c2 = pd.read_csv(args.candidate2_scored)
    c2["season"] = pd.to_numeric(c2["season"], errors="coerce")
    c2 = c2[c2["season"].eq(2025)].copy()
    frozen_controls = metrics_for_controls(pf, c2)

    adv = adversarial(pf, primary_pairs, robustness)
    disp = disposition(primary_pair, c3_score, fst_score, level_pair, adv)

    # Switch ledger.
    fst_pick = (pf["fst_prob"] >= 0.5).astype(int)
    c3_pick = (pf["candidate3_prob"] >= 0.5).astype(int)
    switches = pf.loc[fst_pick.ne(c3_pick), [
        "game_id", "week", "away_abbr", "home_abbr", "home_win",
        "fst_prob", "candidate3_prob", "path_delta_logit", "common_books",
        "p_early", "p_lock",
    ]].copy()
    switches["fst_pick_home"] = fst_pick.loc[switches.index].astype(int)
    switches["candidate3_pick_home"] = c3_pick.loc[switches.index].astype(int)
    switches["candidate3_correct"] = switches["candidate3_pick_home"].eq(switches["home_win"]).astype(int)
    switches["fst_correct"] = switches["fst_pick_home"].eq(switches["home_win"]).astype(int)

    config = {
        "candidate_id": CANDIDATE_ID,
        "preregistration_sha": PREREG_SHA,
        "primary_lambda": PRIMARY_LAMBDA,
        "robustness_lambdas": list(ROBUSTNESS_LAMBDAS),
        "early_band_min_to_kickoff": [EARLY_LO_MIN, EARLY_HI_MIN],
        "primary_lock_band_min_to_kickoff": list(PRIMARY_LOCK),
        "lock_window_grid": [list(x) for x in LOCK_WINDOWS],
        "min_common_books": MIN_COMMON_BOOKS,
        "devig": "proportional_two_outcome",
        "path_statistic": "median_same_book_logit_change",
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
    }
    config_digest = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()

    result = {
        "candidate_id": CANDIDATE_ID,
        "status": "canonical_historical_evaluation",
        "preregistration_sha": PREREG_SHA,
        "execution_sha": os.getenv("GITHUB_SHA"),
        "config": config,
        "config_digest": config_digest,
        "market_archive_sha256": sha256(args.db),
        "sample": {
            "season": 2025,
            "games": int(len(pf)),
            "path_qualified_games": int(pf["path_qualified"].sum()),
            "fail_closed_games": int((~pf["path_qualified"]).sum()),
            "coverage": float(pf["path_qualified"].mean()),
            "prediction_horizon": "EARLY T-2160..T-1440 to LOCK T-360..T-120; not exact T-120",
        },
        "fst": fst_score,
        "candidate3": c3_score,
        "primary_pair": primary_pair,
        "controls": {
            "external_market": external_controls,
            "frozen_previous_candidates": frozen_controls,
            "level_only_pair_vs_fst": level_pair,
        },
        "adversarial": adv,
        "disposition": disp,
        "incremental_information": {
            "candidate3_net_correct_vs_fst": int(primary_pair["candidate_only_correct"] - primary_pair["benchmark_only_correct"]),
            "level_only_net_correct_vs_fst": int(level_pair["candidate_only_correct"] - level_pair["benchmark_only_correct"]),
            "candidate3_exceeds_level_only_net_correct": bool(
                (primary_pair["candidate_only_correct"] - primary_pair["benchmark_only_correct"])
                > (level_pair["candidate_only_correct"] - level_pair["benchmark_only_correct"])
            ),
            "interpretation_rule": "Path is not considered independent incremental winner information if level-only control reproduces or exceeds the Candidate 3 net winner gain.",
        },
        "leakage_assessment": {
            "market_rows_post_kickoff_used": 0,
            "lock_rows_later_than_T120_used": 0,
            "completed_2026_season_outcomes_loaded": 0,
            "post_prereg_candidate_retuning": False,
            "production_changed": False,
        },
        "promotion_authorized": False,
    }

    # Write evidence.
    (outdir / "evaluation.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    robustness.to_csv(outdir / "robustness_grid.csv", index=False)
    switches.to_csv(outdir / "switches.csv", index=False)
    pf[[
        "game_id", "week", "away_abbr", "home_abbr", "home_win", "fst_prob",
        "fst_market_prob", "path_qualified", "common_books", "path_delta_logit",
        "p_early", "p_lock", "candidate3_prob", "level_only_prob", "p_final_market",
    ]].to_csv(outdir / "scored_games.csv", index=False)
    pd.DataFrame(adv["leave_one_week_out"]).to_csv(outdir / "leave_one_week_out.csv", index=False)
    pd.DataFrame(adv["leave_one_team_out"]).to_csv(outdir / "leave_one_team_out.csv", index=False)
    pd.DataFrame(adv["single_book_deletion"]).to_csv(outdir / "single_book_deletion.csv", index=False)

    receipt = {
        "candidate_id": CANDIDATE_ID,
        "preregistration_sha": PREREG_SHA,
        "execution_sha": os.getenv("GITHUB_SHA"),
        "config_digest": config_digest,
        "market_archive_sha256": sha256(args.db),
        "games": int(len(pf)),
        "path_qualified_games": int(pf["path_qualified"].sum()),
        "fst_correct": fst_score["correct"],
        "candidate_correct": c3_score["correct"],
        "accuracy_delta_pp": primary_pair["accuracy_delta_pp"],
        "switches": primary_pair["switches"],
        "candidate_only_correct": primary_pair["candidate_only_correct"],
        "fst_only_correct": primary_pair["benchmark_only_correct"],
        "brier": c3_score["brier"],
        "fst_brier": fst_score["brier"],
        "log_loss": c3_score["log_loss"],
        "fst_log_loss": fst_score["log_loss"],
        "disposition": disp["label"],
        "production_changed": False,
        "completed_2026_season_outcomes_used": 0,
    }
    (outdir / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
