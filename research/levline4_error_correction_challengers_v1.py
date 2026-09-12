from __future__ import annotations

"""Leakage-safe LevLine 4 error-correction challenger audit.

This research-only audit asks a narrow question: when a chronology-clean component-resolved
stack disagrees with the chronology-clean aggregate F-ST benchmark, can predeclared measures
of component consensus, meta-state novelty, or chronological conformal certainty identify a
higher-quality subset of switches?

It is deliberately diagnostic. It does not tune production thresholds, promote a candidate,
or use completed 2026 outcomes.
"""

import argparse
import json
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

BASE_OOF = Path("challenger_outputs/fst/provenance/base_oof_keyed.csv")
TRAINING_KEYED = Path("challenger_outputs/fst/provenance/training_frame_keyed.csv")
TARGET_SEASONS = (2022, 2023, 2024, 2025)
COMPONENTS = ("logistic", "extra_trees", "xgboost", "catboost")
EPS = 1e-6
ALPHA = 0.10


def _logit(values: pd.Series | np.ndarray) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    arr = np.clip(arr, EPS, 1.0 - EPS)
    return np.log(arr / (1.0 - arr))


def _week_from_game_id(game_id: str) -> int:
    try:
        return int(str(game_id).split("_")[1])
    except Exception as exc:
        raise ValueError(f"cannot parse week from game_id={game_id!r}") from exc


def _load_frame() -> pd.DataFrame:
    base = pd.read_csv(BASE_OOF)
    keyed = pd.read_csv(TRAINING_KEYED)
    required_base = {"game_id", "home_win", "season", *COMPONENTS}
    required_keyed = {"game_id", "market_prob", "pure_prob", "home_win", "season"}
    if not required_base.issubset(base.columns):
        raise ValueError(f"base OOF missing columns: {sorted(required_base - set(base.columns))}")
    if not required_keyed.issubset(keyed.columns):
        raise ValueError(f"training keyed missing columns: {sorted(required_keyed - set(keyed.columns))}")

    frame = base.merge(
        keyed[["game_id", "market_prob", "pure_prob", "home_win", "season"]],
        on="game_id",
        how="inner",
        suffixes=("_base", "_keyed"),
        validate="one_to_one",
    )
    if not (frame["home_win_base"].astype(int) == frame["home_win_keyed"].astype(int)).all():
        raise ValueError("home_win mismatch across provenance frames")
    if not (frame["season_base"].astype(int) == frame["season_keyed"].astype(int)).all():
        raise ValueError("season mismatch across provenance frames")

    frame["home_win"] = frame["home_win_base"].astype(int)
    frame["season"] = frame["season_base"].astype(int)
    frame["week"] = frame["game_id"].map(_week_from_game_id)
    frame = frame.drop(columns=["home_win_base", "home_win_keyed", "season_base", "season_keyed"])
    return frame.sort_values(["season", "week", "game_id"]).reset_index(drop=True)


def _feature_matrix(frame: pd.DataFrame, kind: str) -> np.ndarray:
    if kind == "component":
        cols = ["market_prob", *COMPONENTS]
    elif kind == "fst":
        cols = ["market_prob", "pure_prob"]
    else:
        raise ValueError(kind)
    return np.column_stack([_logit(frame[col]) for col in cols])


def _fit_predict(train: pd.DataFrame, test: pd.DataFrame, kind: str) -> tuple[np.ndarray, LogisticRegression]:
    model = LogisticRegression(C=1.0, solver="lbfgs", max_iter=2000)
    model.fit(_feature_matrix(train, kind), train["home_win"].astype(int).to_numpy())
    prob = model.predict_proba(_feature_matrix(test, kind))[:, 1]
    return prob, model


def _novelty(train: pd.DataFrame, test: pd.DataFrame) -> tuple[np.ndarray, float, float]:
    """Training-defined standardized Euclidean meta-state novelty.

    The score is intentionally simple and deterministic. Thresholds are learned only from the
    earlier-season training distribution (80th and 95th percentiles), never from outcomes in
    the target season.
    """
    x_train = _feature_matrix(train, "component")
    x_test = _feature_matrix(test, "component")
    scaler = StandardScaler().fit(x_train)
    z_train = scaler.transform(x_train)
    z_test = scaler.transform(x_test)
    train_score = np.sqrt(np.mean(np.square(z_train), axis=1))
    test_score = np.sqrt(np.mean(np.square(z_test), axis=1))
    return test_score, float(np.quantile(train_score, 0.80)), float(np.quantile(train_score, 0.95))


def _season_forward_predictions(frame: pd.DataFrame, target_seasons: Iterable[int]) -> pd.DataFrame:
    outputs: list[pd.DataFrame] = []
    for season in target_seasons:
        train = frame[frame["season"] < int(season)].copy()
        test = frame[frame["season"] == int(season)].copy()
        if train.empty or test.empty:
            continue
        component_prob, _ = _fit_predict(train, test, "component")
        fst_prob, _ = _fit_predict(train, test, "fst")
        novelty, q80, q95 = _novelty(train, test)

        out = test[["game_id", "season", "week", "home_win", "market_prob", "pure_prob", *COMPONENTS]].copy()
        out["component_prob"] = component_prob
        out["fst_prob"] = fst_prob
        out["novelty_score"] = novelty
        out["novelty_q80_train"] = q80
        out["novelty_q95_train"] = q95
        out["novelty_band"] = np.where(
            novelty <= q80,
            "in_distribution_le_q80",
            np.where(novelty <= q95, "elevated_q80_q95", "high_gt_q95"),
        )
        outputs.append(out)
    if not outputs:
        return pd.DataFrame()
    return pd.concat(outputs, ignore_index=True)


def _side_correct(prob: pd.Series, y: pd.Series) -> pd.Series:
    pred = (pd.to_numeric(prob, errors="raise") >= 0.5).astype(int)
    return pred.eq(pd.to_numeric(y, errors="raise").astype(int))


def _segment_switches(disagree: pd.DataFrame, column: str) -> list[dict]:
    rows: list[dict] = []
    for value, group in disagree.groupby(column, dropna=False, sort=True):
        c = int(group["component_correct"].sum())
        f = int(group["fst_correct"].sum())
        n = int(len(group))
        rows.append(
            {
                "segment": None if pd.isna(value) else str(value),
                "switches": n,
                "component_correct": c,
                "fst_correct": f,
                "switch_win_rate": float(c / n) if n else None,
                "net_correct_vs_fst": int(c - f),
            }
        )
    return rows


def _finite_sample_quantile(values: np.ndarray, alpha: float) -> float:
    values = np.sort(np.asarray(values, dtype=float))
    n = len(values)
    if n == 0:
        raise ValueError("empty conformal calibration sample")
    rank = min(n, int(np.ceil((n + 1) * (1.0 - alpha))))
    return float(values[rank - 1])


def _conformal_switch_audit(all_predictions: pd.DataFrame) -> dict:
    """One-season-lag split-conformal diagnostic.

    For target season S, the immediately preceding season S-1 is the calibration sample.
    Its probabilities were themselves generated season-forward, so target outcomes never
    enter either model fitting or calibration. A switch is considered only when the 90%
    conformal prediction set is a singleton opposite the F-ST side.
    """
    evaluated: list[pd.DataFrame] = []
    per_season: list[dict] = []
    for season in TARGET_SEASONS:
        calibration = all_predictions[all_predictions["season"] == season - 1].copy()
        target = all_predictions[all_predictions["season"] == season].copy()
        if calibration.empty or target.empty:
            continue
        y_cal = calibration["home_win"].astype(int).to_numpy()
        p_cal = calibration["component_prob"].to_numpy(dtype=float)
        p_true = np.where(y_cal == 1, p_cal, 1.0 - p_cal)
        q = _finite_sample_quantile(1.0 - p_true, ALPHA)

        p = target["component_prob"].to_numpy(dtype=float)
        include_home = (1.0 - p) <= q
        include_away = p <= q
        singleton_home = include_home & ~include_away
        singleton_away = include_away & ~include_home
        target["conformal_singleton"] = singleton_home | singleton_away
        target["conformal_side"] = np.where(singleton_home, 1, np.where(singleton_away, 0, -1))
        fst_side = (target["fst_prob"].to_numpy(dtype=float) >= 0.5).astype(int)
        target["conformal_switch"] = target["conformal_singleton"] & (target["conformal_side"].to_numpy() != fst_side)
        switched = target[target["conformal_switch"]].copy()
        switched["component_correct"] = switched["conformal_side"].astype(int).eq(switched["home_win"].astype(int))
        switched["fst_correct"] = _side_correct(switched["fst_prob"], switched["home_win"])
        evaluated.append(switched)
        per_season.append(
            {
                "season": int(season),
                "calibration_season": int(season - 1),
                "calibration_games": int(len(calibration)),
                "q90_nonconformity": float(q),
                "singleton_games": int(target["conformal_singleton"].sum()),
                "switches_vs_fst": int(len(switched)),
                "component_correct": int(switched["component_correct"].sum()),
                "fst_correct": int(switched["fst_correct"].sum()),
            }
        )

    combined = pd.concat(evaluated, ignore_index=True) if evaluated else pd.DataFrame()
    n = int(len(combined))
    c = int(combined["component_correct"].sum()) if n else 0
    f = int(combined["fst_correct"].sum()) if n else 0
    return {
        "alpha": ALPHA,
        "method": "one-season-lag split conformal; finite-sample classification set",
        "per_season": per_season,
        "switches": n,
        "component_correct": c,
        "fst_correct": f,
        "switch_win_rate": float(c / n) if n else None,
        "net_correct_vs_fst": int(c - f),
        "promotion_authorized": False,
    }


def run(output_dir: str = "research_outputs/levline4_error_correction_challengers_v1") -> dict:
    frame = _load_frame()
    # Generate 2021 as a strictly earlier calibration season for the 2022 conformal audit.
    all_predictions = _season_forward_predictions(frame, (2021, *TARGET_SEASONS))
    scored = all_predictions[all_predictions["season"].isin(TARGET_SEASONS)].copy()

    if len(scored) != 1087:
        raise RuntimeError(f"expected exact 2022-2025 common sample of 1087 games, got {len(scored)}")

    scored["market_correct"] = _side_correct(scored["market_prob"], scored["home_win"])
    scored["component_correct"] = _side_correct(scored["component_prob"], scored["home_win"])
    scored["fst_correct"] = _side_correct(scored["fst_prob"], scored["home_win"])
    scored["component_side"] = (scored["component_prob"] >= 0.5).astype(int)
    scored["fst_side"] = (scored["fst_prob"] >= 0.5).astype(int)
    scored["component_fst_disagree"] = scored["component_side"].ne(scored["fst_side"])

    component_values = scored[list(COMPONENTS)].to_numpy(dtype=float)
    component_sides = (component_values >= 0.5).astype(int)
    chosen = scored["component_side"].to_numpy(dtype=int)
    scored["component_votes_for_challenger"] = (component_sides == chosen[:, None]).sum(axis=1)
    scored["component_dispersion_std"] = component_values.std(axis=1)
    scored["dispersion_band"] = pd.cut(
        scored["component_dispersion_std"],
        bins=[-np.inf, 0.05, 0.10, np.inf],
        labels=["low_le_0.05", "medium_0.05_0.10", "high_gt_0.10"],
        right=True,
    ).astype(str)
    scored["market_favorite_prob"] = np.maximum(scored["market_prob"], 1.0 - scored["market_prob"])
    scored["market_strength_band"] = pd.cut(
        scored["market_favorite_prob"],
        bins=[0.5, 0.525, 0.55, 1.0],
        labels=["coinflip_0.50_0.525", "boundary_0.525_0.55", "clear_gt_0.55"],
        include_lowest=True,
    ).astype(str)

    disagree = scored[scored["component_fst_disagree"]].copy()

    def gate_result(name: str, mask: pd.Series, definition: str) -> dict:
        group = disagree.loc[mask].copy()
        n = int(len(group))
        c = int(group["component_correct"].sum())
        f = int(group["fst_correct"].sum())
        return {
            "gate": name,
            "definition": definition,
            "switches": n,
            "component_correct": c,
            "fst_correct": f,
            "switch_win_rate": float(c / n) if n else None,
            "net_correct_vs_fst": int(c - f),
            "promotion_authorized": False,
        }

    low_novelty = disagree["novelty_band"].eq("in_distribution_le_q80")
    three_plus = disagree["component_votes_for_challenger"].ge(3)
    market_boundary = disagree["market_favorite_prob"].lt(0.55)

    report = {
        "audit_id": "LEVLINE4-ERROR-CORRECTION-CHALLENGERS-V1",
        "status": "historical_diagnostic_not_prospective_proof",
        "governance": {
            "research_only": True,
            "completed_2026_outcomes_used": 0,
            "production_changed": False,
            "automatic_promotion_allowed": False,
            "thresholds_selected_from_target_outcomes": False,
        },
        "sample": {
            "seasons": list(TARGET_SEASONS),
            "games": int(len(scored)),
            "evaluation": "season-forward; every target season is fit only on earlier seasons",
        },
        "reproduction": {
            "market_correct": int(scored["market_correct"].sum()),
            "market_accuracy": float(scored["market_correct"].mean()),
            "fst_correct": int(scored["fst_correct"].sum()),
            "fst_accuracy": float(scored["fst_correct"].mean()),
            "component_correct": int(scored["component_correct"].sum()),
            "component_accuracy": float(scored["component_correct"].mean()),
            "component_vs_fst_disagreements": int(len(disagree)),
            "component_only_correct": int((disagree["component_correct"] & ~disagree["fst_correct"]).sum()),
            "fst_only_correct": int((~disagree["component_correct"] & disagree["fst_correct"]).sum()),
        },
        "disagreement_topology": {
            "by_component_votes_for_challenger": _segment_switches(disagree, "component_votes_for_challenger"),
            "by_component_dispersion": _segment_switches(disagree, "dispersion_band"),
            "by_training_defined_novelty": _segment_switches(disagree, "novelty_band"),
            "by_market_strength": _segment_switches(disagree, "market_strength_band"),
        },
        "predeclared_selective_gates": [
            gate_result(
                "low_novelty_only",
                low_novelty,
                "component/F-ST disagreement and standardized meta-state novelty <= training-season q80",
            ),
            gate_result(
                "low_novelty_plus_3of4",
                low_novelty & three_plus,
                "low-novelty disagreement with >=3 of 4 base components on challenger side",
            ),
            gate_result(
                "low_novelty_plus_3of4_plus_market_boundary",
                low_novelty & three_plus & market_boundary,
                "prior gate plus market favorite probability <0.55",
            ),
        ],
        "chronological_conformal_gate": _conformal_switch_audit(all_predictions),
        "interpretation_policy": {
            "small_n_warning": "Any attractive subgroup remains exploratory unless it is season-stable and survives prospective shadow evaluation.",
            "generic_upset_override_remains_rejected": True,
            "point_estimate_is_not_promotion": True,
        },
        "promotion_authorized": False,
    }

    # Reproduction is a hard provenance check: if this fails, no new subgroup result is interpretable.
    expected = {
        "market_correct": 735,
        "fst_correct": 741,
        "component_correct": 744,
        "component_vs_fst_disagreements": 17,
        "component_only_correct": 10,
        "fst_only_correct": 7,
    }
    for key, value in expected.items():
        if report["reproduction"][key] != value:
            raise RuntimeError(
                f"historical reproduction drift for {key}: expected {value}, got {report['reproduction'][key]}"
            )

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    scored.to_csv(out / "scored_games.csv", index=False)
    disagree.to_csv(out / "component_fst_disagreements.csv", index=False)
    (out / "audit.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/levline4_error_correction_challengers_v1")
    args = parser.parse_args()
    run(args.output_dir)


if __name__ == "__main__":
    main()
