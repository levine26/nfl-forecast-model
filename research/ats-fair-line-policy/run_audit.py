from __future__ import annotations

"""Chronology-clean historical audit of the LevLine fair-line ATS decision rule.

Frozen by research/ats-fair-line-policy/PREREGISTRATION.md before execution.
Research only: no completed-2026 outcomes and no production writes.
"""

import json
import math
from pathlib import Path
import subprocess

import numpy as np
import pandas as pd
from scipy.stats import binomtest, pearsonr, spearmanr

from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data, load_advanced_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import (
    aggregate_team_games,
    add_game_results,
    build_matchup_features,
    core_columns,
)
from nfl_forecast.market import add_vig_free_market_prob
from nfl_forecast.models import fit_weighted_regression

ROOT = Path(__file__).resolve().parent
REPO_ROOT = ROOT.parent.parent
RESULTS = ROOT / "results"
OUTER = (2022, 2023, 2024, 2025)
EDGE_EPS = 1e-12
BOOTSTRAP_N = 10_000
BOOTSTRAP_SEED = 20260925
BREAK_EVEN = 1.1 / 2.1


class AuditError(RuntimeError):
    pass


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return "UNKNOWN"


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def prepare_games(config_path: str = "config/model.yaml") -> tuple[pd.DataFrame, list[str], int]:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    seasons = list(range(start, 2026))
    bundle = load_core_data(seasons, cfg["data"]["cache_dir"])
    advanced_start = int(cfg["data"]["advanced_start_season"])
    bundle = load_advanced_data(bundle, range(advanced_start, 2026))
    elo = build_pregame_elo(
        bundle.schedules,
        initial=cfg["elo"]["initial"],
        k_factor=cfg["elo"]["k_factor"],
        home_advantage=cfg["elo"]["home_advantage"],
        offseason_regression=cfg["elo"]["offseason_regression"],
    )
    team_games = aggregate_team_games(
        bundle.pbp,
        cfg["data"]["neutral_wp_lower"],
        cfg["data"]["neutral_wp_upper"],
    )
    team_games = add_game_results(team_games, bundle.schedules)
    games = build_matchup_features(team_games, bundle.schedules, elo)
    games = add_vig_free_market_prob(games)
    games["season"] = pd.to_numeric(games["season"], errors="coerce")
    if games["season"].dropna().ge(2026).any():
        raise AuditError("2026 rows entered audit feature frame")
    historical = games[games["home_win"].notna() & games["season"].le(2025)].copy()
    if "game_type" in historical.columns:
        historical = historical[historical["game_type"].eq("REG")].copy()
    historical["margin"] = pd.to_numeric(historical["margin"], errors="coerce")
    historical["spread_line"] = pd.to_numeric(historical["spread_line"], errors="coerce")
    features = core_columns(historical)
    if not features:
        raise AuditError("production core feature set is empty")
    return historical, features, int(cfg["model"]["random_state"])


def outer_oof(historical: pd.DataFrame, features: list[str], seed: int, core_start: int) -> pd.DataFrame:
    parts: list[pd.DataFrame] = []
    for season in OUTER:
        train = historical[historical["season"] < season].copy()
        target = historical[historical["season"] == season].copy()
        eligible = np.isfinite(target["margin"].to_numpy(dtype=float)) & np.isfinite(target["spread_line"].to_numpy(dtype=float))
        target = target.loc[eligible].copy()
        if len(train) < 100 or target.empty:
            raise AuditError(f"outer season {season} lacks train/target rows")
        model = fit_weighted_regression(
            train,
            features,
            "margin",
            seed=seed,
            validation_start=max(core_start + 1, season - 4),
            validation_end=season - 1,
        )
        pred = np.asarray(model.predict(target), dtype=float)
        if not np.isfinite(pred).all():
            raise AuditError(f"nonfinite margin OOF prediction in {season}")
        out = pd.DataFrame({
            "game_id": target["game_id"].astype(str).to_numpy(),
            "season": target["season"].astype(int).to_numpy(),
            "week": pd.to_numeric(target["week"], errors="raise").astype(int).to_numpy(),
            "actual_margin": target["margin"].to_numpy(dtype=float),
            "market_margin": target["spread_line"].to_numpy(dtype=float),
            "model_margin": pred,
            "margin_sigma": float(model.residual_std),
            "validation_mae": float(model.validation_mae),
        })
        out["model_edge"] = out["model_margin"] - out["market_margin"]
        out["ats_residual"] = out["actual_margin"] - out["market_margin"]
        out["decision"] = np.where(
            np.isclose(out["model_edge"], 0.0, atol=EDGE_EPS, rtol=0.0),
            "NO_EDGE",
            np.where(out["model_edge"] > 0.0, "HOME", "AWAY"),
        )
        out["ats_outcome"] = np.where(
            np.isclose(out["ats_residual"], 0.0, atol=1e-9, rtol=0.0),
            "PUSH",
            np.where(
                ((out["model_edge"] > 0.0) & (out["ats_residual"] > 0.0))
                | ((out["model_edge"] < 0.0) & (out["ats_residual"] < 0.0)),
                "WIN",
                "LOSS",
            ),
        )
        out.loc[out["decision"].eq("NO_EDGE"), "ats_outcome"] = "NO_EDGE"
        parts.append(out)
    result = pd.concat(parts, ignore_index=True).sort_values(["season", "week", "game_id"]).reset_index(drop=True)
    if result["game_id"].duplicated().any():
        raise AuditError("duplicate outer OOF game_id")
    if set(result["season"].unique()) != set(OUTER):
        raise AuditError("outer OOF season identity drift")
    return result


def ats_summary(frame: pd.DataFrame) -> dict:
    d = frame[frame["decision"] != "NO_EDGE"].copy()
    wins = int((d["ats_outcome"] == "WIN").sum())
    losses = int((d["ats_outcome"] == "LOSS").sum())
    pushes = int((d["ats_outcome"] == "PUSH").sum())
    no_edge = int((frame["decision"] == "NO_EDGE").sum())
    n = wins + losses
    hit = None if n == 0 else wins / n
    ci = None
    if n:
        interval = binomtest(wins, n).proportion_ci(confidence_level=0.95, method="exact")
        ci = [float(interval.low), float(interval.high)]
    net = float(wins - 1.1 * losses)
    risk = float(1.1 * n)
    return {
        "rows": int(len(frame)),
        "decisions": int(len(d)),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "no_edge": no_edge,
        "nonpush_n": n,
        "hit_rate_ex_push": hit,
        "exact_95_ci": ci,
        "REFERENCE_MINUS110": {
            "net_units": net,
            "risk_units": risk,
            "roi_on_risk": None if risk == 0 else net / risk,
            "actual_quoted_price_result": False,
        },
    }


def fixed_subset(frame: pd.DataFrame, fraction: float) -> pd.DataFrame:
    d = frame[frame["decision"] != "NO_EDGE"].copy()
    n = max(1, int(math.ceil(len(d) * float(fraction))))
    return d.assign(abs_edge=d["model_edge"].abs()).sort_values(["abs_edge", "game_id"], ascending=[False, True]).head(n)


def bootstrap(frame: pd.DataFrame) -> dict:
    d = frame[frame["decision"] != "NO_EDGE"].copy()
    d["win"] = (d["ats_outcome"] == "WIN").astype(int)
    d["loss"] = (d["ats_outcome"] == "LOSS").astype(int)
    blocks = d.groupby(["season", "week"], as_index=False).agg(wins=("win", "sum"), losses=("loss", "sum"))
    by_season = {int(s): g.reset_index(drop=True) for s, g in blocks.groupby("season")}
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    vals = np.full(BOOTSTRAP_N, np.nan, dtype=float)
    for i in range(BOOTSTRAP_N):
        w = l = 0
        for season in OUTER:
            g = by_season[season]
            idx = rng.integers(0, len(g), size=len(g))
            sample = g.iloc[idx]
            w += int(sample["wins"].sum())
            l += int(sample["losses"].sum())
        if w + l:
            vals[i] = w / (w + l)
    vals = vals[np.isfinite(vals)]
    return {
        "resamples": int(len(vals)),
        "seed": BOOTSTRAP_SEED,
        "hit_rate_95_ci": [float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))],
        "probability_hit_rate_gt_0_50": float(np.mean(vals > 0.50)),
        "probability_hit_rate_gt_reference_minus110_break_even": float(np.mean(vals > BREAK_EVEN)),
    }


def margin_diagnostics(frame: pd.DataFrame) -> dict:
    model_error = frame["actual_margin"] - frame["model_margin"]
    market_error = frame["actual_margin"] - frame["market_margin"]
    edge = frame["model_edge"].to_numpy(dtype=float)
    residual = frame["ats_residual"].to_numpy(dtype=float)
    pear = pearsonr(edge, residual)
    spear = spearmanr(edge, residual)
    return {
        "levline_margin_mae": float(np.mean(np.abs(model_error))),
        "market_spread_center_mae": float(np.mean(np.abs(market_error))),
        "levline_minus_market_mae": float(np.mean(np.abs(model_error)) - np.mean(np.abs(market_error))),
        "mean_absolute_model_edge": float(np.mean(np.abs(edge))),
        "median_absolute_model_edge": float(np.median(np.abs(edge))),
        "pearson_edge_vs_realized_ats_residual": {"r": float(pear.statistic), "pvalue": float(pear.pvalue)},
        "spearman_edge_vs_realized_ats_residual": {"rho": float(spear.statistic), "pvalue": float(spear.pvalue)},
    }


def execute() -> dict:
    cfg = load_config("config/model.yaml")
    core_start = int(cfg["data"]["core_start_season"])
    historical, features, seed = prepare_games()
    oof = outer_oof(historical, features, seed, core_start)
    RESULTS.mkdir(parents=True, exist_ok=True)
    oof.to_csv(RESULTS / "OOF_FAIR_LINE_POLICY.csv", index=False, float_format="%.17g")

    aggregate = ats_summary(oof)
    seasons = {str(s): ats_summary(oof[oof["season"] == s]) for s in OUTER}
    top20 = ats_summary(fixed_subset(oof, 0.20))
    top10 = ats_summary(fixed_subset(oof, 0.10))
    boot = bootstrap(oof)
    diagnostics = margin_diagnostics(oof)
    season_nonadverse = sum(
        seasons[str(s)]["hit_rate_ex_push"] is not None and seasons[str(s)]["hit_rate_ex_push"] >= 0.50
        for s in OUTER
    )
    gates = {
        "aggregate_hit_rate_gt_reference_minus110_break_even": aggregate["hit_rate_ex_push"] is not None and aggregate["hit_rate_ex_push"] > BREAK_EVEN,
        "bootstrap_probability_gt_0_50_at_least_0_80": boot["probability_hit_rate_gt_0_50"] >= 0.80,
        "at_least_3_of_4_seasons_at_or_above_0_50": season_nonadverse >= 3,
        "completed_2026_outcomes_used": 0,
        "chronology": "PASS",
    }
    classification = "HISTORICALLY_INTERESTING" if all(
        [gates["aggregate_hit_rate_gt_reference_minus110_break_even"], gates["bootstrap_probability_gt_0_50_at_least_0_80"], gates["at_least_3_of_4_seasons_at_or_above_0_50"]]
    ) else "NOT_ESTABLISHED"
    receipt = {
        "policy_id": "ATS-FAIR-LINE-POLICY-V1",
        "git_sha": git_sha(),
        "outer_seasons": list(OUTER),
        "completed_2026_outcomes_used": 0,
        "production_changed": False,
        "feature_count": int(len(features)),
        "oof_rows": int(len(oof)),
        "decision_rule": "sign(model_margin - market_margin)",
        "edge_threshold": 0.0,
        "aggregate": aggregate,
        "per_season": seasons,
        "top_20_percent_abs_edge_diagnostic": top20,
        "top_10_percent_abs_edge_diagnostic": top10,
        "bootstrap": boot,
        "margin_diagnostics": diagnostics,
        "reference_minus110_break_even": BREAK_EVEN,
        "gates": gates,
        "classification": classification,
    }
    dump_json(RESULTS / "FINAL_RECEIPT.json", receipt)
    print(json.dumps({
        "classification": classification,
        "hit_rate_ex_push": aggregate["hit_rate_ex_push"],
        "wins": aggregate["wins"],
        "losses": aggregate["losses"],
        "pushes": aggregate["pushes"],
        "bootstrap_p_gt_50": boot["probability_hit_rate_gt_0_50"],
        "levline_minus_market_mae": diagnostics["levline_minus_market_mae"],
    }, indent=2, sort_keys=True))
    return receipt


if __name__ == "__main__":
    execute()
