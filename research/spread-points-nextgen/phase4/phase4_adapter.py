from __future__ import annotations

"""Phase 4 authorization layer for the frozen Phase 3 candidate implementation.

This module does not change A0/B0/C0 scientific behavior.  It only replaces the
Phase-3-specific guards that deliberately prohibited 2025 with Phase-4 guards
that authorize historical target seasons through 2025 while continuing to fail
closed for completed 2026+ outcomes.  The frozen implementation/config hashes
are verified before the adapter may be entered.
"""

from contextlib import contextmanager
from pathlib import Path
from typing import Iterable

import pandas as pd

from ..phase3 import phase3_a0, phase3_b0, phase3_c0, phase3_data
from ..phase3.run_phase3 import _code_hash, _config_hash

FROZEN_IMPLEMENTATION_SHA256 = "5f148219527b07d85261d3f196ace97a5eb5646271d43596032a692389abc579"
FROZEN_CONFIG_SHA256 = "2c5cc1af74fc5f3955e44361b82b791710e4b63bbc69b0c15570617e2d86e543"
TRAINING_FLOOR = 2016
HOLDOUT_SEASON = 2025
COMPLETED_2026_FLOOR = 2026


class Phase4FirewallError(RuntimeError):
    pass


def verify_frozen_hashes() -> dict[str, str]:
    implementation = _code_hash()
    config = _config_hash()
    if implementation != FROZEN_IMPLEMENTATION_SHA256:
        raise Phase4FirewallError(
            f"frozen Phase 3 implementation hash drift: {implementation} != {FROZEN_IMPLEMENTATION_SHA256}"
        )
    if config != FROZEN_CONFIG_SHA256:
        raise Phase4FirewallError(
            f"frozen Phase 3 config hash drift: {config} != {FROZEN_CONFIG_SHA256}"
        )
    return {"implementation_sha256": implementation, "config_sha256": config}


def guard_phase4_target_seasons(seasons: Iterable[int]) -> tuple[int, ...]:
    vals = tuple(int(s) for s in seasons)
    if not vals:
        raise Phase4FirewallError("Phase 4 requires at least one target season")
    if any(s < TRAINING_FLOOR for s in vals):
        raise Phase4FirewallError("target season predates frozen 2016 training floor")
    bad = sorted(s for s in vals if s >= COMPLETED_2026_FLOOR)
    if bad:
        raise Phase4FirewallError(f"completed-2026-or-later outcomes remain prohibited: {bad}")
    if any(s > HOLDOUT_SEASON for s in vals):
        raise Phase4FirewallError(f"Phase 4 target exceeds 2025 holdout: {vals}")
    return vals


def assert_phase4_loaded_universe(frame: pd.DataFrame, *, season_col: str = "season") -> None:
    seasons = pd.to_numeric(frame[season_col], errors="coerce").dropna().astype(int)
    if seasons.empty:
        raise Phase4FirewallError("loaded universe has no seasons")
    if int(seasons.min()) < TRAINING_FLOOR:
        raise Phase4FirewallError("loaded universe predates frozen 2016 training floor")
    if (seasons >= COMPLETED_2026_FLOOR).any():
        seen = sorted(seasons[seasons >= COMPLETED_2026_FLOOR].unique().tolist())
        raise Phase4FirewallError(f"completed 2026+ source/outcome rows prohibited: {seen}")
    if int(seasons.max()) > HOLDOUT_SEASON:
        raise Phase4FirewallError("loaded universe exceeds the 2025 holdout")


def assert_phase4_prediction_receipt(frame: pd.DataFrame, candidate_id: str) -> None:
    required = {
        "game_id", "season", "week", "home_team", "away_team", "candidate_id",
        "outer_target_season", "train_through_season", "source_contract_version",
        "code_sha", "config_sha", "fallback_state",
    }
    missing = required - set(frame.columns)
    if missing:
        raise Phase4FirewallError(f"{candidate_id}: prediction receipt missing {sorted(missing)}")
    if not frame["candidate_id"].eq(candidate_id).all():
        raise Phase4FirewallError(f"{candidate_id}: candidate identity drift")
    seasons = pd.to_numeric(frame["season"], errors="coerce")
    if seasons.ge(COMPLETED_2026_FLOOR).any() or seasons.gt(HOLDOUT_SEASON).any():
        raise Phase4FirewallError(f"{candidate_id}: prediction escaped Phase 4 historical boundary")
    target = pd.to_numeric(frame["outer_target_season"], errors="coerce")
    train_through = pd.to_numeric(frame["train_through_season"], errors="coerce")
    if not (train_through < target).all():
        raise Phase4FirewallError(f"{candidate_id}: invalid prior-time training boundary")
    if not frame["code_sha"].astype(str).eq(FROZEN_IMPLEMENTATION_SHA256).all():
        raise Phase4FirewallError(f"{candidate_id}: implementation hash mismatch in prediction receipt")
    if not frame["config_sha"].astype(str).eq(FROZEN_CONFIG_SHA256).all():
        raise Phase4FirewallError(f"{candidate_id}: config hash mismatch in prediction receipt")


@contextmanager
def authorize_frozen_phase4_execution():
    """Temporarily authorize <=2025 execution without modifying Phase 3 source.

    Candidate modules imported the Phase 3 guard/receipt helpers into module globals,
    so the Phase 4 adapter replaces those references for the duration of the run.
    All estimator/tuning/data-state functions remain byte-for-byte frozen.
    """

    verify_frozen_hashes()
    patches = [
        (phase3_data, "assert_phase3_loaded_universe", assert_phase4_loaded_universe),
        (phase3_a0, "guard_phase3_target_seasons", guard_phase4_target_seasons),
        (phase3_a0, "assert_prediction_receipt", assert_phase4_prediction_receipt),
        (phase3_b0, "guard_phase3_target_seasons", guard_phase4_target_seasons),
        (phase3_b0, "assert_prediction_receipt", assert_phase4_prediction_receipt),
        (phase3_c0, "guard_phase3_target_seasons", guard_phase4_target_seasons),
        (phase3_c0, "assert_prediction_receipt", assert_phase4_prediction_receipt),
    ]
    originals: list[tuple[object, str, object]] = []
    try:
        for module, name, replacement in patches:
            originals.append((module, name, getattr(module, name)))
            setattr(module, name, replacement)
        yield
    finally:
        for module, name, original in reversed(originals):
            setattr(module, name, original)
