from __future__ import annotations

"""Weekly error audit and shrinkage calibration for adaptive LevLine research.

The calibration candidate fits only a single logit intercept from strictly prior
forecast weeks with an L2 prior centered on zero.  A pick-preserving projection is
reported separately so probability calibration can be studied without silently
changing the winner decision.
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.challenger_stacking import build_chronological_logit_stack

SOURCE = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
EPS = 1e-6
L2_PENALTY = 25.0
CANDIDATE_ID = "ADAPTIVE-CALIBRATION-INTERCEPT-V1"


def _logit(values) -> np.ndarray:
    p = np.clip(np.asarray(values, dtype=float), EPS, 1.0 - EPS)
    return np.log(p / (1.0 - p))


def _sigmoid(values) -> np.ndarray:
    x = np.asarray(values, dtype=float)
    return 1.0 / (1.0 + np.exp(-x))


def _parse_game_id(game_id: str) -> tuple[int, int]:
    parts = str(game_id).split("_")
    if len(parts) != 4:
        raise ValueError(f"unexpected game id: {game_id}")
    return int(parts[0]), int(parts[1])


def load_incumbent_frame(path: str | Path = SOURCE) -> pd.DataFrame:
    source = pd.read_csv(path)
    stack = build_chronological_logit_stack(source, target_seasons=TARGET_SEASONS)
    frame = stack.predictions.copy()
    frame["game_id"] = source.loc[frame.index, "game_id"].astype(str)
    parsed = frame["game_id"].map(_parse_game_id)
    frame["season"] = [x[0] for x in parsed]
    frame["week"] = [x[1] for x in parsed]
    frame["home_win"] = pd.to_numeric(frame["home_win"], errors="raise").astype(int)
    frame["fst_prob"] = pd.to_numeric(frame["stack_probability"], errors="raise")
    return frame.sort_values(["season", "week", "game_id"], kind="stable").reset_index(drop=True)


def fit_shrunk_intercept(
    probability: pd.Series | np.ndarray,
    outcome: pd.Series | np.ndarray,
    *,
    penalty: float = L2_PENALTY,
    max_iter: int = 50,
) -> float:
    p = np.clip(np.asarray(probability, dtype=float), EPS, 1.0 - EPS)
    y = np.asarray(outcome, dtype=float)
    if len(p) == 0:
        return 0.0
    if len(p) != len(y):
        raise ValueError("probability/outcome lengths differ")
    base = _logit(p)
    intercept = 0.0
    for _ in range(max_iter):
        q = _sigmoid(base + intercept)
        gradient = float(np.sum(y - q) - penalty * intercept)
        hessian = float(-np.sum(q * (1.0 - q)) - penalty)
        if hessian == 0.0:
            break
        step = gradient / hessian
        intercept -= step
        if abs(step) < 1e-10:
            break
    return float(intercept)


def online_calibrate(
    frame: pd.DataFrame,
    *,
    probability_col: str = "fst_prob",
    outcome_col: str = "home_win",
    penalty: float = L2_PENALTY,
) -> pd.DataFrame:
    required = {"season", "week", "game_id", probability_col, outcome_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"online calibration frame missing: {sorted(missing)}")

    work = frame.sort_values(["season", "week", "game_id"], kind="stable").copy()
    outputs = []
    history_parts = []

    for (season, week), current in work.groupby(["season", "week"], sort=True):
        history = pd.concat(history_parts, ignore_index=True) if history_parts else pd.DataFrame()
        if history.empty:
            intercept = 0.0
        else:
            intercept = fit_shrunk_intercept(
                history[probability_col],
                history[outcome_col],
                penalty=penalty,
            )

        part = current.copy()
        raw = pd.to_numeric(part[probability_col], errors="raise").to_numpy(float)
        calibrated = _sigmoid(_logit(raw) + intercept)
        raw_side = raw >= 0.5
        preserving = calibrated.copy()
        preserving[raw_side] = np.maximum(preserving[raw_side], 0.500001)
        preserving[~raw_side] = np.minimum(preserving[~raw_side], 0.499999)

        part["calibration_intercept"] = intercept
        part["calibrated_prob"] = calibrated
        part["pick_preserving_calibrated_prob"] = preserving
        part["calibration_training_games"] = int(len(history))
        part["same_week_outcomes_used_for_calibration"] = False
        outputs.append(part)

        # Only after this week's probabilities are frozen can its outcomes enter history.
        history_parts.append(current.copy())

    return pd.concat(outputs, ignore_index=True)


def build_error_audit(
    frame: pd.DataFrame,
    *,
    incumbent_col: str,
    challenger_col: str,
    outcome_col: str = "home_win",
) -> pd.DataFrame:
    required = {"game_id", "season", "week", incumbent_col, challenger_col, outcome_col}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"error audit missing fields: {sorted(missing)}")
    out = frame.copy()
    y = pd.to_numeric(out[outcome_col], errors="raise").astype(int)
    incumbent = pd.to_numeric(out[incumbent_col], errors="raise").clip(EPS, 1.0 - EPS)
    challenger = pd.to_numeric(out[challenger_col], errors="raise").clip(EPS, 1.0 - EPS)
    out["incumbent_correct"] = incumbent.ge(0.5).astype(int).eq(y)
    out["challenger_correct"] = challenger.ge(0.5).astype(int).eq(y)
    out["switch"] = incumbent.ge(0.5).ne(challenger.ge(0.5))
    out["switch_helped"] = out["switch"] & out["challenger_correct"] & ~out["incumbent_correct"]
    out["switch_hurt"] = out["switch"] & out["incumbent_correct"] & ~out["challenger_correct"]
    out["incumbent_probability_error"] = y - incumbent
    out["challenger_probability_error"] = y - challenger
    out["incumbent_brier_contribution"] = (incumbent - y) ** 2
    out["challenger_brier_contribution"] = (challenger - y) ** 2
    out["incumbent_log_loss_contribution"] = -(y * np.log(incumbent) + (1 - y) * np.log(1 - incumbent))
    out["challenger_log_loss_contribution"] = -(y * np.log(challenger) + (1 - y) * np.log(1 - challenger))
    out["challenger_shift_pp"] = 100.0 * (challenger - incumbent)
    out["incumbent_boundary_distance_pp"] = 100.0 * (incumbent - 0.5).abs()
    return out


def _metrics(probability: pd.Series, y: pd.Series) -> dict:
    p = pd.to_numeric(probability, errors="raise").clip(EPS, 1.0 - EPS)
    target = pd.to_numeric(y, errors="raise").astype(int)
    return {
        "games": int(len(target)),
        "accuracy": float(p.ge(0.5).astype(int).eq(target).mean()),
        "correct": int(p.ge(0.5).astype(int).eq(target).sum()),
        "brier": float(np.mean((p - target) ** 2)),
        "log_loss": float(np.mean(-(target * np.log(p) + (1 - target) * np.log(1 - p)))),
    }


def run(output_dir: str = "research_outputs/adaptive_calibration_intercept_v1") -> dict:
    base = load_incumbent_frame()
    scored = online_calibrate(base)
    audit = build_error_audit(
        scored,
        incumbent_col="fst_prob",
        challenger_col="pick_preserving_calibrated_prob",
    )
    incumbent = _metrics(audit["fst_prob"], audit["home_win"])
    candidate = _metrics(audit["pick_preserving_calibrated_prob"], audit["home_win"])
    report = {
        "candidate_id": CANDIDATE_ID,
        "status": "historical_fixed_candidate_not_promotion_proof",
        "governance": {
            "same_week_outcomes_used": False,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "promotion_authorized": False,
        },
        "algorithm": {
            "type": "single logit intercept recalibration",
            "l2_penalty": L2_PENALTY,
            "prior_center": 0.0,
            "pick_preserving_primary_variant": True,
        },
        "incumbent": incumbent,
        "candidate": candidate,
        "deltas": {
            "accuracy_pp": 100.0 * (candidate["accuracy"] - incumbent["accuracy"]),
            "brier": candidate["brier"] - incumbent["brier"],
            "log_loss": candidate["log_loss"] - incumbent["log_loss"],
        },
        "switches": int(audit["switch"].sum()),
    }
    if incumbent["correct"] != 741:
        raise RuntimeError(f"incumbent reproduction drift: {incumbent['correct']} != 741")
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    audit.to_csv(out / "error_audit.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/adaptive_calibration_intercept_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
