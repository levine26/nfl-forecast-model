from __future__ import annotations

"""Execute the frozen ATS-FAIR-LINE-POLICY-V1 historical audit.

The audit reproduces the production Core margin architecture in strict expanding-
season chronology. It never requests 2026 data and never uses F-ST winner output to
choose an ATS side.
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nfl_forecast.ats_fair_line_policy import (
    OUTER_SEASONS,
    REFERENCE_BREAK_EVEN,
    bootstrap_hit_rate,
    classification,
    grade_oof,
    margin_diagnostics,
    record,
    season_records,
    selective_records,
)
from nfl_forecast.config import load_config
from nfl_forecast.data import load_core_data
from nfl_forecast.elo import build_pregame_elo
from nfl_forecast.features import add_game_results, aggregate_team_games, build_matchup_features, core_columns
from nfl_forecast.models import fit_weighted_regression

HISTORICAL_END = 2025
POLICY_ID = "ATS-FAIR-LINE-POLICY-V1"
PREREGISTRATION = Path("research/ats-fair-line-policy/PREREGISTRATION.md")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _build_games(config_path: str) -> tuple[pd.DataFrame, dict, list[int]]:
    cfg = load_config(config_path)
    start = int(cfg["data"]["core_start_season"])
    requested_seasons = list(range(start, HISTORICAL_END + 1))
    if any(season > HISTORICAL_END for season in requested_seasons):
        raise RuntimeError("historical request crossed the 2025 outcome firewall")

    bundle = load_core_data(requested_seasons, cfg["data"]["cache_dir"])
    schedules = bundle.schedules.copy()
    schedule_season = pd.to_numeric(schedules["season"], errors="coerce")
    if schedule_season.isna().any() or schedule_season.gt(HISTORICAL_END).any():
        raise RuntimeError("audit received post-2025 schedule rows")

    elo = build_pregame_elo(
        schedules,
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
    team_games = add_game_results(team_games, schedules)
    games = build_matchup_features(team_games, schedules, elo)
    games["season"] = pd.to_numeric(games["season"], errors="coerce")
    games["week"] = pd.to_numeric(games["week"], errors="coerce")
    if games["season"].isna().any() or games["season"].gt(HISTORICAL_END).any():
        raise RuntimeError("matchup frame crossed the 2025 outcome firewall")
    return games, cfg, requested_seasons


def _generate_outer_oof(games: pd.DataFrame, cfg: dict) -> tuple[pd.DataFrame, list[dict]]:
    completed = games[
        games["margin"].notna()
        & games["season"].le(HISTORICAL_END)
    ].copy()
    features = core_columns(completed)
    if not features:
        raise RuntimeError("production Core margin feature set is empty")

    start = int(cfg["data"]["core_start_season"])
    seed = int(cfg["model"]["random_state"])
    outputs: list[pd.DataFrame] = []
    chronology: list[dict] = []

    for outer in OUTER_SEASONS:
        train = completed[completed["season"].lt(outer)].copy()
        target = completed[completed["season"].eq(outer)].copy()
        if train.empty or target.empty:
            raise RuntimeError(f"outer season {outer} lacks training or target rows")
        if int(train["season"].max()) >= outer:
            raise RuntimeError(f"outer season {outer} training chronology leaked")

        validation_start = max(start + 1, outer - 4)
        validation_end = outer - 1
        model = fit_weighted_regression(
            train,
            features,
            "margin",
            seed=seed,
            validation_start=validation_start,
            validation_end=validation_end,
        )
        prediction = np.asarray(model.predict(target), dtype=float)
        if len(prediction) != len(target) or not np.isfinite(prediction).all():
            raise RuntimeError(f"outer season {outer} produced invalid margin predictions")

        keep = [
            column
            for column in (
                "game_id", "season", "week", "gameday", "home_team", "away_team",
                "home_score", "away_score", "margin", "spread_line", "total_line",
            )
            if column in target.columns
        ]
        part = target[keep].copy()
        part["expected_margin"] = prediction
        part["margin_validation_mae"] = float(model.validation_mae)
        for name, weight in sorted(model.weights.items()):
            part[f"ensemble_weight_{name}"] = float(weight)
        outputs.append(part)
        chronology.append({
            "outer_target_season": int(outer),
            "training_min_season": int(train["season"].min()),
            "training_max_season": int(train["season"].max()),
            "training_rows": int(len(train)),
            "target_rows": int(len(target)),
            "validation_start": int(validation_start),
            "validation_end": int(validation_end),
            "validation_mae": float(model.validation_mae),
            "weights": {name: float(weight) for name, weight in sorted(model.weights.items())},
        })

    oof = pd.concat(outputs, ignore_index=True)
    if "game_id" in oof.columns and oof["game_id"].astype(str).duplicated().any():
        raise RuntimeError("fair-line OOF contains duplicate game_id")
    observed = sorted(pd.to_numeric(oof["season"], errors="raise").astype(int).unique().tolist())
    if observed != list(OUTER_SEASONS):
        raise RuntimeError(f"outer-season result contract drifted: {observed}")
    return oof, chronology


def _markdown(summary: dict) -> str:
    agg = summary["aggregate"]
    boot = summary["bootstrap"]
    diag = summary["margin_diagnostics"]
    lines = [
        "# ATS Fair-Line Policy V1 — Historical Audit Result",
        "",
        f"**Classification:** `{summary['classification']}`  ",
        f"**Outer seasons:** 2022–2025  ",
        f"**Completed-2026 outcomes used:** {summary['completed_2026_outcomes_used']}  ",
        "",
        "## Aggregate ATS policy",
        "",
        f"- W-L-P: **{agg['wins']}-{agg['losses']}-{agg['pushes']}**",
        f"- Decisions: **{agg['decisions']}**; exact no-edge rows: **{agg['no_edge']}**",
        f"- Ex-push hit rate: **{agg['hit_rate_ex_push']:.4%}**",
        f"- Exact 95% Clopper-Pearson interval: **[{agg['ci_lower']:.4%}, {agg['ci_upper']:.4%}]**",
        f"- Reference -110 net units (risk 1.10 to win 1.00): **{agg['reference_minus110_net_units']:.2f}**",
        f"- Reference -110 ROI on risk: **{agg['reference_minus110_roi_on_risk']:.4%}**",
        "",
        "## Week-block uncertainty",
        "",
        f"- 95% bootstrap interval: **[{boot['ci_lower']:.4%}, {boot['ci_upper']:.4%}]**",
        f"- P(hit rate > 50%): **{boot['probability_hit_rate_gt_50pct']:.4f}**",
        f"- P(hit rate > 52.38095%): **{boot['probability_hit_rate_gt_reference_break_even']:.4f}**",
        "",
        "## Margin diagnostics",
        "",
        f"- LevLine margin MAE: **{diag['levline_margin_mae']:.4f}**",
        f"- Market spread-center MAE: **{diag['market_spread_center_mae']:.4f}**",
        f"- LevLine − market MAE: **{diag['levline_minus_market_mae']:+.4f}**",
        f"- Pearson(edge, realized ATS residual): **{diag['pearson_edge_vs_ats_residual']:+.4f}**",
        f"- Spearman(edge, realized ATS residual): **{diag['spearman_edge_vs_ats_residual']:+.4f}**",
        "",
        "## Interpretation boundary",
        "",
        "The winner/ATS decoupling is a production semantics contract and is not contingent on this historical classification. This audit only tests whether the existing independent LevLine margin forecast historically supplied ATS directional information on the frozen 2022–2025 development sample. No post-result threshold, favorite/underdog filter, F-ST agreement filter, or 2026 outcome was used.",
        "",
    ]
    return "\n".join(lines)


def run(
    output_dir: str = "research_outputs/ats_fair_line_policy",
    *,
    config_path: str = "config/model.yaml",
) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    if not PREREGISTRATION.is_file():
        raise RuntimeError("frozen fair-line preregistration is missing")

    games, cfg, requested_seasons = _build_games(config_path)
    oof, chronology = _generate_outer_oof(games, cfg)
    graded = grade_oof(oof)
    aggregate = record(graded)
    seasons = season_records(graded)
    selective = selective_records(graded)
    diagnostics = margin_diagnostics(graded)
    bootstrap = bootstrap_hit_rate(graded)
    label = classification(aggregate, seasons, bootstrap)
    season_passes = int((pd.to_numeric(seasons["hit_rate_ex_push"], errors="coerce") >= 0.50).sum())

    graded_path = out / "ats_fair_line_outer_oof_2022_2025.csv"
    seasons_path = out / "ats_fair_line_season_results.csv"
    selective_path = out / "ats_fair_line_fixed_selective_diagnostics.csv"
    graded.to_csv(graded_path, index=False, float_format="%.17g")
    seasons.to_csv(seasons_path, index=False, float_format="%.17g")
    selective.to_csv(selective_path, index=False, float_format="%.17g")

    summary = {
        "status": "COMPLETE",
        "policy_id": POLICY_ID,
        "classification": label,
        "historical_evidence_class": "development_non_pristine",
        "production_changed_by_audit": False,
        "winner_ats_decoupling_is_contingent_on_audit": False,
        "completed_2026_outcomes_used": 0,
        "f_st_winner_filter_used": False,
        "post_result_threshold_tuning_performed": False,
        "requested_seasons": requested_seasons,
        "outer_target_seasons": list(OUTER_SEASONS),
        "reference_break_even_rate": REFERENCE_BREAK_EVEN,
        "reference_minus110_convention": "risk_1.10_to_win_1.00; pushes_return_stake",
        "preregistration_sha256": _sha256(PREREGISTRATION),
        "chronology": chronology,
        "aggregate": aggregate.__dict__,
        "season_results": seasons.to_dict(orient="records"),
        "seasons_at_or_above_50pct": season_passes,
        "fixed_selective_diagnostics": selective.to_dict(orient="records"),
        "margin_diagnostics": diagnostics,
        "bootstrap": bootstrap,
        "frozen_gate": {
            "aggregate_hit_rate_gt_reference_break_even": bool(aggregate.hit_rate_ex_push > REFERENCE_BREAK_EVEN),
            "bootstrap_probability_gt_50pct_at_least_0_80": bool(float(bootstrap["probability_hit_rate_gt_50pct"]) >= 0.80),
            "at_least_3_of_4_seasons_at_or_above_50pct": bool(season_passes >= 3),
            "chronology_and_2026_firewall_pass": True,
        },
    }
    summary_path = out / "ats_fair_line_policy_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (out / "ATS_FAIR_LINE_POLICY_RESULT.md").write_text(_markdown(summary), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="research_outputs/ats_fair_line_policy")
    parser.add_argument("--config", default="config/model.yaml")
    args = parser.parse_args()
    run(args.output_dir, config_path=args.config)


if __name__ == "__main__":
    main()
