from __future__ import annotations

"""Research-only sportsbook market engine for LevLine offensive player props.

The market is a benchmark, not an automatic betting signal. Live artifacts are
point-in-time: quotes observed after as_of_utc and evaluation-only closing
quotes are excluded from prospective summaries. Closing data can be attached
later for CLV/evaluation but is never promoted to an earlier forecast state.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import math
from statistics import median, pstdev
from typing import Iterable, Sequence


SCHEMA_VERSION = "levline.props.market.v1"
EPS = 1e-12

SUPPORTED_PROP_TYPES = {
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "passing_tds",
    "rushing_tds",
    "receiving_tds",
    "anytime_td",
}
BINARY_PROP_TYPES = {"anytime_td"}


def _nonempty(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} is required")
    return text


def _finite(value: object, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    return parsed


def parse_utc(value: object) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamps must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def american_to_decimal(odds: float) -> float:
    value = _finite(odds, "american odds")
    if -100.0 < value < 100.0:
        raise ValueError("American odds must be <= -100 or >= +100")
    return 1.0 + (100.0 / abs(value) if value < 0 else value / 100.0)


def decimal_to_american(odds: float) -> float:
    value = _finite(odds, "decimal odds")
    if value <= 1.0:
        raise ValueError("decimal odds must be > 1")
    if value >= 2.0:
        return (value - 1.0) * 100.0
    return -100.0 / (value - 1.0)


def decimal_to_implied(odds: float) -> float:
    value = _finite(odds, "decimal odds")
    if value <= 1.0:
        raise ValueError("decimal odds must be > 1")
    return 1.0 / value


def implied_to_decimal(probability: float) -> float:
    p = _finite(probability, "probability")
    if not 0.0 < p < 1.0:
        raise ValueError("probability must be inside (0, 1)")
    return 1.0 / p


def implied_to_american(probability: float) -> float:
    return decimal_to_american(implied_to_decimal(probability))


def american_to_implied(odds: float) -> float:
    return decimal_to_implied(american_to_decimal(odds))


def _power_exponent(q1: float, q2: float) -> float:
    if not (0.0 < q1 < 1.0 and 0.0 < q2 < 1.0):
        raise ValueError("power de-vig requires probabilities inside (0, 1)")

    def objective(alpha: float) -> float:
        return q1**alpha + q2**alpha - 1.0

    lo, hi = 1e-9, 64.0
    if not (objective(lo) > 0.0 and objective(hi) < 0.0):
        raise ValueError("could not bracket power de-vig exponent")
    for _ in range(200):
        mid = (lo + hi) / 2.0
        score = objective(mid)
        if abs(score) <= 1e-13:
            return mid
        if score > 0.0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def remove_vig_two_way(
    first_american: float,
    second_american: float,
    *,
    method: str = "proportional",
) -> dict[str, float | str]:
    """Return raw and no-vig probabilities for a genuine two-way market."""

    q1 = american_to_implied(first_american)
    q2 = american_to_implied(second_american)
    total = q1 + q2
    if total <= 0.0 or not math.isfinite(total):
        raise ValueError("invalid two-way market")
    overround = total - 1.0

    if method == "proportional":
        p1, p2 = q1 / total, q2 / total
    elif method == "additive":
        margin = overround / 2.0
        p1, p2 = q1 - margin, q2 - margin
        if not (0.0 < p1 < 1.0 and 0.0 < p2 < 1.0):
            raise ValueError("additive de-vig left probability simplex")
    elif method == "power":
        exponent = _power_exponent(q1, q2)
        p1, p2 = q1**exponent, q2**exponent
        norm = p1 + p2
        p1, p2 = p1 / norm, p2 / norm
    else:
        raise ValueError(f"unsupported de-vig method: {method}")

    return {
        "method": method,
        "first_raw_implied": q1,
        "second_raw_implied": q2,
        "overround": overround,
        "first_no_vig": p1,
        "second_no_vig": p2,
    }


def _logit(p: float) -> float:
    value = min(1.0 - EPS, max(EPS, float(p)))
    return math.log(value / (1.0 - value))


def _inv_logit(value: float) -> float:
    if value >= 0:
        z = math.exp(-value)
        return 1.0 / (1.0 + z)
    z = math.exp(value)
    return z / (1.0 + z)


def median_logit(probabilities: Iterable[float]) -> float:
    vals = [float(p) for p in probabilities if math.isfinite(float(p)) and 0.0 < float(p) < 1.0]
    if not vals:
        raise ValueError("consensus requires at least one valid probability")
    return _inv_logit(median(_logit(p) for p in vals))


@dataclass(frozen=True)
class PropMarketQuote:
    provider: str
    sportsbook_key: str
    sportsbook_title: str
    captured_at_utc: datetime
    player_id: str
    player: str
    game_id: str
    prop_type: str
    line: float | None = None
    over_american: float | None = None
    under_american: float | None = None
    yes_american: float | None = None
    no_american: float | None = None
    team: str | None = None
    opponent: str | None = None
    position: str | None = None
    kickoff_utc: datetime | None = None
    sportsbook_last_update_utc: datetime | None = None
    provider_event_id: str | None = None
    provider_market_key: str | None = None
    is_alternative_line: bool = False
    is_closing: bool = False
    related_market_group_id: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field in (
            "provider",
            "sportsbook_key",
            "sportsbook_title",
            "player_id",
            "player",
            "game_id",
            "prop_type",
        ):
            _nonempty(getattr(self, field), field)
        if self.prop_type not in SUPPORTED_PROP_TYPES:
            raise ValueError(f"unsupported prop_type: {self.prop_type}")

        captured = parse_utc(self.captured_at_utc)
        object.__setattr__(self, "captured_at_utc", captured)
        if self.kickoff_utc is not None:
            kickoff = parse_utc(self.kickoff_utc)
            object.__setattr__(self, "kickoff_utc", kickoff)
            if captured > kickoff:
                raise ValueError("post-kickoff quotes cannot enter pregame market artifacts")
        if self.sportsbook_last_update_utc is not None:
            updated = parse_utc(self.sportsbook_last_update_utc)
            object.__setattr__(self, "sportsbook_last_update_utc", updated)
            if updated > captured:
                raise ValueError("sportsbook last_update cannot be after capture time")

        if self.prop_type not in BINARY_PROP_TYPES:
            if self.line is None:
                raise ValueError("line is required for non-binary prop markets")
            _finite(self.line, "line")
        elif self.line is not None:
            _finite(self.line, "line")

        prices = (
            self.over_american,
            self.under_american,
            self.yes_american,
            self.no_american,
        )
        if all(price is None for price in prices):
            raise ValueError("at least one market price is required")
        for price in prices:
            if price is not None:
                american_to_decimal(price)

    @property
    def identity(self) -> tuple[str, str, str]:
        return (self.game_id, self.player_id, self.prop_type)

    def to_record(self, *, devig_method: str = "proportional") -> dict:
        record = asdict(self)
        for key in ("captured_at_utc", "kickoff_utc", "sportsbook_last_update_utc"):
            if record[key] is not None:
                record[key] = parse_utc(record[key]).isoformat()

        record.update(
            {
                "research_only": True,
                "production_authorized": False,
                "closing_evaluation_only": bool(self.is_closing),
                "cross_market_join_key": f"{self.game_id}:{self.player_id}",
                "over_decimal": None,
                "under_decimal": None,
                "over_raw_implied": None,
                "under_raw_implied": None,
                "over_no_vig": None,
                "under_no_vig": None,
                "yes_decimal": None,
                "no_decimal": None,
                "yes_raw_implied": None,
                "no_raw_implied": None,
                "yes_no_vig": None,
                "no_no_vig": None,
                "overround": None,
                "devig_method": None,
            }
        )

        if self.over_american is not None:
            record["over_decimal"] = american_to_decimal(self.over_american)
            record["over_raw_implied"] = american_to_implied(self.over_american)
        if self.under_american is not None:
            record["under_decimal"] = american_to_decimal(self.under_american)
            record["under_raw_implied"] = american_to_implied(self.under_american)
        if self.over_american is not None and self.under_american is not None:
            metrics = remove_vig_two_way(
                self.over_american,
                self.under_american,
                method=devig_method,
            )
            record["over_no_vig"] = metrics["first_no_vig"]
            record["under_no_vig"] = metrics["second_no_vig"]
            record["overround"] = metrics["overround"]
            record["devig_method"] = metrics["method"]

        if self.yes_american is not None:
            record["yes_decimal"] = american_to_decimal(self.yes_american)
            record["yes_raw_implied"] = american_to_implied(self.yes_american)
        if self.no_american is not None:
            record["no_decimal"] = american_to_decimal(self.no_american)
            record["no_raw_implied"] = american_to_implied(self.no_american)
        if self.yes_american is not None and self.no_american is not None:
            metrics = remove_vig_two_way(
                self.yes_american,
                self.no_american,
                method=devig_method,
            )
            record["yes_no_vig"] = metrics["first_no_vig"]
            record["no_no_vig"] = metrics["second_no_vig"]
            record["overround"] = metrics["overround"]
            record["devig_method"] = metrics["method"]
        return record


def _require_one_identity(quotes: Sequence[PropMarketQuote]) -> tuple[str, str, str]:
    if not quotes:
        raise ValueError("market summary requires at least one quote")
    identities = {quote.identity for quote in quotes}
    if len(identities) != 1:
        raise ValueError("market summary cannot mix game/player/prop identities")
    return next(iter(identities))


def _latest_primary_by_book(
    quotes: Sequence[PropMarketQuote],
    *,
    as_of_utc: datetime,
) -> list[PropMarketQuote]:
    eligible = [
        q
        for q in quotes
        if not q.is_closing
        and not q.is_alternative_line
        and q.captured_at_utc <= as_of_utc
    ]
    out: list[PropMarketQuote] = []
    for book in sorted({q.sportsbook_key for q in eligible}):
        rows = [q for q in eligible if q.sportsbook_key == book]
        latest_time = max(q.captured_at_utc for q in rows)
        latest = [q for q in rows if q.captured_at_utc == latest_time]
        keys = {(q.line, q.over_american, q.under_american, q.yes_american, q.no_american) for q in latest}
        if len(keys) == 1:
            out.append(latest[0])
    return out


def _latest_by_book_and_line(
    quotes: Sequence[PropMarketQuote],
    *,
    as_of_utc: datetime,
) -> list[PropMarketQuote]:
    eligible = [q for q in quotes if not q.is_closing and q.captured_at_utc <= as_of_utc]
    latest: dict[tuple[str, float | None], PropMarketQuote] = {}
    for quote in sorted(eligible, key=lambda q: q.captured_at_utc):
        latest[(quote.sportsbook_key, quote.line)] = quote
    return list(latest.values())


def _pava_nonincreasing(values: Sequence[float], weights: Sequence[float]) -> list[float]:
    if len(values) != len(weights) or not values:
        raise ValueError("PAVA requires equal non-empty values and weights")
    blocks: list[list[float]] = []
    for idx, (value, weight) in enumerate(zip(values, weights)):
        if weight <= 0:
            raise ValueError("PAVA weights must be positive")
        blocks.append([float(value), float(weight), float(idx), float(idx)])
        while len(blocks) >= 2 and blocks[-2][0] < blocks[-1][0]:
            right = blocks.pop()
            left = blocks.pop()
            total_w = left[1] + right[1]
            mean = (left[0] * left[1] + right[0] * right[1]) / total_w
            blocks.append([mean, total_w, left[2], right[3]])
    out = [0.0] * len(values)
    for mean, _weight, start, end in blocks:
        for idx in range(int(start), int(end) + 1):
            out[idx] = mean
    return out


def market_survival_points(
    quotes: Sequence[PropMarketQuote],
    *,
    as_of_utc: object,
    devig_method: str = "proportional",
) -> list[dict]:
    """Approximate P(stat > line) from available two-way primary/alternate lines."""

    as_of = parse_utc(as_of_utc)
    _require_one_identity(quotes)
    latest = _latest_by_book_and_line(quotes, as_of_utc=as_of)
    by_line: dict[float, list[float]] = {}
    source_books: dict[float, set[str]] = {}
    for quote in latest:
        if quote.line is None or quote.over_american is None or quote.under_american is None:
            continue
        record = quote.to_record(devig_method=devig_method)
        probability = record["over_no_vig"]
        if probability is None:
            continue
        line = float(quote.line)
        by_line.setdefault(line, []).append(float(probability))
        source_books.setdefault(line, set()).add(quote.sportsbook_key)
    if not by_line:
        return []

    lines = sorted(by_line)
    raw = [median_logit(by_line[line]) for line in lines]
    weights = [float(len(source_books[line])) for line in lines]
    projected = _pava_nonincreasing(raw, weights)
    return [
        {
            "line": line,
            "raw_consensus_p_over": raw[idx],
            "monotone_p_over": projected[idx],
            "source_count": int(weights[idx]),
            "source_books": sorted(source_books[line]),
        }
        for idx, line in enumerate(lines)
    ]


def survival_probability_at(points: Sequence[dict], line: float) -> float | None:
    if not points:
        return None
    x = float(line)
    ordered = sorted(points, key=lambda row: float(row["line"]))
    for row in ordered:
        if math.isclose(float(row["line"]), x, abs_tol=1e-12):
            return float(row["monotone_p_over"])
    if x < float(ordered[0]["line"]) or x > float(ordered[-1]["line"]):
        return None
    for left, right in zip(ordered, ordered[1:]):
        x0, x1 = float(left["line"]), float(right["line"])
        if x0 < x < x1:
            p0 = float(left["monotone_p_over"])
            p1 = float(right["monotone_p_over"])
            weight = (x - x0) / (x1 - x0)
            return p0 + weight * (p1 - p0)
    return None


def best_available_price(
    quotes: Sequence[PropMarketQuote],
    *,
    side: str,
    as_of_utc: object,
    line: float | None = None,
) -> dict | None:
    as_of = parse_utc(as_of_utc)
    _require_one_identity(quotes)
    latest = _latest_by_book_and_line(quotes, as_of_utc=as_of)
    field = {
        "over": "over_american",
        "under": "under_american",
        "yes": "yes_american",
        "no": "no_american",
    }.get(side)
    if field is None:
        raise ValueError("side must be over, under, yes, or no")

    candidates = []
    for quote in latest:
        if line is not None and (
            quote.line is None
            or not math.isclose(float(quote.line), float(line), abs_tol=1e-12)
        ):
            continue
        price = getattr(quote, field)
        if price is None:
            continue
        candidates.append((american_to_decimal(price), quote, float(price)))
    if not candidates:
        return None
    decimal, quote, american = max(candidates, key=lambda row: row[0])
    return {
        "sportsbook_key": quote.sportsbook_key,
        "sportsbook_title": quote.sportsbook_title,
        "american": american,
        "decimal": decimal,
        "line": quote.line,
        "captured_at_utc": quote.captured_at_utc.isoformat(),
    }


def _same_threshold(first: PropMarketQuote, last: PropMarketQuote) -> bool:
    if first.line is None and last.line is None:
        return True
    if first.line is None or last.line is None:
        return False
    return math.isclose(float(first.line), float(last.line), abs_tol=1e-12)


def _price_movement(
    first_price: float | None,
    last_price: float | None,
    *,
    comparable: bool,
) -> dict[str, float | None]:
    if not comparable or first_price is None or last_price is None:
        return {"decimal": None, "raw_implied_pp": None}
    opening_decimal = american_to_decimal(first_price)
    current_decimal = american_to_decimal(last_price)
    opening_implied = american_to_implied(first_price)
    current_implied = american_to_implied(last_price)
    return {
        "decimal": current_decimal - opening_decimal,
        "raw_implied_pp": 100.0 * (current_implied - opening_implied),
    }


def movement_summary(
    quotes: Sequence[PropMarketQuote],
    *,
    as_of_utc: object,
) -> dict:
    as_of = parse_utc(as_of_utc)
    _require_one_identity(quotes)
    eligible = [
        q for q in quotes
        if not q.is_closing and not q.is_alternative_line and q.captured_at_utc <= as_of
    ]
    per_book = []
    opening_lines: list[float] = []
    current_lines: list[float] = []
    for book in sorted({q.sportsbook_key for q in eligible}):
        rows = sorted(
            (q for q in eligible if q.sportsbook_key == book),
            key=lambda q: q.captured_at_utc,
        )
        if not rows:
            continue
        first, last = rows[0], rows[-1]
        if first.line is not None:
            opening_lines.append(float(first.line))
        if last.line is not None:
            current_lines.append(float(last.line))

        comparable = _same_threshold(first, last)
        over_move = _price_movement(
            first.over_american,
            last.over_american,
            comparable=comparable,
        )
        under_move = _price_movement(
            first.under_american,
            last.under_american,
            comparable=comparable,
        )
        yes_move = _price_movement(
            first.yes_american,
            last.yes_american,
            comparable=comparable,
        )
        no_move = _price_movement(
            first.no_american,
            last.no_american,
            comparable=comparable,
        )
        per_book.append(
            {
                "sportsbook_key": book,
                "opening_timestamp_utc": first.captured_at_utc.isoformat(),
                "current_timestamp_utc": last.captured_at_utc.isoformat(),
                "opening_line": first.line,
                "current_line": last.line,
                "line_movement": (
                    None
                    if first.line is None or last.line is None
                    else float(last.line) - float(first.line)
                ),
                "price_movement_comparable": comparable,
                "opening_over_american": first.over_american,
                "current_over_american": last.over_american,
                "over_price_movement_decimal": over_move["decimal"],
                "over_raw_implied_movement_pp": over_move["raw_implied_pp"],
                "opening_under_american": first.under_american,
                "current_under_american": last.under_american,
                "under_price_movement_decimal": under_move["decimal"],
                "under_raw_implied_movement_pp": under_move["raw_implied_pp"],
                "opening_yes_american": first.yes_american,
                "current_yes_american": last.yes_american,
                "yes_price_movement_decimal": yes_move["decimal"],
                "yes_raw_implied_movement_pp": yes_move["raw_implied_pp"],
                "opening_no_american": first.no_american,
                "current_no_american": last.no_american,
                "no_price_movement_decimal": no_move["decimal"],
                "no_raw_implied_movement_pp": no_move["raw_implied_pp"],
            }
        )
    opening = median(opening_lines) if opening_lines else None
    current = median(current_lines) if current_lines else None
    return {
        "consensus_opening_line": opening,
        "consensus_current_line": current,
        "consensus_line_movement": None if opening is None or current is None else current - opening,
        "per_book": per_book,
    }


def _best_price_from_quotes(
    quotes: Sequence[PropMarketQuote],
    *,
    side: str,
    line: float | None = None,
) -> dict | None:
    field = {
        "over": "over_american",
        "under": "under_american",
        "yes": "yes_american",
        "no": "no_american",
    }.get(side)
    if field is None:
        raise ValueError("side must be over, under, yes, or no")
    candidates = []
    for quote in quotes:
        if line is not None and (
            quote.line is None
            or not math.isclose(float(quote.line), float(line), abs_tol=1e-12)
        ):
            continue
        price = getattr(quote, field)
        if price is None:
            continue
        candidates.append((american_to_decimal(price), quote, float(price)))
    if not candidates:
        return None
    decimal, quote, american = max(candidates, key=lambda row: row[0])
    return {
        "sportsbook_key": quote.sportsbook_key,
        "sportsbook_title": quote.sportsbook_title,
        "american": american,
        "decimal": decimal,
        "line": quote.line,
        "captured_at_utc": quote.captured_at_utc.isoformat(),
    }


def _closing_evaluation(
    quotes: Sequence[PropMarketQuote],
    *,
    devig_method: str,
    evaluation_as_of_utc: datetime,
) -> dict | None:
    closing = [
        q
        for q in quotes
        if q.is_closing
        and not q.is_alternative_line
        and q.captured_at_utc <= evaluation_as_of_utc
    ]
    if not closing:
        return None

    latest: dict[str, PropMarketQuote] = {}
    for quote in sorted(closing, key=lambda q: q.captured_at_utc):
        latest[quote.sportsbook_key] = quote
    rows = list(latest.values())
    records = [q.to_record(devig_method=devig_method) for q in rows]
    lines = [float(q.line) for q in rows if q.line is not None]
    closing_line = median(lines) if lines else None

    exact_line_over_probs = [
        float(record["over_no_vig"])
        for quote, record in zip(rows, records)
        if closing_line is not None
        and quote.line is not None
        and math.isclose(float(quote.line), float(closing_line), abs_tol=1e-12)
        and record["over_no_vig"] is not None
    ]
    yes_probs = [
        float(record["yes_no_vig"])
        for record in records
        if record["yes_no_vig"] is not None
    ]

    return {
        "evaluation_only": True,
        "evaluation_as_of_utc": evaluation_as_of_utc.isoformat(),
        "source_count": len(rows),
        "sportsbooks": sorted(q.sportsbook_key for q in rows),
        "closing_line": closing_line,
        "closing_no_vig_p_over": (
            median_logit(exact_line_over_probs) if exact_line_over_probs else None
        ),
        "closing_no_vig_probability": median_logit(yes_probs) if yes_probs else None,
        "best_closing_over_price": (
            None
            if closing_line is None
            else _best_price_from_quotes(rows, side="over", line=closing_line)
        ),
        "best_closing_under_price": (
            None
            if closing_line is None
            else _best_price_from_quotes(rows, side="under", line=closing_line)
        ),
        "best_closing_yes_price": _best_price_from_quotes(rows, side="yes"),
        "best_closing_no_price": _best_price_from_quotes(rows, side="no"),
        "individual_books": records,
        "latest_capture_utc": max(q.captured_at_utc for q in rows).isoformat(),
    }


def build_market_artifact(
    quotes: Sequence[PropMarketQuote],
    *,
    as_of_utc: object,
    devig_method: str = "proportional",
    include_closing_evaluation: bool = False,
    evaluation_as_of_utc: object | None = None,
) -> dict:
    """Build the immutable point-in-time artifact consumed by simulation/product."""

    game_id, player_id, prop_type = _require_one_identity(quotes)
    as_of = parse_utc(as_of_utc)
    eligible = [q for q in quotes if not q.is_closing and q.captured_at_utc <= as_of]
    if not eligible:
        raise ValueError("no eligible pre-as-of market quotes")

    primaries = _latest_primary_by_book(eligible, as_of_utc=as_of)
    primary_records = [q.to_record(devig_method=devig_method) for q in primaries]
    lines = [float(q.line) for q in primaries if q.line is not None]
    consensus_line = median(lines) if lines else None

    survival = market_survival_points(eligible, as_of_utc=as_of, devig_method=devig_method)
    consensus_over = (
        None if consensus_line is None else survival_probability_at(survival, float(consensus_line))
    )
    consensus_under = None if consensus_over is None else 1.0 - consensus_over

    binary_probs = [
        float(row["yes_no_vig"])
        for row in primary_records
        if row.get("yes_no_vig") is not None
    ]
    consensus_binary = median_logit(binary_probs) if binary_probs else None

    if consensus_over is not None:
        quality_state = "multi_book_two_way" if len(primaries) >= 2 else "single_book_two_way"
    elif consensus_binary is not None:
        quality_state = (
            "multi_book_binary_two_way"
            if len(primaries) >= 2
            else "single_book_binary_two_way"
        )
    elif primaries:
        quality_state = "one_sided_or_incomplete"
    else:
        quality_state = "alternatives_only"

    market_data_quality = {
        "state": quality_state,
        "primary_sportsbook_count": len(primaries),
        "survival_threshold_count": len(survival),
        "two_way_probability_available": bool(
            consensus_over is not None or consensus_binary is not None
        ),
        "has_primary_line": consensus_line is not None,
    }

    summary = {
        "schema_version": SCHEMA_VERSION,
        "research_only": True,
        "production_authorized": False,
        "market_is_benchmark_not_edge_label": True,
        "as_of_utc": as_of.isoformat(),
        "game_id": game_id,
        "player_id": player_id,
        "player": eligible[0].player,
        "team": eligible[0].team,
        "opponent": eligible[0].opponent,
        "position": eligible[0].position,
        "prop_type": prop_type,
        "cross_market_join_key": f"{game_id}:{player_id}",
        "related_market_group_id": eligible[0].related_market_group_id,
        "consensus_line": consensus_line,
        "consensus_no_vig_p_over": consensus_over,
        "consensus_no_vig_p_under": consensus_under,
        "consensus_no_vig_probability": consensus_binary,
        "consensus_probability_method": (
            "market_survival_at_consensus_line"
            if consensus_over is not None
            else ("median_logit_binary_two_way" if consensus_binary is not None else None)
        ),
        "market_data_quality": market_data_quality,
        "sportsbook_count": len(primaries),
        "sportsbooks": sorted(q.sportsbook_key for q in primaries),
        "line_min": min(lines) if lines else None,
        "line_max": max(lines) if lines else None,
        "line_range": max(lines) - min(lines) if len(lines) >= 2 else (0.0 if lines else None),
        "line_stddev": pstdev(lines) if len(lines) >= 2 else (0.0 if lines else None),
        "individual_books": primary_records,
        "alternative_line_survival": survival,
        "best_over_price": (
            None
            if consensus_line is None
            else best_available_price(eligible, side="over", as_of_utc=as_of, line=consensus_line)
        ),
        "best_under_price": (
            None
            if consensus_line is None
            else best_available_price(eligible, side="under", as_of_utc=as_of, line=consensus_line)
        ),
        "best_yes_price": best_available_price(eligible, side="yes", as_of_utc=as_of),
        "best_no_price": best_available_price(eligible, side="no", as_of_utc=as_of),
        "movement": movement_summary(eligible, as_of_utc=as_of),
        "closing_evaluation": None,
    }
    if include_closing_evaluation:
        if evaluation_as_of_utc is None:
            raise ValueError(
                "evaluation_as_of_utc is required when closing evaluation is requested"
            )
        evaluation_as_of = parse_utc(evaluation_as_of_utc)
        if evaluation_as_of < as_of:
            raise ValueError("evaluation_as_of_utc cannot precede forecast as_of_utc")
        summary["closing_evaluation"] = _closing_evaluation(
            quotes,
            devig_method=devig_method,
            evaluation_as_of_utc=evaluation_as_of,
        )
    return summary


def compare_levline_to_market(
    market: dict,
    *,
    levline_fair_line: float | None = None,
    levline_p_over: float | None = None,
    levline_p_under: float | None = None,
    levline_probability: float | None = None,
) -> dict:
    """Create product-safe LevLine-vs-market deltas without declaring a betting edge."""

    out = {
        "market_line": market.get("consensus_line"),
        "levline_fair_line": levline_fair_line,
        "line_difference": None,
        "levline_p_over": levline_p_over,
        "market_no_vig_p_over": market.get("consensus_no_vig_p_over"),
        "probability_difference_over_pp": None,
        "levline_p_under": levline_p_under,
        "market_no_vig_p_under": market.get("consensus_no_vig_p_under"),
        "probability_difference_under_pp": None,
        "levline_fair_over_american": None,
        "levline_fair_under_american": None,
        "best_market_over": market.get("best_over_price"),
        "best_market_under": market.get("best_under_price"),
        "levline_probability": levline_probability,
        "market_no_vig_probability": market.get("consensus_no_vig_probability"),
        "probability_difference_pp": None,
        "levline_fair_american": None,
        "best_market_yes": market.get("best_yes_price"),
        "research_only": True,
        "bet_recommendation": None,
    }
    if levline_fair_line is not None and market.get("consensus_line") is not None:
        out["line_difference"] = float(levline_fair_line) - float(market["consensus_line"])
    if levline_p_over is not None:
        p = _finite(levline_p_over, "levline_p_over")
        out["levline_fair_over_american"] = implied_to_american(p)
        if out["market_no_vig_p_over"] is not None:
            out["probability_difference_over_pp"] = 100.0 * (
                p - float(out["market_no_vig_p_over"])
            )
    if levline_p_under is not None:
        p = _finite(levline_p_under, "levline_p_under")
        out["levline_fair_under_american"] = implied_to_american(p)
        if out["market_no_vig_p_under"] is not None:
            out["probability_difference_under_pp"] = 100.0 * (
                p - float(out["market_no_vig_p_under"])
            )
    if levline_probability is not None:
        p = _finite(levline_probability, "levline_probability")
        out["levline_fair_american"] = implied_to_american(p)
        if out["market_no_vig_probability"] is not None:
            out["probability_difference_pp"] = 100.0 * (
                p - float(out["market_no_vig_probability"])
            )
    return out


def closing_line_value(
    *,
    captured_line: float,
    closing_line: float,
    side: str,
) -> float:
    """Side-aware threshold CLV. Positive means the captured threshold beat close."""

    if side == "over":
        return float(closing_line) - float(captured_line)
    if side == "under":
        return float(captured_line) - float(closing_line)
    raise ValueError("side must be over or under")


def closing_price_value(
    *,
    captured_american: float,
    closing_american: float,
) -> float:
    """Same-threshold price CLV in decimal-odds units.

    Positive means the captured price offered a larger payout than the closing
    price for the identical outcome and threshold. Callers must not use this
    across different lines; line movement is handled separately.
    """

    return american_to_decimal(captured_american) - american_to_decimal(closing_american)
