"""Sportsbook contract normalization and exact net-return arithmetic.

All monetary results are in dollars per $1 staked.  Pushes return stake.
Neither vig-free prices nor implied probabilities are forecasts of true outcomes.
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from math import isfinite, log
from typing import Literal

Market = Literal['moneyline', 'spread', 'total', 'player_td', 'player_prop']


def odds_multiple(american: int) -> float:
    if isinstance(american, bool) or not isinstance(american, int) or abs(american) < 100:
        raise ValueError('American odds must be integer with abs >= 100')
    return american / 100.0 if american > 0 else 100.0 / (-american)


def implied_probability(american: int) -> float:
    return 1.0 / (1.0 + odds_multiple(american))


def american_from_probability(p: float) -> float:
    if not (0 < p < 1 and isfinite(p)):
        raise ValueError('probability must be strictly in (0,1)')
    return -100.0 * p / (1.0 - p) if p >= 0.5 else 100.0 * (1.0 - p) / p


def proportional_devig(two_way_prices: dict[str, int]) -> dict[str, float]:
    if len(two_way_prices) != 2:
        raise ValueError('only two-way markets supported')
    raw = {k: implied_probability(v) for k, v in two_way_prices.items()}
    total = sum(raw.values())
    if total < 1:
        raise ValueError('underround/arbitrage quotes require separate handling')
    return {k: p / total for k, p in raw.items()}


def expected_net(pwin: float, ppush: float, american: int) -> float:
    if not all(isfinite(v) for v in (pwin, ppush)) or pwin < 0 or ppush < 0 or pwin + ppush > 1 + 1e-10:
        raise ValueError('invalid win/push probability')
    ploss = max(0., 1. - pwin - ppush)
    return pwin * odds_multiple(american) - ploss


def quote_time(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('timestamps must have an explicit timezone')
    return dt.astimezone(timezone.utc)


@dataclass(frozen=True)
class BookQuote:
    id: str
    game_id: str
    market: Market
    selection: str
    american: int
    observed_utc: str
    source: str
    kickoff_utc: str
    side: str = ''
    line: float | None = None
    player_id: str = ''
    stat: str = ''
    bookmaker: str = ''
    # 'two_way_push' is explicit for NFL regular-season games that end tied.
    moneyline_tie: Literal['two_way_push', 'three_way'] = 'two_way_push'

    def validate(self, decision_utc: str, max_quote_age_seconds: int = 1800) -> None:
        if not self.id or not self.game_id or not self.source or not self.selection or not self.bookmaker:
            raise ValueError('quote lacks identity / source / bookmaker')
        odds_multiple(self.american)
        now, observed, kickoff = map(quote_time, (decision_utc, self.observed_utc, self.kickoff_utc))
        if observed > now or now >= kickoff or observed >= kickoff:
            raise ValueError('future/post-kickoff quote or post-kickoff decision')
        if (now - observed).total_seconds() > max_quote_age_seconds:
            raise ValueError('quote too stale')
        if self.market in ('spread', 'total', 'player_prop') and (self.line is None or not isfinite(self.line)):
            raise ValueError('numeric line required')
        if self.market == 'moneyline' and self.side not in ('home', 'away', 'tie'):
            raise ValueError('invalid moneyline side')
        if self.market == 'moneyline' and self.moneyline_tie == 'three_way' and self.side not in ('home','away','tie'):
            raise ValueError('invalid three-way selection')
        if self.market == 'spread' and self.side not in ('home','away'):
            raise ValueError('invalid spread side')
        if self.market == 'total' and self.side not in ('over','under'):
            raise ValueError('invalid total side')
        if self.market in ('player_td','player_prop') and not self.player_id:
            raise ValueError('player ID required')
        if self.market == 'player_prop' and (self.side not in ('over','under') or not self.stat):
            raise ValueError('player prop requires stat + over/under')


def cash_profit(status: Literal['win','loss','push'], american: int, stake: float) -> float:
    if not isfinite(stake) or stake < 0:
        raise ValueError('invalid stake')
    return {'win': stake * odds_multiple(american), 'loss': -stake, 'push': 0.0}[status]


def fractional_kelly(pwin: float, ploss: float, american: int, fraction: float = 0.125) -> float:
    """Positive Kelly fraction of bankroll. Not a bet recommendation without calibration."""
    if not 0 <= pwin <= 1 or not 0 <= ploss <= 1 or pwin + ploss > 1 + 1e-10:
        raise ValueError('invalid probabilities')
    if not 0 <= fraction <= 1:
        raise ValueError('invalid fraction')
    b = odds_multiple(american)
    return fraction * max(0., (b * pwin - ploss) / b)