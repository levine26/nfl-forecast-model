from __future__ import annotations

"""Validated frozen-manifest assembly for LevLine Props Research Beta."""

from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

from .props_player_state import normalize_team_code


MANIFEST_CONTRACT_VERSION = "levline-props-integration-manifest-v0.1"
MAX_TRAINING_SEASON = 2025
OPTIONAL_CONTROLS = (
    "model_version",
    "simulations",
    "seed",
    "shared_pace_correlation",
    "shared_scoring_log_sd",
    "pass_rate_game_script_sensitivity",
    "prediction_interval_level",
)


class PropsManifestError(ValueError):
    pass


def _canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def payload_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _aware(value: object, label: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise PropsManifestError(f"{label} must be a valid timestamp") from exc
    if parsed.tzinfo is None:
        raise PropsManifestError(f"{label} must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def _required_text(mapping: Mapping[str, Any], key: str, label: str) -> str:
    value = str(mapping.get(key) or "").strip()
    if not value:
        raise PropsManifestError(f"{label} missing required field: {key}")
    return value


def _validate_projection_set(
    projections: Sequence[Mapping[str, Any]],
    *,
    expected_teams: set[str],
    forecast: datetime,
) -> str:
    if len(projections) != 2:
        raise PropsManifestError("integration manifest requires exactly two team opportunity projections")
    game_ids: set[str] = set()
    teams: set[str] = set()
    for raw in projections:
        metadata = raw.get("metadata")
        if not isinstance(metadata, Mapping):
            raise PropsManifestError("opportunity projection metadata is required")
        game_ids.add(_required_text(metadata, "game_id", "opportunity projection"))
        teams.add(normalize_team_code(_required_text(metadata, "team", "opportunity projection")))
        projection_forecast = _aware(
            metadata.get("forecast_timestamp"), "opportunity forecast_timestamp"
        )
        horizon = _aware(metadata.get("data_horizon"), "opportunity data_horizon")
        if horizon > projection_forecast:
            raise PropsManifestError("opportunity data_horizon cannot exceed its forecast timestamp")
        if projection_forecast > forecast:
            raise PropsManifestError("opportunity projection cannot be newer than manifest forecast")
    if teams != expected_teams:
        raise PropsManifestError(
            f"opportunity teams {sorted(teams)} do not match game teams {sorted(expected_teams)}"
        )
    if len(game_ids) != 1:
        raise PropsManifestError("opportunity projections disagree on game_id")
    return next(iter(game_ids))


def _validate_efficiency_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    game_id: str,
    expected_teams: set[str],
    forecast: datetime,
    kickoff: datetime,
) -> None:
    if not rows:
        raise PropsManifestError("efficiency_player_parameters cannot be empty")
    identities: set[tuple[str, str]] = set()
    seen_teams: set[str] = set()
    for row in rows:
        if str(row.get("game_id") or "") != game_id:
            raise PropsManifestError("efficiency row game_id does not match opportunity game")
        team = normalize_team_code(_required_text(row, "team", "efficiency row"))
        if team not in expected_teams:
            raise PropsManifestError(f"unexpected efficiency team: {team}")
        seen_teams.add(team)
        player_id = _required_text(row, "player_id", "efficiency row")
        identity = (team, player_id)
        if identity in identities:
            raise PropsManifestError(f"duplicate efficiency player identity: {team}/{player_id}")
        identities.add(identity)
        row_forecast = _aware(row.get("forecast_timestamp"), "efficiency forecast_timestamp")
        horizon = _aware(row.get("feature_data_horizon"), "efficiency feature_data_horizon")
        row_kickoff = _aware(row.get("kickoff_timestamp"), "efficiency kickoff_timestamp")
        if horizon > row_forecast or row_forecast > forecast:
            raise PropsManifestError("efficiency timestamps violate point-in-time ordering")
        if row_kickoff != kickoff:
            raise PropsManifestError("efficiency kickoff timestamp disagrees with game spec")
        try:
            trained_through = int(row.get("prior_model_trained_through_season"))
        except (TypeError, ValueError) as exc:
            raise PropsManifestError(
                "efficiency row requires prior_model_trained_through_season"
            ) from exc
        if trained_through > MAX_TRAINING_SEASON:
            raise PropsManifestError("completed 2026 outcomes cannot enter efficiency priors")
    if seen_teams != expected_teams:
        raise PropsManifestError("efficiency rows must cover both teams")


def _validate_team_td_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    game_id: str,
    expected_teams: set[str],
    forecast: datetime,
    kickoff: datetime,
) -> None:
    if len(rows) != 2:
        raise PropsManifestError("team_td_parameters must contain exactly two team rows")
    teams: set[str] = set()
    for row in rows:
        if str(row.get("game_id") or "") != game_id:
            raise PropsManifestError("team TD row game_id does not match opportunity game")
        team = normalize_team_code(_required_text(row, "team", "team TD row"))
        if team in teams:
            raise PropsManifestError(f"duplicate team TD row: {team}")
        teams.add(team)
        row_forecast = _aware(row.get("forecast_timestamp"), "team TD forecast_timestamp")
        horizon = _aware(row.get("feature_data_horizon"), "team TD feature_data_horizon")
        row_kickoff = _aware(row.get("kickoff_timestamp"), "team TD kickoff_timestamp")
        if horizon > row_forecast or row_forecast > forecast:
            raise PropsManifestError("team TD timestamps violate point-in-time ordering")
        if row_kickoff != kickoff:
            raise PropsManifestError("team TD kickoff timestamp disagrees with game spec")
        try:
            trained_through = int(row.get("prior_model_trained_through_season"))
        except (TypeError, ValueError) as exc:
            raise PropsManifestError(
                "team TD row requires prior_model_trained_through_season"
            ) from exc
        if trained_through > MAX_TRAINING_SEASON:
            raise PropsManifestError("completed 2026 outcomes cannot enter team TD priors")
    if teams != expected_teams:
        raise PropsManifestError("team TD rows do not cover both game teams")


def _validate_residual(
    residual: Mapping[str, Any],
    *,
    expected_teams: set[str],
) -> None:
    normalized = {normalize_team_code(key) for key in residual}
    if not expected_teams.issubset(normalized):
        raise PropsManifestError("residual_efficiency_by_team must cover both teams")


def _market_artifacts(
    market_snapshot: Mapping[str, Any],
    *,
    game_id: str,
    forecast: datetime,
    kickoff: datetime,
) -> list[dict[str, Any]]:
    artifacts = market_snapshot.get("market_artifacts")
    if not isinstance(artifacts, list):
        raise PropsManifestError("market snapshot must contain market_artifacts list")
    captured_raw = market_snapshot.get("captured_at_utc")
    if captured_raw is not None:
        captured = _aware(captured_raw, "market snapshot captured_at_utc")
        if captured > forecast:
            raise PropsManifestError("market snapshot cannot be newer than manifest forecast")
        if captured >= kickoff:
            raise PropsManifestError("market snapshot must be pregame")

    seen: set[tuple[str, str]] = set()
    output: list[dict[str, Any]] = []
    for raw in artifacts:
        if not isinstance(raw, Mapping):
            raise PropsManifestError("market artifact must be an object")
        row = dict(raw)
        if str(row.get("game_id") or "") != game_id:
            raise PropsManifestError("market artifact game_id does not match opportunity game")
        player_id = _required_text(row, "player_id", "market artifact")
        prop_type = _required_text(row, "prop_type", "market artifact")
        key = (player_id, prop_type)
        if key in seen:
            raise PropsManifestError(f"duplicate market artifact: {player_id}/{prop_type}")
        seen.add(key)
        if row.get("closing_evaluation") is not None:
            raise PropsManifestError("closing evaluation cannot enter prospective manifest")
        as_of = _aware(row.get("as_of_utc"), "market as_of_utc")
        if as_of > forecast:
            raise PropsManifestError("market artifact cannot be newer than manifest forecast")
        if as_of >= kickoff:
            raise PropsManifestError("market artifact must be pregame")
        output.append(row)
    return output


def assemble_manifest(
    *,
    game_spec: Mapping[str, Any],
    opportunity_projections: Sequence[Mapping[str, Any]],
    efficiency_player_parameters: Sequence[Mapping[str, Any]],
    team_td_parameters: Sequence[Mapping[str, Any]],
    residual_efficiency_by_team: Mapping[str, Any],
    market_snapshot: Mapping[str, Any],
    input_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    home = normalize_team_code(_required_text(game_spec, "home_team", "game spec"))
    away = normalize_team_code(_required_text(game_spec, "away_team", "game spec"))
    if home == away:
        raise PropsManifestError("home_team and away_team must differ")
    expected_teams = {home, away}

    forecast = _aware(game_spec.get("forecast_timestamp_utc"), "forecast_timestamp_utc")
    kickoff = _aware(game_spec.get("kickoff_utc"), "kickoff_utc")
    if forecast >= kickoff:
        raise PropsManifestError("forecast_timestamp_utc must be before kickoff_utc")

    projections = [dict(row) for row in opportunity_projections]
    efficiency = [dict(row) for row in efficiency_player_parameters]
    team_td = [dict(row) for row in team_td_parameters]
    residual = dict(residual_efficiency_by_team)
    game_id = _validate_projection_set(
        projections,
        expected_teams=expected_teams,
        forecast=forecast,
    )
    _validate_efficiency_rows(
        efficiency,
        game_id=game_id,
        expected_teams=expected_teams,
        forecast=forecast,
        kickoff=kickoff,
    )
    _validate_team_td_rows(
        team_td,
        game_id=game_id,
        expected_teams=expected_teams,
        forecast=forecast,
        kickoff=kickoff,
    )
    _validate_residual(residual, expected_teams=expected_teams)
    markets = _market_artifacts(
        market_snapshot,
        game_id=game_id,
        forecast=forecast,
        kickoff=kickoff,
    )

    manifest: dict[str, Any] = {
        "manifest_contract_version": MANIFEST_CONTRACT_VERSION,
        "research_only": True,
        "production_authorized": False,
        "game_id": game_id,
        "home_team": home,
        "away_team": away,
        "kickoff_utc": kickoff.isoformat(),
        "forecast_timestamp_utc": forecast.isoformat(),
        "opportunity_projections": projections,
        "efficiency_player_parameters": efficiency,
        "team_td_parameters": team_td,
        "residual_efficiency_by_team": residual,
        "market_artifacts": markets,
        "input_provenance": dict(input_provenance or {}),
    }
    for key in OPTIONAL_CONTROLS:
        if key in game_spec:
            manifest[key] = game_spec[key]
    return manifest
