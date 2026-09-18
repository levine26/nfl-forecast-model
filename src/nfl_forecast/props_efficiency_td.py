from __future__ import annotations

"""Research-beta efficiency/matchup/TD parameters for LevLine offensive props.

Opportunity volume is upstream. This module supplies shrunken conditional efficiency,
red-zone/goal-line opportunity rates, and team-coherent TD allocation. It never mutates
LevLine winner probabilities. Matchup effects are neutral unless coefficients trained
through 2025 or earlier are explicitly supplied.
"""

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

ENGINE_VERSION = "props-efficiency-td-research-beta-v1"
MAX_TRAINING_SEASON = 2025
PRIOR_STRENGTH = {
    "completion_rate": 150.0,
    "yards_per_completion": 75.0,
    "rushing_ypc": 65.0,
    "catch_rate": 45.0,
    "receiving_ypr": 45.0,
    "red_zone_target_rate": 45.0,
    "end_zone_target_rate": 60.0,
    "goal_line_carry_rate": 65.0,
}
TD_ALLOCATION_PRIOR_STRENGTH = 8.0
POSITIONS = {"QB", "RB", "WR", "TE"}
SOURCE_STATES = {"qualified", "prospective_unqualified", "unknown"}
PROHIBITED = {
    "actual_current_game_snaps", "actual_snap_count", "actual_snap_share",
    "actual_participation", "final_inactive_learned_post_kickoff", "postgame_player_value",
    "home_win", "actual_home_score", "actual_away_score", "actual_passing_yards",
    "actual_rushing_yards", "actual_receiving_yards", "actual_receptions",
    "actual_passing_tds", "actual_rushing_tds", "actual_receiving_tds",
}
MATCHUP_FEATURES = {
    "pressure_pass_rush_mismatch_z", "ol_pass_rush_mismatch_z", "man_rate_matchup_z",
    "zone_rate_matchup_z", "explosive_pass_suppression_z", "slot_coverage_mismatch_z",
    "outside_coverage_mismatch_z", "rb_linebacker_coverage_mismatch_z",
    "tackling_yac_suppression_z", "box_run_tendency_z", "run_defense_efficiency_z",
    "red_zone_defense_z", "qb_scramble_pressure_matchup_z", "defensive_availability_impact_z",
}
PLAYER_METRICS = {
    "completion_rate", "yards_per_completion", "rushing_ypc", "catch_rate",
    "receiving_ypr", "red_zone_target_rate", "end_zone_target_rate", "goal_line_carry_rate",
}
TEAM_METRICS = {"red_zone_td_rate", "pass_td_fraction"}

PLAYER_REQUIRED = {
    "game_id", "season", "week", "team", "opponent", "player_id", "player_name", "position",
    "forecast_timestamp", "kickoff_timestamp", "feature_data_horizon", "source_status",
    "prior_model_trained_through_season", "expected_pass_attempts", "expected_qb_rush_attempts",
    "expected_carries", "expected_routes", "expected_targets", "hist_pass_attempts",
    "hist_completions", "hist_passing_yards", "hist_qb_rush_attempts", "hist_qb_rush_yards",
    "hist_carries", "hist_rushing_yards", "hist_targets", "hist_receptions",
    "hist_receiving_yards", "hist_red_zone_targets", "hist_end_zone_targets",
    "hist_goal_line_carries", "prior_completion_rate", "prior_yards_per_completion_mean",
    "prior_yards_per_completion_sd", "prior_qb_rush_ypc_mean", "prior_qb_rush_ypc_sd",
    "prior_rush_ypc_mean", "prior_rush_ypc_sd", "prior_catch_rate",
    "prior_receiving_ypr_mean", "prior_receiving_ypr_sd", "prior_red_zone_target_rate",
    "prior_end_zone_target_rate", "prior_goal_line_carry_rate",
}
TEAM_REQUIRED = {
    "game_id", "season", "week", "team", "opponent", "forecast_timestamp", "kickoff_timestamp",
    "feature_data_horizon", "source_status", "prior_model_trained_through_season",
    "expected_drives", "expected_red_zone_trips", "prior_red_zone_td_rate",
    "prior_pass_td_fraction", "expected_non_red_zone_pass_tds", "expected_non_red_zone_rush_tds",
}
TEXT_PLAYER = {
    "game_id", "team", "opponent", "player_id", "player_name", "position",
    "forecast_timestamp", "kickoff_timestamp", "feature_data_horizon", "source_status",
}
TEXT_TEAM = {
    "game_id", "team", "opponent", "forecast_timestamp", "kickoff_timestamp",
    "feature_data_horizon", "source_status",
}


@dataclass(frozen=True)
class EfficiencyTDBuild:
    player_parameters: pd.DataFrame
    team_td_parameters: pd.DataFrame
    diagnostics: pd.DataFrame
    audit: dict[str, Any]


def _require(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"{label} missing required fields: {sorted(missing)}")


def _aware_utc_series(frame: pd.DataFrame, column: str, label: str) -> pd.Series:
    parsed: list[pd.Timestamp] = []
    for value in frame[column]:
        try:
            ts = pd.Timestamp(value)
        except Exception as exc:
            raise ValueError(f"{label} timestamps must be parseable") from exc
        if ts.tzinfo is None:
            raise ValueError(f"{label} timestamps must be timezone-aware: {column}")
        parsed.append(ts.tz_convert("UTC"))
    return pd.Series(parsed, index=frame.index)


def _validate_common(frame: pd.DataFrame, required: set[str], text: set[str], label: str) -> None:
    _require(frame, required, label)
    bad = PROHIBITED.intersection(frame.columns)
    if bad:
        raise ValueError(f"{label} refuses current-game/postgame outcome fields: {sorted(bad)}")
    if frame.empty:
        raise ValueError(f"{label} requires at least one row")
    for col in required - text:
        values = pd.to_numeric(frame[col], errors="coerce")
        if values.isna().any() or not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"{label} numeric field is incomplete/non-finite: {col}")
    forecast = _aware_utc_series(frame, "forecast_timestamp", label)
    kickoff = _aware_utc_series(frame, "kickoff_timestamp", label)
    horizon = _aware_utc_series(frame, "feature_data_horizon", label)
    if (forecast >= kickoff).any():
        raise ValueError(f"{label} forecast_timestamp must be before kickoff")
    if (horizon > forecast).any():
        raise ValueError(f"{label} feature_data_horizon cannot be after forecast_timestamp")
    if (pd.to_numeric(frame.prior_model_trained_through_season) > MAX_TRAINING_SEASON).any():
        raise ValueError("Research-beta priors may not be trained on completed 2026 outcomes")
    invalid = set(frame.source_status.astype(str)) - SOURCE_STATES
    if invalid:
        raise ValueError(f"{label} invalid source_status: {sorted(invalid)}")


def validate_player_inputs(frame: pd.DataFrame) -> None:
    _validate_common(frame, PLAYER_REQUIRED, TEXT_PLAYER, "player efficiency input")
    ids = frame.player_id.astype("string").fillna("").str.strip()
    if ids.eq("").any() or ids.str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Stable player_id is required; ambiguous identity fails closed")
    if frame.duplicated(["game_id", "team", "player_id"]).any():
        raise ValueError("Duplicate player identity within game/team")
    pos = frame.position.astype(str).str.upper()
    if set(pos) - POSITIONS:
        raise ValueError(f"Unsupported offensive positions: {sorted(set(pos) - POSITIONS)}")
    signed_historical_yardage = {
        "hist_passing_yards",
        "hist_qb_rush_yards",
        "hist_rushing_yards",
        "hist_receiving_yards",
    }
    non_negative_player_fields = [
        col
        for col in PLAYER_REQUIRED
        if (
            col.startswith("expected_")
            or col.startswith("hist_")
        )
        and col not in signed_historical_yardage
    ]
    for col in non_negative_player_fields:
        if (pd.to_numeric(frame[col]) < 0).any():
            raise ValueError(f"{col} must be non-negative")
    for col in [
        "prior_completion_rate", "prior_catch_rate", "prior_red_zone_target_rate",
        "prior_end_zone_target_rate", "prior_goal_line_carry_rate",
    ]:
        v = pd.to_numeric(frame[col])
        if ((v <= 0) | (v >= 1)).any():
            raise ValueError(f"{col} must lie strictly within (0, 1)")
    if (frame.hist_completions > frame.hist_pass_attempts).any() or (frame.hist_receptions > frame.hist_targets).any():
        raise ValueError("Historical successes cannot exceed opportunities")
    if (frame.hist_red_zone_targets > frame.hist_targets).any() or (frame.hist_end_zone_targets > frame.hist_targets).any():
        raise ValueError("Historical target sub-count exceeds targets")
    rush_n = np.where(pos.eq("QB"), frame.hist_qb_rush_attempts, frame.hist_carries)
    if (frame.hist_goal_line_carries.to_numpy() > rush_n).any():
        raise ValueError("hist_goal_line_carries exceeds historical rush opportunities")


def validate_team_inputs(frame: pd.DataFrame) -> None:
    _validate_common(frame, TEAM_REQUIRED, TEXT_TEAM, "team TD input")
    if frame.duplicated(["game_id", "team"]).any():
        raise ValueError("Duplicate team TD input within game")
    for col in ["expected_drives", "expected_red_zone_trips", "expected_non_red_zone_pass_tds", "expected_non_red_zone_rush_tds"]:
        if (pd.to_numeric(frame[col]) < 0).any():
            raise ValueError(f"{col} must be non-negative")
    if (pd.to_numeric(frame.expected_red_zone_trips) > pd.to_numeric(frame.expected_drives)).any():
        raise ValueError("expected_red_zone_trips cannot exceed expected_drives")
    for col in ["prior_red_zone_td_rate", "prior_pass_td_fraction"]:
        v = pd.to_numeric(frame[col])
        if ((v <= 0) | (v >= 1)).any():
            raise ValueError(f"{col} must lie strictly within (0, 1)")


def validate_matchup_coefficients(coeff: pd.DataFrame | None) -> None:
    if coeff is None or coeff.empty:
        return
    needed = {"scope", "metric", "feature", "coefficient", "trained_through_season", "model_id", "position_scope"}
    _require(coeff, needed, "matchup coefficients")
    trained = pd.to_numeric(coeff.trained_through_season, errors="coerce")
    if trained.isna().any() or not np.isfinite(trained.to_numpy(dtype=float)).all():
        raise ValueError("Matchup coefficients require finite trained_through_season provenance")
    if (trained > MAX_TRAINING_SEASON).any():
        raise ValueError("Matchup coefficients trained on 2026 outcomes are prohibited")
    if ((trained % 1) != 0).any():
        raise ValueError("trained_through_season must be an integer season")
    model_ids = coeff.model_id.astype("string").fillna("").str.strip()
    if model_ids.eq("").any() or model_ids.str.lower().isin({"nan", "<na>"}).any():
        raise ValueError("Matchup coefficients require non-empty model_id provenance")
    c = pd.to_numeric(coeff.coefficient, errors="coerce")
    if c.isna().any() or not np.isfinite(c.to_numpy()).all():
        raise ValueError("Matchup coefficients must be finite")
    if coeff.duplicated(["scope", "metric", "feature", "position_scope", "model_id"]).any():
        raise ValueError("Duplicate matchup coefficient identity")
    bad_features = set(coeff.feature.astype(str)) - MATCHUP_FEATURES
    if bad_features:
        raise ValueError(f"Unapproved matchup feature(s): {sorted(bad_features)}")
    for _, row in coeff.iterrows():
        scope, metric = str(row.scope), str(row.metric)
        if scope == "player" and metric not in PLAYER_METRICS:
            raise ValueError(f"Unsupported player matchup metric: {metric}")
        if scope == "team" and metric not in TEAM_METRICS:
            raise ValueError(f"Unsupported team matchup metric: {metric}")
        if scope not in {"player", "team"}:
            raise ValueError(f"Unsupported matchup coefficient scope: {scope}")
        ps = str(row.position_scope).upper()
        if ps != "ALL" and ps not in POSITIONS:
            raise ValueError(f"Invalid position_scope: {ps}")
        if scope == "team" and ps != "ALL":
            raise ValueError("Team matchup coefficients must use position_scope=ALL")


def _beta(successes: float, trials: float, prior: float, strength: float) -> tuple[float, float, float]:
    a = prior * strength + successes
    b = (1 - prior) * strength + trials - successes
    return a, b, a / (a + b)


def _mean(total: float, n: float, prior: float, sd: float, strength: float) -> tuple[float, float, float]:
    return (total + strength * prior) / (n + strength), sd, sd / np.sqrt(n + strength)


def _delta(row: pd.Series, metric: str, scope: str, coeff: pd.DataFrame | None, position: str = "ALL") -> tuple[float, str]:
    if coeff is None or coeff.empty:
        return 0.0, "neutral_no_validated_coefficients"
    sub = coeff[(coeff.scope.astype(str) == scope) & (coeff.metric.astype(str) == metric)]
    if scope == "player":
        sub = sub[sub.position_scope.astype(str).str.upper().isin({"ALL", position.upper()})]
    if sub.empty:
        return 0.0, "neutral_no_metric_coefficients"
    value, models = 0.0, set()
    for _, c in sub.iterrows():
        feature = str(c.feature)
        if feature not in row.index or not np.isfinite(float(row[feature])):
            raise ValueError(f"Validated matchup feature missing/non-finite: {feature}")
        value += float(c.coefficient) * float(row[feature])
        models.add(str(c.model_id))
    return value, "validated:" + ",".join(sorted(models))


def _adjust(value: float, delta: float, probability: bool) -> float:
    if probability:
        logit = np.log(value / (1 - value)) + delta
        return float(1 / (1 + np.exp(-logit)))
    adjusted = float(value * np.exp(delta))
    if not np.isfinite(adjusted):
        raise ValueError("Matchup adjustment produced non-finite mean")
    return adjusted


def _efficiency(players: pd.DataFrame, coeff: pd.DataFrame | None) -> pd.DataFrame:
    rows = []
    for _, r in players.iterrows():
        pos, out, statuses = str(r.position).upper(), r.to_dict(), []
        samples: list[tuple[float, float]] = []
        if pos == "QB":
            a, b, m = _beta(r.hist_completions, r.hist_pass_attempts, r.prior_completion_rate, PRIOR_STRENGTH["completion_rate"])
            d, s = _delta(r, "completion_rate", "player", coeff, pos); statuses.append(s)
            m = _adjust(m, d, True); conc = a + b
            out.update(completion_alpha=m * conc, completion_beta=(1 - m) * conc, completion_rate_mean=m)
            m0, sd, se = _mean(r.hist_passing_yards, r.hist_completions, r.prior_yards_per_completion_mean, r.prior_yards_per_completion_sd, PRIOR_STRENGTH["yards_per_completion"])
            d, s = _delta(r, "yards_per_completion", "player", coeff, pos); statuses.append(s); mult = np.exp(d)
            out.update(yards_per_completion_mean=_adjust(m0, d, False), yards_per_completion_event_sd=sd * mult, yards_per_completion_mean_se=se * mult)
            samples += [(r.hist_pass_attempts, PRIOR_STRENGTH["completion_rate"]), (r.hist_completions, PRIOR_STRENGTH["yards_per_completion"])]
        else:
            for c in ["completion_alpha", "completion_beta", "completion_rate_mean", "yards_per_completion_mean", "yards_per_completion_event_sd", "yards_per_completion_mean_se"]:
                out[c] = np.nan

        if pos == "QB":
            n, yards, prior, sd = r.hist_qb_rush_attempts, r.hist_qb_rush_yards, r.prior_qb_rush_ypc_mean, r.prior_qb_rush_ypc_sd
        else:
            n, yards, prior, sd = r.hist_carries, r.hist_rushing_yards, r.prior_rush_ypc_mean, r.prior_rush_ypc_sd
        m0, event_sd, se = _mean(yards, n, prior, sd, PRIOR_STRENGTH["rushing_ypc"])
        d, s = _delta(r, "rushing_ypc", "player", coeff, pos); statuses.append(s); mult = np.exp(d)
        out.update(rushing_yards_per_attempt_mean=_adjust(m0, d, False), rushing_yards_per_attempt_event_sd=event_sd * mult, rushing_yards_per_attempt_mean_se=se * mult)
        samples.append((n, PRIOR_STRENGTH["rushing_ypc"]))

        if pos in {"RB", "WR", "TE"}:
            a, b, m = _beta(r.hist_receptions, r.hist_targets, r.prior_catch_rate, PRIOR_STRENGTH["catch_rate"])
            d, s = _delta(r, "catch_rate", "player", coeff, pos); statuses.append(s); m = _adjust(m, d, True); conc = a + b
            out.update(catch_alpha=m * conc, catch_beta=(1 - m) * conc, catch_rate_mean=m)
            m0, sd, se = _mean(r.hist_receiving_yards, r.hist_receptions, r.prior_receiving_ypr_mean, r.prior_receiving_ypr_sd, PRIOR_STRENGTH["receiving_ypr"])
            d, s = _delta(r, "receiving_ypr", "player", coeff, pos); statuses.append(s); mult = np.exp(d)
            out.update(receiving_yards_per_reception_mean=_adjust(m0, d, False), receiving_yards_per_reception_event_sd=sd * mult, receiving_yards_per_reception_mean_se=se * mult)
            samples += [(r.hist_targets, PRIOR_STRENGTH["catch_rate"]), (r.hist_receptions, PRIOR_STRENGTH["receiving_ypr"])]
        else:
            for c in ["catch_alpha", "catch_beta", "catch_rate_mean", "receiving_yards_per_reception_mean", "receiving_yards_per_reception_event_sd", "receiving_yards_per_reception_mean_se"]:
                out[c] = np.nan

        for metric, success, trials, prior in [
            ("red_zone_target_rate", r.hist_red_zone_targets, r.hist_targets, r.prior_red_zone_target_rate),
            ("end_zone_target_rate", r.hist_end_zone_targets, r.hist_targets, r.prior_end_zone_target_rate),
            ("goal_line_carry_rate", r.hist_goal_line_carries, n, r.prior_goal_line_carry_rate),
        ]:
            a, b, m = _beta(success, trials, prior, PRIOR_STRENGTH[metric])
            d, s = _delta(r, metric, "player", coeff, pos); statuses.append(s); m = _adjust(m, d, True); conc = a + b
            out[f"{metric}_alpha"], out[f"{metric}_beta"], out[f"{metric}_mean"] = m * conc, (1 - m) * conc, m
        out["expected_red_zone_targets"] = r.expected_targets * out["red_zone_target_rate_mean"]
        out["expected_end_zone_targets"] = r.expected_targets * out["end_zone_target_rate_mean"]
        rush_opp = r.expected_qb_rush_attempts if pos == "QB" else r.expected_carries
        out["td_rushing_opportunities"] = rush_opp
        out["expected_goal_line_carries"] = rush_opp * out["goal_line_carry_rate_mean"]
        conf = float(np.mean([n0 / (n0 + k) for n0, k in samples])) if samples else 0.0
        if r.source_status == "unknown": state = "degraded_source_unknown"
        elif r.source_status != "qualified": state = "prospective_unqualified"
        elif conf >= .60: state = "qualified_moderate_history"
        elif conf >= .25: state = "qualified_shrunk_history"
        else: state = "qualified_prior_dominant"
        out.update(matchup_adjustment_status=";".join(sorted(set(statuses))), confidence_state=state,
                   engine_version=ENGINE_VERSION, research_only=True, winner_probability_feature_authorized=False)
        rows.append(out)
    return pd.DataFrame(rows)


def _team_td(teams: pd.DataFrame, coeff: pd.DataFrame | None) -> pd.DataFrame:
    rows = []
    for _, r in teams.iterrows():
        d1, s1 = _delta(r, "red_zone_td_rate", "team", coeff)
        d2, s2 = _delta(r, "pass_td_fraction", "team", coeff)
        rz = _adjust(r.prior_red_zone_td_rate, d1, True)
        pf = _adjust(r.prior_pass_td_fraction, d2, True)
        rz_tds = r.expected_red_zone_trips * rz
        pass_mean = rz_tds * pf + r.expected_non_red_zone_pass_tds
        rush_mean = rz_tds * (1 - pf) + r.expected_non_red_zone_rush_tds
        rows.append({**r.to_dict(), "red_zone_td_rate_mean": rz, "pass_td_fraction_mean": pf,
                     "expected_red_zone_tds": rz_tds, "expected_passing_td_opportunities": pass_mean,
                     "expected_rushing_td_opportunities": rush_mean, "expected_total_offensive_tds": pass_mean + rush_mean,
                     "td_count_distribution": "poisson_shared_team_baseline", "td_count_mean": pass_mean + rush_mean,
                     "team_td_matchup_status": ";".join(sorted({s1, s2})), "engine_version": ENGINE_VERSION,
                     "research_only": True, "winner_probability_feature_authorized": False})
    return pd.DataFrame(rows)


def _share(part: pd.DataFrame, primary: str, fallback: str) -> pd.Series:
    p = pd.to_numeric(part[primary], errors="coerce").fillna(0).clip(lower=0)
    if p.sum() > 0: return p / p.sum()
    f = pd.to_numeric(part[fallback], errors="coerce").fillna(0).clip(lower=0)
    if f.sum() > 0: return f / f.sum()
    return pd.Series(1 / len(part), index=part.index, dtype=float)


def _dirichlet_share_sd(alpha: pd.Series) -> pd.Series:
    values = pd.to_numeric(alpha, errors="coerce").fillna(0.0).clip(lower=0.0)
    total = float(values.sum())
    if total <= 0:
        return pd.Series(0.0, index=values.index, dtype=float)
    variance = values * (total - values) / (total**2 * (total + 1.0))
    return np.sqrt(variance.clip(lower=0.0))


def _allocate(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    out = players.copy()
    cols = ["passing_td_share_mean", "receiving_td_share_mean", "rushing_td_share_mean",
            "passing_td_share_sd", "receiving_td_share_sd", "rushing_td_share_sd",
            "passing_td_allocation_alpha", "receiving_td_allocation_alpha", "rushing_td_allocation_alpha",
            "expected_passing_tds", "expected_receiving_tds", "expected_rushing_tds", "qb_rushing_td_share_mean"]
    for c in cols: out[c] = 0.0
    lookup = teams.set_index(["game_id", "team"])
    for key, part in out.groupby(["game_id", "team"], sort=False):
        if key not in lookup.index: raise ValueError(f"Missing team TD parameters for {key}")
        tr = lookup.loc[key]; pass_mean = float(tr.expected_passing_td_opportunities); rush_mean = float(tr.expected_rushing_td_opportunities)
        qb = part[(part.position.str.upper() == "QB") & (part.expected_pass_attempts > 0)]
        if pass_mean > 0 and qb.empty: raise ValueError(f"Positive passing-TD expectation requires a QB for {key}")
        if not qb.empty:
            base = _share(qb, "expected_pass_attempts", "expected_pass_attempts"); alpha = TD_ALLOCATION_PRIOR_STRENGTH * base; share = alpha / alpha.sum()
            share_sd = _dirichlet_share_sd(alpha)
            out.loc[qb.index, ["passing_td_allocation_alpha", "passing_td_share_mean", "passing_td_share_sd", "expected_passing_tds"]] = np.column_stack([alpha, share, share_sd, share * pass_mean])
        rec = part[part.expected_targets > 0]
        if pass_mean > 0 and rec.empty: raise ValueError(f"Positive passing-TD expectation requires receivers for {key}")
        if not rec.empty:
            base = _share(rec, "expected_end_zone_targets", "expected_red_zone_targets")
            if rec.expected_end_zone_targets.sum() <= 0 and rec.expected_red_zone_targets.sum() <= 0: base = _share(rec, "expected_targets", "expected_targets")
            alpha = rec.hist_end_zone_targets.astype(float) + TD_ALLOCATION_PRIOR_STRENGTH * base; share = alpha / alpha.sum()
            share_sd = _dirichlet_share_sd(alpha)
            out.loc[rec.index, ["receiving_td_allocation_alpha", "receiving_td_share_mean", "receiving_td_share_sd", "expected_receiving_tds"]] = np.column_stack([alpha, share, share_sd, share * pass_mean])
        rush = part[part.td_rushing_opportunities > 0]
        if rush_mean > 0 and rush.empty: raise ValueError(f"Positive rushing-TD expectation requires rushers for {key}")
        if not rush.empty:
            base = _share(rush, "expected_goal_line_carries", "td_rushing_opportunities")
            alpha = rush.hist_goal_line_carries.astype(float) + TD_ALLOCATION_PRIOR_STRENGTH * base; share = alpha / alpha.sum()
            share_sd = _dirichlet_share_sd(alpha)
            out.loc[rush.index, ["rushing_td_allocation_alpha", "rushing_td_share_mean", "rushing_td_share_sd", "expected_rushing_tds"]] = np.column_stack([alpha, share, share_sd, share * rush_mean])
            qidx = rush[rush.position.str.upper() == "QB"].index; out.loc[qidx, "qb_rushing_td_share_mean"] = out.loc[qidx, "rushing_td_share_mean"]
    pos = out.position.str.upper()
    out["expected_anytime_tds"] = np.where(
        pos == "QB",
        out.expected_rushing_tds,
        out.expected_rushing_tds + out.expected_receiving_tds,
    )
    out["receiving_td_prop_eligible"] = pos.isin({"RB", "WR", "TE"})
    out["rushing_td_prop_eligible"] = pos.isin({"QB", "RB"})
    out["anytime_td_prop_eligible"] = pos.isin(POSITIONS)
    out["td_allocation_uncertainty"] = out[
        ["passing_td_share_sd", "receiving_td_share_sd", "rushing_td_share_sd"]
    ].max(axis=1)
    out["td_allocation_uncertainty_method"] = "max_dirichlet_marginal_share_sd"
    return out


def _diagnostics(players: pd.DataFrame, teams: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, tr in teams.iterrows():
        p = players[(players.game_id == tr.game_id) & (players.team == tr.team)]
        pm, rm = float(tr.expected_passing_td_opportunities), float(tr.expected_rushing_td_opportunities)
        qp, rec, rush = p.expected_passing_tds.sum(), p.expected_receiving_tds.sum(), p.expected_rushing_tds.sum()
        rows.append({"game_id": tr.game_id, "team": tr.team, "passing_td_opportunities": pm, "qb_passing_td_sum": qp,
                     "receiving_td_sum": rec, "rushing_td_opportunities": rm, "player_rushing_td_sum": rush,
                     "qb_pass_reconciliation_error": qp - pm, "receiver_reconciliation_error": rec - pm,
                     "rusher_reconciliation_error": rush - rm, "receiving_td_share_sum": p.receiving_td_share_mean.sum(),
                     "rushing_td_share_sum": p.rushing_td_share_mean.sum(), "passing_td_share_sum": p.passing_td_share_mean.sum(),
                     "reconciled": abs(qp-pm)<1e-9 and abs(rec-pm)<1e-9 and abs(rush-rm)<1e-9, "engine_version": ENGINE_VERSION})
    return pd.DataFrame(rows)


def build_efficiency_td_parameters(player_inputs: pd.DataFrame, team_inputs: pd.DataFrame, *, matchup_coefficients: pd.DataFrame | None = None) -> EfficiencyTDBuild:
    validate_player_inputs(player_inputs); validate_team_inputs(team_inputs); validate_matchup_coefficients(matchup_coefficients)
    missing = set(zip(player_inputs.game_id, player_inputs.team)) - set(zip(team_inputs.game_id, team_inputs.team))
    if missing: raise ValueError(f"Player inputs reference missing team TD rows: {sorted(missing)}")
    team_meta = team_inputs.set_index(["game_id", "team"])
    for _, player in player_inputs.iterrows():
        team = team_meta.loc[(player.game_id, player.team)]
        for field in ("season", "week"):
            if float(player[field]) != float(team[field]):
                raise ValueError(f"Player/team metadata mismatch for {player.player_id}: {field}")
        if str(player.opponent) != str(team.opponent):
            raise ValueError(f"Player/team metadata mismatch for {player.player_id}: opponent")
        for field in ("forecast_timestamp", "kickoff_timestamp"):
            player_ts = pd.Timestamp(player[field]).tz_convert("UTC")
            team_ts = pd.Timestamp(team[field]).tz_convert("UTC")
            if player_ts != team_ts:
                raise ValueError(f"Player/team metadata mismatch for {player.player_id}: {field}")
    players = _efficiency(player_inputs.copy(), matchup_coefficients)
    teams = _team_td(team_inputs.copy(), matchup_coefficients)
    players = _allocate(players, teams); diag = _diagnostics(players, teams)
    if not diag.reconciled.all(): raise AssertionError("TD allocation failed team-level reconciliation")
    audit = {"engine_version": ENGINE_VERSION, "research_only": True, "winner_probability_feature_authorized": False,
             "player_rows": len(players), "team_rows": len(teams), "stable_player_ids": players.player_id.nunique(),
             "matchup_coefficients_applied": 0 if matchup_coefficients is None else len(matchup_coefficients),
             "matchup_training_season_max": None if matchup_coefficients is None or matchup_coefficients.empty else int(matchup_coefficients.trained_through_season.max()),
             "completed_2026_outcomes_used_for_architecture_or_tuning": 0, "td_reconciliation_failures": int((~diag.reconciled).sum()), "research_beta": True}
    return EfficiencyTDBuild(players.reset_index(drop=True), teams.reset_index(drop=True), diag, audit)


def simulator_contract_columns() -> dict[str, tuple[str, ...]]:
    return {
        "player_parameters": (
            "game_id", "team", "opponent", "player_id", "player_name", "position", "forecast_timestamp",
            "feature_data_horizon", "expected_pass_attempts", "expected_qb_rush_attempts", "expected_carries",
            "expected_routes", "expected_targets", "completion_alpha", "completion_beta", "completion_rate_mean",
            "yards_per_completion_mean", "yards_per_completion_event_sd", "yards_per_completion_mean_se",
            "rushing_yards_per_attempt_mean", "rushing_yards_per_attempt_event_sd", "rushing_yards_per_attempt_mean_se",
            "catch_alpha", "catch_beta", "catch_rate_mean", "receiving_yards_per_reception_mean",
            "receiving_yards_per_reception_event_sd", "receiving_yards_per_reception_mean_se",
            "expected_red_zone_targets", "expected_end_zone_targets", "expected_goal_line_carries",
            "passing_td_share_mean", "receiving_td_share_mean", "rushing_td_share_mean",
            "passing_td_share_sd", "receiving_td_share_sd", "rushing_td_share_sd",
            "passing_td_allocation_alpha", "receiving_td_allocation_alpha", "rushing_td_allocation_alpha", "expected_passing_tds",
            "expected_receiving_tds", "expected_rushing_tds", "expected_anytime_tds", "qb_rushing_td_share_mean",
            "td_allocation_uncertainty", "td_allocation_uncertainty_method", "confidence_state",
            "matchup_adjustment_status", "engine_version", "research_only",
        ),
        "team_td_parameters": (
            "game_id", "team", "opponent", "forecast_timestamp", "feature_data_horizon", "expected_drives",
            "expected_red_zone_trips", "red_zone_td_rate_mean", "pass_td_fraction_mean", "expected_red_zone_tds",
            "expected_passing_td_opportunities", "expected_rushing_td_opportunities", "expected_total_offensive_tds",
            "td_count_distribution", "td_count_mean", "team_td_matchup_status", "engine_version", "research_only",
        ),
    }
