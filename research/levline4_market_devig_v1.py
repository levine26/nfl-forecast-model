from __future__ import annotations

"""Deterministic two-way moneyline de-vig candidates for LevLine 4 research.

No outcomes are consumed here. These transforms operate only on the immutable raw
book prices already preserved by market-capture v2. For two-outcome books, the Shin
solution is algebraically equivalent to the additive margin-removal solution; it is
therefore labeled explicitly rather than treated as a distinct hidden-information
signal.
"""

from dataclasses import dataclass
import math
from typing import Any

import pandas as pd

from research.market_capture_v2 import american_implied, median_logit

PROPORTIONAL_CANDIDATE_ID = "L4-MKT-DEVIG-PROP-V1"
SHIN_TWO_WAY_CANDIDATE_ID = "L4-MKT-DEVIG-SHIN2-V1"
POWER_CANDIDATE_ID = "L4-MKT-DEVIG-POWER-V1"
MIN_BOOKS = 2


@dataclass(frozen=True)
class TwoWayDevig:
    first_raw_implied: float
    second_raw_implied: float
    overround: float
    proportional_first: float
    proportional_second: float
    shin_additive_first: float
    shin_additive_second: float
    power_first: float
    power_second: float
    power_exponent: float


def _valid_probability(value: float) -> bool:
    return math.isfinite(value) and 0.0 < value < 1.0


def _power_exponent(q1: float, q2: float, *, tolerance: float = 1e-13) -> float:
    """Solve q1**alpha + q2**alpha = 1 by monotone bisection."""
    if not (_valid_probability(q1) and _valid_probability(q2)):
        raise ValueError("power de-vig requires implied probabilities in (0, 1)")

    def objective(alpha: float) -> float:
        return q1**alpha + q2**alpha - 1.0

    lo = 1e-9
    hi = 64.0
    flo = objective(lo)
    fhi = objective(hi)
    if not (flo > 0.0 and fhi < 0.0):
        raise ValueError("could not bracket power de-vig exponent")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        fmid = objective(mid)
        if abs(fmid) <= tolerance:
            return mid
        if fmid > 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def two_way_devig(first_american: float, second_american: float) -> TwoWayDevig:
    q1 = float(american_implied(float(first_american)))
    q2 = float(american_implied(float(second_american)))
    booksum = q1 + q2
    if not math.isfinite(booksum) or booksum <= 0.0:
        raise ValueError("invalid two-way booksum")

    proportional_first = q1 / booksum
    proportional_second = q2 / booksum

    margin = booksum - 1.0
    # In a two-outcome market the Shin solution equals additive margin removal.
    shin_first = q1 - margin / 2.0
    shin_second = q2 - margin / 2.0
    if not (_valid_probability(shin_first) and _valid_probability(shin_second)):
        raise ValueError("two-way Shin/additive solution left the probability simplex")

    exponent = _power_exponent(q1, q2)
    power_first = q1**exponent
    power_second = q2**exponent
    total_power = power_first + power_second
    if not math.isclose(total_power, 1.0, rel_tol=0.0, abs_tol=1e-10):
        raise ValueError("power de-vig failed normalization")

    return TwoWayDevig(
        first_raw_implied=q1,
        second_raw_implied=q2,
        overround=margin,
        proportional_first=proportional_first,
        proportional_second=proportional_second,
        shin_additive_first=shin_first,
        shin_additive_second=shin_second,
        power_first=power_first,
        power_second=power_second,
        power_exponent=exponent,
    )


def book_method_probabilities(home_moneyline: float, away_moneyline: float) -> dict[str, Any]:
    result = two_way_devig(home_moneyline, away_moneyline)
    return {
        "raw_home_implied": result.first_raw_implied,
        "raw_away_implied": result.second_raw_implied,
        "overround": result.overround,
        "proportional_home_prob": result.proportional_first,
        "shin_two_way_home_prob": result.shin_additive_first,
        "power_home_prob": result.power_first,
        "power_exponent": result.power_exponent,
    }


def consensus_from_book_rows(book_rows: pd.DataFrame) -> dict[str, Any]:
    """Build method-specific robust consensus from one immutable capture batch.

    The caller is responsible for supplying book rows from one game/horizon/request
    timestamp. This function verifies that identity and sportsbook uniqueness rather
    than merging observations from different capture times.
    """
    required = {
        "game_id",
        "horizon",
        "request_timestamp_utc",
        "sportsbook_key",
        "home_moneyline",
        "away_moneyline",
    }
    missing = required - set(book_rows.columns)
    if book_rows.empty or missing:
        raise ValueError(f"book rows missing required fields: {sorted(missing)}")

    identity = book_rows[["game_id", "horizon", "request_timestamp_utc"]].astype(str)
    if len(identity.drop_duplicates()) != 1:
        raise ValueError("de-vig consensus requires one game/horizon/request batch")

    keys = book_rows["sportsbook_key"].astype(str).str.strip()
    if keys.eq("").any() or keys.duplicated().any():
        raise ValueError("sportsbook identities must be present and unique")
    if len(book_rows) < MIN_BOOKS:
        raise ValueError(f"de-vig consensus requires at least {MIN_BOOKS} books")

    proportional: list[float] = []
    shin_two_way: list[float] = []
    power: list[float] = []
    power_exponents: list[float] = []
    overrounds: list[float] = []

    for _, row in book_rows.iterrows():
        metrics = book_method_probabilities(row["home_moneyline"], row["away_moneyline"])
        proportional.append(float(metrics["proportional_home_prob"]))
        shin_two_way.append(float(metrics["shin_two_way_home_prob"]))
        power.append(float(metrics["power_home_prob"]))
        power_exponents.append(float(metrics["power_exponent"]))
        overrounds.append(float(metrics["overround"]))

    first = book_rows.iloc[0]
    return {
        "game_id": str(first["game_id"]),
        "horizon": str(first["horizon"]),
        "request_timestamp_utc": str(first["request_timestamp_utc"]),
        "source_count": int(len(book_rows)),
        "source_names": "|".join(sorted(keys.tolist())),
        "proportional_candidate_id": PROPORTIONAL_CANDIDATE_ID,
        "proportional_home_prob": float(median_logit(proportional)),
        "shin_candidate_id": SHIN_TWO_WAY_CANDIDATE_ID,
        "shin_two_way_home_prob": float(median_logit(shin_two_way)),
        "shin_two_way_note": "algebraically_equivalent_to_additive_for_two_outcomes",
        "power_candidate_id": POWER_CANDIDATE_ID,
        "power_home_prob": float(median_logit(power)),
        "power_exponent_min": float(min(power_exponents)),
        "power_exponent_max": float(max(power_exponents)),
        "overround_min": float(min(overrounds)),
        "overround_max": float(max(overrounds)),
        "completed_2026_outcomes_used": 0,
        "research_only": True,
        "production_authorized": False,
    }
