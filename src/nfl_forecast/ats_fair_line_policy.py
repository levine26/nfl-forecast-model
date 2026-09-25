from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.stats import beta, pearsonr, spearmanr

OUTER_SEASONS = (2022, 2023, 2024, 2025)
EDGE_EPSILON = 1e-12
PUSH_EPSILON = 1e-12
BOOTSTRAP_SAMPLES = 10_000
BOOTSTRAP_SEED = 20260925
REFERENCE_BREAK_EVEN = 1.1 / 2.1


@dataclass(frozen=True)
class AtsRecord:
    decisions: int
    wins: int
    losses: int
    pushes: int
    no_edge: int
    hit_rate_ex_push: float
    ci_lower: float
    ci_upper: float
    reference_minus110_net_units: float
    reference_minus110_roi_on_risk: float


def clopper_pearson(wins: int, losses: int, alpha: float = 0.05) -> tuple[float, float]:
    n = int(wins) + int(losses)
    if n <= 0:
        return float("nan"), float("nan")
    lower = 0.0 if wins == 0 else float(beta.ppf(alpha / 2.0, wins, losses + 1))
    upper = 1.0 if losses == 0 else float(beta.ppf(1.0 - alpha / 2.0, wins + 1, losses))
    return lower, upper


def grade_oof(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"season", "week", "margin", "spread_line", "expected_margin"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"fair-line audit frame missing required columns: {missing}")

    out = frame.copy()
    for column in ("season", "week", "margin", "spread_line", "expected_margin"):
        out[column] = pd.to_numeric(out[column], errors="coerce")
    finite = np.isfinite(out[["season", "week", "margin", "spread_line", "expected_margin"]].to_numpy(dtype=float)).all(axis=1)
    out = out.loc[finite].copy()
    if out.empty:
        raise ValueError("fair-line audit has no finite eligible rows")
    if pd.to_numeric(out["season"], errors="coerce").gt(2025).any():
        raise RuntimeError("fair-line audit crossed the completed-2026 firewall")

    out["edge_home"] = out["expected_margin"] - out["spread_line"]
    out["ats_residual"] = out["margin"] - out["spread_line"]
    out["abs_edge"] = out["edge_home"].abs()
    out["decision"] = out["abs_edge"] > EDGE_EPSILON
    out["pick_home"] = np.where(out["decision"], out["edge_home"] > 0.0, pd.NA)
    out["push"] = out["decision"] & out["ats_residual"].abs().le(PUSH_EPSILON)
    out["win"] = out["decision"] & ~out["push"] & (
        ((out["edge_home"] > 0.0) & (out["ats_residual"] > 0.0))
        | ((out["edge_home"] < 0.0) & (out["ats_residual"] < 0.0))
    )
    out["loss"] = out["decision"] & ~out["push"] & ~out["win"]
    return out


def record(frame: pd.DataFrame) -> AtsRecord:
    graded = grade_oof(frame) if "decision" not in frame.columns else frame.copy()
    decisions = int(graded["decision"].sum())
    wins = int(graded["win"].sum())
    losses = int(graded["loss"].sum())
    pushes = int(graded["push"].sum())
    no_edge = int((~graded["decision"]).sum())
    resolved = wins + losses
    hit = float(wins / resolved) if resolved else float("nan")
    lo, hi = clopper_pearson(wins, losses)
    net = float(wins - 1.1 * losses)
    risk = 1.1 * resolved
    roi = float(net / risk) if risk else float("nan")
    return AtsRecord(
        decisions=decisions,
        wins=wins,
        losses=losses,
        pushes=pushes,
        no_edge=no_edge,
        hit_rate_ex_push=hit,
        ci_lower=lo,
        ci_upper=hi,
        reference_minus110_net_units=net,
        reference_minus110_roi_on_risk=roi,
    )


def season_records(graded: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for season in OUTER_SEASONS:
        subset = graded[pd.to_numeric(graded["season"], errors="coerce").eq(season)].copy()
        rec = record(subset)
        rows.append({"season": season, **rec.__dict__})
    return pd.DataFrame(rows)


def selective_records(graded: pd.DataFrame) -> pd.DataFrame:
    decisions = graded[graded["decision"]].copy()
    rows: list[dict] = []
    for label, fraction in (("TOP_20PCT_ABS_EDGE", 0.20), ("TOP_10PCT_ABS_EDGE", 0.10)):
        n = max(1, int(np.ceil(len(decisions) * fraction)))
        subset = decisions.sort_values(["abs_edge", "season", "week"], ascending=[False, True, True], kind="mergesort").head(n)
        rec = record(subset)
        rows.append({
            "slice": label,
            "target_fraction": fraction,
            "rows": int(len(subset)),
            "minimum_abs_edge": float(subset["abs_edge"].min()),
            **rec.__dict__,
        })
    return pd.DataFrame(rows)


def margin_diagnostics(graded: pd.DataFrame) -> dict[str, float | int]:
    actual = graded["margin"].to_numpy(dtype=float)
    market = graded["spread_line"].to_numpy(dtype=float)
    model = graded["expected_margin"].to_numpy(dtype=float)
    edge = graded["edge_home"].to_numpy(dtype=float)
    residual = graded["ats_residual"].to_numpy(dtype=float)
    pearson = pearsonr(edge, residual)
    spearman = spearmanr(edge, residual)
    return {
        "rows": int(len(graded)),
        "levline_margin_mae": float(np.mean(np.abs(actual - model))),
        "market_spread_center_mae": float(np.mean(np.abs(actual - market))),
        "levline_minus_market_mae": float(np.mean(np.abs(actual - model)) - np.mean(np.abs(actual - market))),
        "mean_absolute_model_edge": float(np.mean(np.abs(edge))),
        "median_absolute_model_edge": float(np.median(np.abs(edge))),
        "pearson_edge_vs_ats_residual": float(pearson.statistic),
        "pearson_pvalue": float(pearson.pvalue),
        "spearman_edge_vs_ats_residual": float(spearman.statistic),
        "spearman_pvalue": float(spearman.pvalue),
    }


def bootstrap_hit_rate(graded: pd.DataFrame) -> dict[str, float | int]:
    decisions = graded[graded["decision"]].copy()
    decisions["season"] = pd.to_numeric(decisions["season"], errors="raise").astype(int)
    decisions["week"] = pd.to_numeric(decisions["week"], errors="raise").astype(int)
    seasons = sorted(decisions["season"].unique().tolist())
    if seasons != list(OUTER_SEASONS):
        raise ValueError(f"bootstrap season contract drifted: {seasons}")

    blocks: dict[int, list[pd.DataFrame]] = {}
    for season in seasons:
        sdf = decisions[decisions["season"].eq(season)]
        blocks[season] = [group for _, group in sdf.groupby("week", sort=True)]
        if not blocks[season]:
            raise ValueError(f"season {season} has no week blocks")

    rng = np.random.default_rng(BOOTSTRAP_SEED)
    rates = np.empty(BOOTSTRAP_SAMPLES, dtype=float)
    for draw in range(BOOTSTRAP_SAMPLES):
        wins = 0
        losses = 0
        for season in seasons:
            season_blocks = blocks[season]
            chosen = rng.integers(0, len(season_blocks), size=len(season_blocks))
            for idx in chosen:
                block = season_blocks[int(idx)]
                wins += int(block["win"].sum())
                losses += int(block["loss"].sum())
        rates[draw] = wins / (wins + losses) if wins + losses else np.nan

    rates = rates[np.isfinite(rates)]
    if len(rates) != BOOTSTRAP_SAMPLES:
        raise RuntimeError("bootstrap produced non-finite hit-rate draws")
    return {
        "samples": BOOTSTRAP_SAMPLES,
        "seed": BOOTSTRAP_SEED,
        "block": "season_stratified_week",
        "ci_lower": float(np.quantile(rates, 0.025)),
        "ci_upper": float(np.quantile(rates, 0.975)),
        "probability_hit_rate_gt_50pct": float(np.mean(rates > 0.50)),
        "probability_hit_rate_gt_reference_break_even": float(np.mean(rates > REFERENCE_BREAK_EVEN)),
    }


def classification(aggregate: AtsRecord, seasons: pd.DataFrame, bootstrap: dict[str, float | int]) -> str:
    season_passes = int((pd.to_numeric(seasons["hit_rate_ex_push"], errors="coerce") >= 0.50).sum())
    if (
        aggregate.hit_rate_ex_push > REFERENCE_BREAK_EVEN
        and float(bootstrap["probability_hit_rate_gt_50pct"]) >= 0.80
        and season_passes >= 3
    ):
        return "HISTORICALLY_INTERESTING"
    return "NOT_ESTABLISHED"
