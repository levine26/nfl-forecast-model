from __future__ import annotations

"""Research-only market-anchored coherent margin/total distribution.

PHASE3-JOINT-DIST-001 is pre-registered in research/phase3_joint_distribution_prereg.json.
No production module imports this file. Historical fitting is season-forward and refuses
2026+ outcomes.
"""

from dataclasses import asdict, dataclass
from math import pi, sqrt
from typing import Sequence

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

TARGET_SEASONS = (2022, 2023, 2024, 2025)
ALPHA_MARGIN = 100.0
ALPHA_TOTAL = 100.0
MARGIN_CAP = 3.0
TOTAL_CAP = 4.0
EPS = 1e-6


@dataclass(frozen=True)
class ContinuousBootstrap:
    metric: str
    candidate: str
    reference: str
    games: int
    blocks: int
    observed_delta: float
    ci_lower: float
    ci_upper: float
    probability_better: float
    samples: int


def _ridge(alpha: float) -> Pipeline:
    return Pipeline(
        [
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            ("ridge", Ridge(alpha=float(alpha))),
        ]
    )


def _validate_historical(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "season", "home_win", "margin", "game_total", "spread_line", "total_line",
        "market_home_prob",
    }
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"joint-distribution frame missing fields: {sorted(missing)}")
    out = frame.copy()
    for col in ("season", "home_win", "margin", "game_total", "spread_line", "total_line", "market_home_prob"):
        out[col] = pd.to_numeric(out[col], errors="coerce")
    if out.loc[out.margin.notna() | out.game_total.notna(), "season"].ge(2026).any():
        raise ValueError("Phase 3 historical fitting refuses 2026-or-later outcomes")
    return out


def normal_crps(y: np.ndarray, mean: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    y = np.asarray(y, dtype=float)
    mean = np.asarray(mean, dtype=float)
    sigma = np.clip(np.asarray(sigma, dtype=float), 1e-6, None)
    z = (y - mean) / sigma
    return sigma * (z * (2.0 * norm.cdf(z) - 1.0) + 2.0 * norm.pdf(z) - 1.0 / sqrt(pi))


def season_forward_joint_distribution(
    frame: pd.DataFrame,
    feature_cols: Sequence[str],
    *,
    target_seasons: Sequence[int] = TARGET_SEASONS,
    alpha_margin: float = ALPHA_MARGIN,
    alpha_total: float = ALPHA_TOTAL,
    margin_cap: float = MARGIN_CAP,
    total_cap: float = TOTAL_CAP,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = _validate_historical(frame)
    features = list(feature_cols)
    missing = [c for c in features if c not in work.columns]
    if missing:
        raise ValueError(f"joint-distribution features missing: {missing[:10]}")

    predictions: list[pd.DataFrame] = []
    diagnostics: list[dict] = []
    for season in [int(x) for x in target_seasons]:
        train = work[
            work.season.lt(season)
            & work.margin.notna()
            & work.game_total.notna()
            & work.spread_line.notna()
            & work.total_line.notna()
        ].copy()
        test = work[
            work.season.eq(season)
            & work.margin.notna()
            & work.game_total.notna()
            & work.spread_line.notna()
            & work.total_line.notna()
            & work.market_home_prob.between(EPS, 1.0 - EPS)
        ].copy()
        if test.empty:
            continue
        if len(train) < 300:
            raise ValueError(f"Insufficient pre-{season} joint-distribution history: {len(train)}")

        margin_resid = train.margin.to_numpy(float) - train.spread_line.to_numpy(float)
        total_resid = train.game_total.to_numpy(float) - train.total_line.to_numpy(float)
        margin_model = _ridge(alpha_margin)
        total_model = _ridge(alpha_total)
        margin_model.fit(train[features], margin_resid)
        total_model.fit(train[features], total_resid)
        raw_margin_correction = margin_model.predict(test[features])
        raw_total_correction = total_model.predict(test[features])
        margin_correction = np.clip(raw_margin_correction, -float(margin_cap), float(margin_cap))
        total_correction = np.clip(raw_total_correction, -float(total_cap), float(total_cap))

        margin_sigma = max(float(np.std(margin_resid, ddof=1)), 1.0)
        total_sigma = max(float(np.std(total_resid, ddof=1)), 1.0)
        rho = float(np.corrcoef(margin_resid, total_resid)[0, 1])
        if not np.isfinite(rho):
            rho = 0.0
        rho = float(np.clip(rho, -0.95, 0.95))

        margin_mean = test.spread_line.to_numpy(float) + margin_correction
        total_mean = test.total_line.to_numpy(float) + total_correction
        probability = np.clip(norm.cdf(margin_mean / margin_sigma), EPS, 1.0 - EPS)
        market_spread_probability = np.clip(norm.cdf(test.spread_line.to_numpy(float) / margin_sigma), EPS, 1.0 - EPS)
        home_score_mean = (total_mean + margin_mean) / 2.0
        away_score_mean = (total_mean - margin_mean) / 2.0
        z80 = float(norm.ppf(0.9))

        keep = [
            c for c in (
                "game_id", "season", "week", "gameday", "away_team", "home_team",
                "home_win", "margin", "game_total", "spread_line", "total_line", "market_home_prob",
            ) if c in test.columns
        ]
        part = test[keep].copy()
        part["candidate_margin_mean"] = margin_mean
        part["candidate_total_mean"] = total_mean
        part["candidate_home_score_mean"] = home_score_mean
        part["candidate_away_score_mean"] = away_score_mean
        part["candidate_home_win_prob"] = probability
        part["market_spread_home_win_prob"] = market_spread_probability
        part["margin_sigma"] = margin_sigma
        part["total_sigma"] = total_sigma
        part["margin_total_rho"] = rho
        part["margin_correction"] = margin_correction
        part["total_correction"] = total_correction
        part["margin_correction_raw"] = raw_margin_correction
        part["total_correction_raw"] = raw_total_correction
        part["margin_cap_hit"] = np.abs(raw_margin_correction) > float(margin_cap)
        part["total_cap_hit"] = np.abs(raw_total_correction) > float(total_cap)
        part["candidate_margin_abs_error"] = np.abs(part.margin - part.candidate_margin_mean)
        part["market_margin_abs_error"] = np.abs(part.margin - part.spread_line)
        part["candidate_total_abs_error"] = np.abs(part.game_total - part.candidate_total_mean)
        part["market_total_abs_error"] = np.abs(part.game_total - part.total_line)
        part["candidate_margin_sq_error"] = (part.margin - part.candidate_margin_mean) ** 2
        part["market_margin_sq_error"] = (part.margin - part.spread_line) ** 2
        part["candidate_total_sq_error"] = (part.game_total - part.candidate_total_mean) ** 2
        part["market_total_sq_error"] = (part.game_total - part.total_line) ** 2
        part["candidate_margin_crps"] = normal_crps(part.margin, part.candidate_margin_mean, margin_sigma)
        part["market_margin_crps"] = normal_crps(part.margin, part.spread_line, margin_sigma)
        part["candidate_total_crps"] = normal_crps(part.game_total, part.candidate_total_mean, total_sigma)
        part["market_total_crps"] = normal_crps(part.game_total, part.total_line, total_sigma)
        part["margin_low_80"] = part.candidate_margin_mean - z80 * margin_sigma
        part["margin_high_80"] = part.candidate_margin_mean + z80 * margin_sigma
        part["total_low_80"] = part.candidate_total_mean - z80 * total_sigma
        part["total_high_80"] = part.candidate_total_mean + z80 * total_sigma
        part["margin_covered_80"] = part.margin.between(part.margin_low_80, part.margin_high_80)
        part["total_covered_80"] = part.game_total.between(part.total_low_80, part.total_high_80)
        # Algebraic identities for downstream executable coherence checks.
        part["score_margin_identity_error"] = (
            (part.candidate_home_score_mean - part.candidate_away_score_mean) - part.candidate_margin_mean
        ).abs()
        part["score_total_identity_error"] = (
            (part.candidate_home_score_mean + part.candidate_away_score_mean) - part.candidate_total_mean
        ).abs()
        part["probability_identity_error"] = (
            part.candidate_home_win_prob - norm.cdf(part.candidate_margin_mean / part.margin_sigma)
        ).abs()
        predictions.append(part)
        diagnostics.append(
            {
                "season": season,
                "training_games": int(len(train)),
                "test_games": int(len(test)),
                "alpha_margin": float(alpha_margin),
                "alpha_total": float(alpha_total),
                "margin_cap": float(margin_cap),
                "total_cap": float(total_cap),
                "margin_sigma": margin_sigma,
                "total_sigma": total_sigma,
                "margin_total_rho": rho,
                "margin_cap_rate": float(np.mean(np.abs(raw_margin_correction) > float(margin_cap))),
                "total_cap_rate": float(np.mean(np.abs(raw_total_correction) > float(total_cap))),
            }
        )
    if not predictions:
        raise ValueError("No Phase 3 target predictions generated")
    return pd.concat(predictions).sort_index(), pd.DataFrame(diagnostics)


def summarize_joint_distribution(predictions: pd.DataFrame) -> dict[str, float]:
    p = predictions.copy()
    y = p.home_win.to_numpy(int)
    candidate_prob = np.clip(p.candidate_home_win_prob.to_numpy(float), EPS, 1.0 - EPS)
    market_prob = np.clip(p.market_home_prob.to_numpy(float), EPS, 1.0 - EPS)
    candidate_log_loss = -np.mean(y * np.log(candidate_prob) + (1 - y) * np.log(1 - candidate_prob))
    market_log_loss = -np.mean(y * np.log(market_prob) + (1 - y) * np.log(1 - market_prob))
    return {
        "games": int(len(p)),
        "candidate_winner_accuracy": float(np.mean((candidate_prob >= 0.5) == y)),
        "market_winner_accuracy": float(np.mean((market_prob >= 0.5) == y)),
        "candidate_brier": float(np.mean((candidate_prob - y) ** 2)),
        "market_brier": float(np.mean((market_prob - y) ** 2)),
        "candidate_minus_market_brier": float(np.mean((candidate_prob - y) ** 2) - np.mean((market_prob - y) ** 2)),
        "candidate_log_loss": float(candidate_log_loss),
        "market_log_loss": float(market_log_loss),
        "candidate_minus_market_log_loss": float(candidate_log_loss - market_log_loss),
        "candidate_margin_mae": float(p.candidate_margin_abs_error.mean()),
        "market_margin_mae": float(p.market_margin_abs_error.mean()),
        "candidate_minus_market_margin_mae": float((p.candidate_margin_abs_error - p.market_margin_abs_error).mean()),
        "candidate_total_mae": float(p.candidate_total_abs_error.mean()),
        "market_total_mae": float(p.market_total_abs_error.mean()),
        "candidate_minus_market_total_mae": float((p.candidate_total_abs_error - p.market_total_abs_error).mean()),
        "candidate_margin_rmse": float(np.sqrt(p.candidate_margin_sq_error.mean())),
        "market_margin_rmse": float(np.sqrt(p.market_margin_sq_error.mean())),
        "candidate_total_rmse": float(np.sqrt(p.candidate_total_sq_error.mean())),
        "market_total_rmse": float(np.sqrt(p.market_total_sq_error.mean())),
        "candidate_margin_crps": float(p.candidate_margin_crps.mean()),
        "market_margin_crps": float(p.market_margin_crps.mean()),
        "candidate_total_crps": float(p.candidate_total_crps.mean()),
        "market_total_crps": float(p.market_total_crps.mean()),
        "margin_80_coverage": float(p.margin_covered_80.mean()),
        "total_80_coverage": float(p.total_covered_80.mean()),
        "margin_cap_rate": float(p.margin_cap_hit.mean()),
        "total_cap_rate": float(p.total_cap_hit.mean()),
        "coherence_failures": int(
            ((p.score_margin_identity_error > 1e-10) | (p.score_total_identity_error > 1e-10) | (p.probability_identity_error > 1e-12)).sum()
        ),
    }


def blocked_continuous_bootstrap(
    predictions: pd.DataFrame,
    candidate_loss_col: str,
    reference_loss_col: str,
    *,
    metric: str,
    samples: int = 2000,
    seed: int = 26,
) -> ContinuousBootstrap:
    data = predictions.dropna(subset=[candidate_loss_col, reference_loss_col, "season", "week"]).copy()
    if data.empty:
        raise ValueError("No paired continuous rows")
    data["_delta"] = pd.to_numeric(data[candidate_loss_col], errors="coerce") - pd.to_numeric(data[reference_loss_col], errors="coerce")
    data["_block"] = data.season.astype(str) + "|" + data.week.astype(str)
    blocks = list(data._block.unique())
    values = {b: data.loc[data._block.eq(b), "_delta"].to_numpy(float) for b in blocks}
    observed = float(data._delta.mean())
    rng = np.random.default_rng(seed)
    draws = np.empty(int(samples), dtype=float)
    for i in range(int(samples)):
        chosen = rng.choice(blocks, size=len(blocks), replace=True)
        draws[i] = float(np.mean(np.concatenate([values[b] for b in chosen])))
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return ContinuousBootstrap(
        metric=metric,
        candidate=candidate_loss_col,
        reference=reference_loss_col,
        games=int(len(data)),
        blocks=int(len(blocks)),
        observed_delta=observed,
        ci_lower=float(lo),
        ci_upper=float(hi),
        probability_better=float(np.mean(draws < 0.0)),
        samples=int(samples),
    )


def result_dict(result: ContinuousBootstrap) -> dict:
    return asdict(result)
