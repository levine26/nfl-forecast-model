from __future__ import annotations

"""Canonical point-in-time offensive player-state contract for LevLine Props.

This module is deliberately a data contract, not a player-value model. It keeps identity,
availability, role, and lagged opportunity evidence explicit so downstream opportunity,
efficiency, TD, simulation, market, and product lanes can consume the same leakage-safe
state.

Historical game participation may be used as lagged usage evidence for *later* games once
it was actually available. It must never be used to reconstruct pregame availability for
the game in which it occurred.
"""

from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from math import isfinite
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

import pandas as pd

OFFENSIVE_PLAYER_STATE_SCHEMA_NAME = "levline_props_offensive_player_state"
OFFENSIVE_PLAYER_STATE_SCHEMA_VERSION = 1
SUPPORTED_POSITIONS = frozenset({"QB", "RB", "WR", "TE"})


class IdentityResolution(StrEnum):
    UNIQUE = "unique"
    AMBIGUOUS = "ambiguous"
    UNRESOLVED = "unresolved"


class AvailabilityStatus(StrEnum):
    ACTIVE = "active"
    PROBABLE = "probable"
    QUESTIONABLE = "questionable"
    DOUBTFUL = "doubtful"
    OUT = "out"
    UNKNOWN = "unknown"


class AvailabilityHistorySupport(StrEnum):
    """Whether availability evidence can be replayed historically."""

    QUALIFIED_POINT_IN_TIME = "qualified_point_in_time"
    PROSPECTIVE_ONLY = "prospective_only"
    NONE = "none"


class AvailabilityEvidenceKind(StrEnum):
    OFFICIAL_INJURY_REPORT = "official_injury_report"
    OFFICIAL_INACTIVES = "official_inactives"
    TEAM_REPORT = "team_report"
    DEPTH_CHART = "depth_chart"
    PROJECTION = "projection"
    QUALIFIED_HISTORICAL_RECONSTRUCTION = "qualified_historical_reconstruction"
    FINAL_PARTICIPATION = "final_participation"


class SourceStatus(StrEnum):
    OBSERVED = "observed"
    PARTIAL = "partial"
    MISSING = "missing"
    PROSPECTIVE_ONLY = "prospective_only"


class ExpectedRole(StrEnum):
    QB_STARTER = "qb_starter"
    QB_BACKUP = "qb_backup"
    RB_LEAD = "rb_lead"
    RB_COMMITTEE = "rb_committee"
    RB_PASSING_DOWN = "rb_passing_down"
    PASS_CATCHER_PRIMARY = "pass_catcher_primary"
    PASS_CATCHER_SECONDARY = "pass_catcher_secondary"
    ROTATION = "rotation"
    UNKNOWN = "unknown"


def _require_aware(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")


def _clean_text(value: str, field_name: str) -> str:
    cleaned = str(value or "").strip()
    if not cleaned or cleaned.lower() in {"nan", "<na>", "none"}:
        raise ValueError(f"{field_name} must be non-empty")
    return cleaned


def _validate_nonnegative_optional(value: float | int | None, field_name: str) -> None:
    if value is None:
        return
    if not isfinite(float(value)) or float(value) < 0:
        raise ValueError(f"{field_name} must be finite and >= 0 when present")


def _validate_share_optional(value: float | None, field_name: str) -> None:
    if value is None:
        return
    if not isfinite(float(value)) or not 0.0 <= float(value) <= 1.0:
        raise ValueError(f"{field_name} must be between 0 and 1 when present")


@dataclass(frozen=True)
class PlayerIdentity:
    player_id: str
    player_name: str
    position: str
    team: str
    resolution: IdentityResolution = IdentityResolution.UNIQUE
    identity_source: str = "nflverse"

    def __post_init__(self) -> None:
        object.__setattr__(self, "player_id", _clean_text(self.player_id, "player_id"))
        object.__setattr__(self, "player_name", _clean_text(self.player_name, "player_name"))
        position = _clean_text(self.position, "position").upper()
        team = _clean_text(self.team, "team").upper()
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "team", team)
        if position not in SUPPORTED_POSITIONS:
            raise ValueError(f"Unsupported offensive prop position: {position}")
        if self.resolution is not IdentityResolution.UNIQUE:
            raise ValueError(
                f"Stable identity must resolve uniquely; got resolution={self.resolution.value}"
            )
        _clean_text(self.identity_source, "identity_source")


@dataclass(frozen=True)
class GameContext:
    game_id: str
    team: str
    opponent: str
    kickoff_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "game_id", _clean_text(self.game_id, "game_id"))
        team = _clean_text(self.team, "team").upper()
        opponent = _clean_text(self.opponent, "opponent").upper()
        object.__setattr__(self, "team", team)
        object.__setattr__(self, "opponent", opponent)
        if team == opponent:
            raise ValueError("team and opponent must differ")
        _require_aware(self.kickoff_at, "kickoff_at")


@dataclass(frozen=True)
class AvailabilityEvidence:
    status: AvailabilityStatus
    observed_at: datetime
    source: str
    evidence_kind: AvailabilityEvidenceKind
    history_support: AvailabilityHistorySupport
    active_probability: float | None = None
    uncertainty: str | None = None

    def __post_init__(self) -> None:
        _require_aware(self.observed_at, "availability.observed_at")
        _clean_text(self.source, "availability.source")
        if self.active_probability is not None:
            probability = float(self.active_probability)
            if not isfinite(probability) or not 0.0 <= probability <= 1.0:
                raise ValueError("availability.active_probability must be between 0 and 1")
        if self.evidence_kind is AvailabilityEvidenceKind.FINAL_PARTICIPATION:
            raise ValueError("Final participation cannot be used as pregame availability evidence")
        if (
            self.history_support is AvailabilityHistorySupport.QUALIFIED_POINT_IN_TIME
            and self.evidence_kind
            not in {
                AvailabilityEvidenceKind.OFFICIAL_INJURY_REPORT,
                AvailabilityEvidenceKind.OFFICIAL_INACTIVES,
                AvailabilityEvidenceKind.TEAM_REPORT,
                AvailabilityEvidenceKind.QUALIFIED_HISTORICAL_RECONSTRUCTION,
            }
        ):
            raise ValueError(
                "Qualified historical availability requires a point-in-time evidence kind"
            )


@dataclass(frozen=True)
class PriorUsageGame:
    """Observed opportunity state from a game completed before the forecast game.

    ``available_at`` is the earliest timestamp at which this normalized record was safe to
    consume. Missing source statistics remain ``None``; absence of data is never converted
    to zero.
    """

    game_id: str
    kickoff_at: datetime
    available_at: datetime
    source: str
    snaps: int | None = None
    snap_share: float | None = None
    routes: int | None = None
    route_participation: float | None = None
    carries: int | None = None
    rush_share: float | None = None
    targets: int | None = None
    target_share: float | None = None
    dropbacks: int | None = None
    qb_rush_attempts: int | None = None
    designed_rushes: int | None = None
    scrambles: int | None = None
    red_zone_carries: int | None = None
    goal_line_carries: int | None = None
    red_zone_targets: int | None = None
    end_zone_targets: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "game_id", _clean_text(self.game_id, "prior_usage.game_id"))
        _clean_text(self.source, "prior_usage.source")
        _require_aware(self.kickoff_at, "prior_usage.kickoff_at")
        _require_aware(self.available_at, "prior_usage.available_at")
        if self.available_at < self.kickoff_at:
            raise ValueError("prior_usage.available_at cannot precede that game's kickoff")
        for name in (
            "snaps", "routes", "carries", "targets", "dropbacks", "qb_rush_attempts",
            "designed_rushes", "scrambles", "red_zone_carries", "goal_line_carries",
            "red_zone_targets", "end_zone_targets",
        ):
            _validate_nonnegative_optional(getattr(self, name), f"prior_usage.{name}")
        for name in ("snap_share", "route_participation", "rush_share", "target_share"):
            _validate_share_optional(getattr(self, name), f"prior_usage.{name}")


_USAGE_METRICS = (
    "snaps", "snap_share", "routes", "route_participation", "carries", "rush_share",
    "targets", "target_share", "dropbacks", "qb_rush_attempts", "designed_rushes",
    "scrambles", "red_zone_carries", "goal_line_carries", "red_zone_targets",
    "end_zone_targets",
)


@dataclass(frozen=True)
class PriorUsageSummary:
    games: int
    first_game_id: str | None
    last_game_id: str | None
    metrics: Mapping[str, float | None]

    def as_flat_dict(self, prefix: str = "prior_") -> dict[str, Any]:
        values: dict[str, Any] = {
            f"{prefix}games": self.games,
            f"{prefix}first_game_id": self.first_game_id,
            f"{prefix}last_game_id": self.last_game_id,
        }
        values.update({f"{prefix}{key}_mean": value for key, value in self.metrics.items()})
        return values


def summarize_prior_usage(
    usage: Sequence[PriorUsageGame], *, max_games: int | None = None
) -> PriorUsageSummary:
    if max_games is not None and max_games <= 0:
        raise ValueError("max_games must be positive when provided")
    ordered = sorted(usage, key=lambda row: (row.kickoff_at, row.game_id))
    if max_games is not None:
        ordered = ordered[-max_games:]
    metrics: dict[str, float | None] = {}
    for name in _USAGE_METRICS:
        observed = [float(getattr(row, name)) for row in ordered if getattr(row, name) is not None]
        metrics[name] = fmean(observed) if observed else None
    return PriorUsageSummary(
        games=len(ordered),
        first_game_id=ordered[0].game_id if ordered else None,
        last_game_id=ordered[-1].game_id if ordered else None,
        metrics=metrics,
    )


@dataclass(frozen=True)
class OffensivePlayerState:
    schema_name: str
    schema_version: int
    player_id: str
    player_name: str
    position: str
    team: str
    opponent: str
    game_id: str
    kickoff_at: datetime
    forecast_at: datetime
    data_horizon_at: datetime
    expected_role: ExpectedRole
    role_source: str | None
    availability_status: AvailabilityStatus
    availability_probability: float | None
    availability_source: str | None
    availability_observed_at: datetime | None
    availability_history_support: AvailabilityHistorySupport
    availability_uncertainty: str | None
    source_status: SourceStatus
    prior_usage: tuple[PriorUsageGame, ...]
    prior_usage_summary: PriorUsageSummary
    missing_fields: tuple[str, ...]
    quality_flags: tuple[str, ...]
    critical_missing: bool

    def to_record(self, *, include_history: bool = False) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "position": self.position,
            "team": self.team,
            "opponent": self.opponent,
            "game_id": self.game_id,
            "kickoff_at": self.kickoff_at,
            "forecast_at": self.forecast_at,
            "data_horizon_at": self.data_horizon_at,
            "expected_role": self.expected_role.value,
            "role_source": self.role_source,
            "availability_status": self.availability_status.value,
            "availability_probability": self.availability_probability,
            "availability_source": self.availability_source,
            "availability_observed_at": self.availability_observed_at,
            "availability_history_support": self.availability_history_support.value,
            "availability_uncertainty": self.availability_uncertainty,
            "source_status": self.source_status.value,
            "missing_fields": list(self.missing_fields),
            "quality_flags": list(self.quality_flags),
            "critical_missing": self.critical_missing,
        }
        record.update(self.prior_usage_summary.as_flat_dict())
        if include_history:
            record["prior_usage_history"] = [asdict(row) for row in self.prior_usage]
        return record


OFFENSIVE_PLAYER_STATE_COLUMNS = (
    "schema_name", "schema_version", "player_id", "player_name", "position", "team",
    "opponent", "game_id", "kickoff_at", "forecast_at", "data_horizon_at",
    "expected_role", "role_source", "availability_status", "availability_probability",
    "availability_source", "availability_observed_at", "availability_history_support",
    "availability_uncertainty", "source_status", "prior_games", "prior_first_game_id",
    "prior_last_game_id", *tuple(f"prior_{metric}_mean" for metric in _USAGE_METRICS),
    "missing_fields", "quality_flags", "critical_missing",
)


def _unknown_availability(
    history_support: AvailabilityHistorySupport = AvailabilityHistorySupport.NONE,
) -> tuple[
    AvailabilityStatus, float | None, str | None, datetime | None,
    AvailabilityHistorySupport, str | None,
]:
    return (
        AvailabilityStatus.UNKNOWN, None, None, None, history_support,
        "availability_not_supported_at_horizon",
    )


def build_offensive_player_state(
    *,
    identity: PlayerIdentity,
    game: GameContext,
    forecast_at: datetime,
    data_horizon_at: datetime,
    expected_role: ExpectedRole = ExpectedRole.UNKNOWN,
    role_source: str | None = None,
    availability: AvailabilityEvidence | None = None,
    prior_usage: Iterable[PriorUsageGame] = (),
    historical_replay: bool = False,
    usage_window_games: int | None = None,
) -> OffensivePlayerState:
    """Build one fail-closed offensive player state.

    Every accepted datum must have been available by ``data_horizon_at``. Prospective-only
    availability is intentionally blanked during historical replay rather than backfilled
    from eventual participation.
    """
    _require_aware(forecast_at, "forecast_at")
    _require_aware(data_horizon_at, "data_horizon_at")
    if forecast_at >= game.kickoff_at:
        raise ValueError("forecast_at must be strictly before kickoff_at")
    if data_horizon_at > forecast_at:
        raise ValueError("data_horizon_at cannot be later than forecast_at")
    if identity.team != game.team:
        raise ValueError(f"identity team {identity.team} does not match game team {game.team}")

    usage_rows = tuple(prior_usage)
    seen_game_ids: set[str] = set()
    for row in usage_rows:
        if row.game_id == game.game_id:
            raise ValueError("Current-game usage is prohibited in pregame player state")
        if row.game_id in seen_game_ids:
            raise ValueError(f"Duplicate prior usage game_id: {row.game_id}")
        seen_game_ids.add(row.game_id)
        if row.kickoff_at >= game.kickoff_at:
            raise ValueError(
                f"Prior usage game {row.game_id} did not occur before forecast game kickoff"
            )
        if row.available_at > data_horizon_at:
            raise ValueError(f"Prior usage game {row.game_id} was not available by data horizon")

    quality_flags: list[str] = []
    if availability is not None and availability.observed_at > data_horizon_at:
        raise ValueError("Availability evidence was not known by data_horizon_at")

    if availability is None:
        availability_values = _unknown_availability()
        quality_flags.append("availability_missing")
    elif historical_replay and (
        availability.history_support is not AvailabilityHistorySupport.QUALIFIED_POINT_IN_TIME
    ):
        availability_values = _unknown_availability(AvailabilityHistorySupport.PROSPECTIVE_ONLY)
        quality_flags.append("availability_prospective_only_not_replayed")
    else:
        availability_values = (
            availability.status, availability.active_probability, availability.source,
            availability.observed_at, availability.history_support, availability.uncertainty,
        )

    (
        availability_status, availability_probability, availability_source,
        availability_observed_at, availability_history_support, availability_uncertainty,
    ) = availability_values

    if role_source is not None and not str(role_source).strip():
        raise ValueError("role_source must be non-empty when provided")
    if expected_role is ExpectedRole.UNKNOWN:
        quality_flags.append("expected_role_unknown")

    summary = summarize_prior_usage(usage_rows, max_games=usage_window_games)
    missing_fields: list[str] = []
    if availability_status is AvailabilityStatus.UNKNOWN:
        missing_fields.append("availability")
    if expected_role is ExpectedRole.UNKNOWN:
        missing_fields.append("expected_role")
    if summary.games == 0:
        missing_fields.append("prior_usage")
        quality_flags.append("prior_usage_missing")

    position_required = {
        "QB": ("dropbacks", "qb_rush_attempts"),
        "RB": ("carries", "routes", "targets"),
        "WR": ("routes", "targets"),
        "TE": ("routes", "targets"),
    }[identity.position]
    for metric in position_required:
        if summary.metrics.get(metric) is None:
            missing_fields.append(f"prior_{metric}")
            quality_flags.append(f"prior_{metric}_missing")

    observed_sources = bool(usage_rows) or availability_source is not None
    if not observed_sources:
        source_status = SourceStatus.MISSING
    elif availability_status is AvailabilityStatus.UNKNOWN:
        source_status = (
            SourceStatus.PROSPECTIVE_ONLY
            if "availability_prospective_only_not_replayed" in quality_flags
            else SourceStatus.PARTIAL
        )
    elif missing_fields:
        source_status = SourceStatus.PARTIAL
    else:
        source_status = SourceStatus.OBSERVED

    critical_missing = (
        "availability" in missing_fields
        or "expected_role" in missing_fields
        or "prior_usage" in missing_fields
    )
    return OffensivePlayerState(
        schema_name=OFFENSIVE_PLAYER_STATE_SCHEMA_NAME,
        schema_version=OFFENSIVE_PLAYER_STATE_SCHEMA_VERSION,
        player_id=identity.player_id,
        player_name=identity.player_name,
        position=identity.position,
        team=identity.team,
        opponent=game.opponent,
        game_id=game.game_id,
        kickoff_at=game.kickoff_at,
        forecast_at=forecast_at,
        data_horizon_at=data_horizon_at,
        expected_role=expected_role,
        role_source=role_source,
        availability_status=availability_status,
        availability_probability=availability_probability,
        availability_source=availability_source,
        availability_observed_at=availability_observed_at,
        availability_history_support=availability_history_support,
        availability_uncertainty=availability_uncertainty,
        source_status=source_status,
        prior_usage=tuple(sorted(usage_rows, key=lambda row: (row.kickoff_at, row.game_id))),
        prior_usage_summary=summary,
        missing_fields=tuple(dict.fromkeys(missing_fields)),
        quality_flags=tuple(dict.fromkeys(quality_flags)),
        critical_missing=critical_missing,
    )


def states_to_frame(states: Iterable[OffensivePlayerState]) -> pd.DataFrame:
    """Serialize states to the stable downstream tabular contract."""
    records = [state.to_record() for state in states]
    frame = pd.DataFrame(records, columns=OFFENSIVE_PLAYER_STATE_COLUMNS)
    validate_offensive_player_state_frame(frame)
    return frame


def validate_offensive_player_state_frame(frame: pd.DataFrame) -> None:
    """Validate a serialized player-state frame before downstream consumption."""
    missing = set(OFFENSIVE_PLAYER_STATE_COLUMNS) - set(frame.columns)
    if missing:
        raise ValueError(f"Offensive player-state frame missing columns: {sorted(missing)}")
    if frame.empty:
        return

    if frame[["game_id", "player_id"]].duplicated().any():
        raise ValueError("Offensive player-state frame has duplicate game_id/player_id rows")
    if not frame["position"].isin(SUPPORTED_POSITIONS).all():
        bad = sorted(set(frame.loc[~frame["position"].isin(SUPPORTED_POSITIONS), "position"]))
        raise ValueError(f"Unsupported positions in offensive player-state frame: {bad}")
    if not frame["schema_name"].eq(OFFENSIVE_PLAYER_STATE_SCHEMA_NAME).all():
        raise ValueError("Unexpected offensive player-state schema_name")
    if not frame["schema_version"].eq(OFFENSIVE_PLAYER_STATE_SCHEMA_VERSION).all():
        raise ValueError("Unexpected offensive player-state schema_version")

    for column in ("kickoff_at", "forecast_at", "data_horizon_at"):
        parsed = pd.to_datetime(frame[column], utc=True, errors="coerce")
        if parsed.isna().any():
            raise ValueError(f"{column} contains missing or unparseable timestamps")
    kickoff = pd.to_datetime(frame["kickoff_at"], utc=True)
    forecast = pd.to_datetime(frame["forecast_at"], utc=True)
    horizon = pd.to_datetime(frame["data_horizon_at"], utc=True)
    if forecast.ge(kickoff).any():
        raise ValueError("Serialized state contains forecast_at at/after kickoff")
    if horizon.gt(forecast).any():
        raise ValueError("Serialized state contains data_horizon_at after forecast_at")

    probability = pd.to_numeric(frame["availability_probability"], errors="coerce")
    supplied = frame["availability_probability"].notna()
    if supplied.any() and (~probability[supplied].between(0.0, 1.0)).any():
        raise ValueError("Serialized availability_probability must be in [0, 1]")
