"""Game/player event settlement and sportsbook-ticket mechanics.

Teaser pushes vary by sportsbook; unknown settlement is a hard error.
Same-game tickets must be priced using a *joint* outcome distribution.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from itertools import combinations
from math import isfinite
from typing import Literal
from .pricing import BookQuote, odds_multiple

Result = Literal['win','push','loss']


@dataclass(frozen=True)
class GameResult:
    home_points: int
    away_points: int
    player_tds: dict[str, int] = field(default_factory=dict)
    player_stats: dict[str, dict[str, float]] = field(default_factory=dict)

    def __post_init__(self):
        if any(isinstance(n,bool) or not isinstance(n,int) or n < 0 for n in (self.home_points, self.away_points)):
            raise ValueError('scores must be nonnegative integers')


def grade(quote: BookQuote, result: GameResult) -> Result:
    m = result.home_points - result.away_points
    if quote.market == 'moneyline':
        if m == 0:
            return 'push' if quote.moneyline_tie == 'two_way_push' else ('win' if quote.side == 'tie' else 'loss')
        winner = 'home' if m > 0 else 'away'
        return 'win' if quote.side == winner else 'loss'
    if quote.market == 'spread':
        diff = (m if quote.side == 'home' else -m) + quote.line
    elif quote.market == 'total':
        diff = result.home_points + result.away_points - quote.line
        if quote.side == 'under': diff = -diff
    elif quote.market == 'player_td':
        if quote.player_id not in result.player_tds: raise ValueError('TD result missing for player')
        if quote.side not in ('yes','no'): raise ValueError('player TD requires yes/no')
        yes = result.player_tds[quote.player_id] >= 1
        return 'win' if yes == (quote.side == 'yes') else 'loss'
    elif quote.market == 'player_prop':
        if quote.player_id not in result.player_stats or quote.stat not in result.player_stats[quote.player_id]:
            raise ValueError('player prop result missing for player/stat')
        diff = result.player_stats[quote.player_id][quote.stat] - quote.line
        if quote.side == 'under': diff = -diff
    else:
        raise ValueError('unknown market')
    return 'win' if diff > 1e-9 else ('loss' if diff < -1e-9 else 'push')


@dataclass(frozen=True)
class Ticket:
    id: str
    legs: tuple[BookQuote,...]
    american: int
    stake: float
    kind: Literal['straight','parlay','teaser'] = 'straight'
    push_policy: Literal['unknown','lose_ticket','void_ticket','reprice_from_legs'] = 'unknown'
    teaser_points: float = 0.0

    def __post_init__(self):
        if not self.legs or not isfinite(self.stake) or self.stake < 0:
            raise ValueError('invalid ticket')
        if len({q.id for q in self.legs}) != len(self.legs):
            raise ValueError('duplicate leg identity')
        odds_multiple(self.american)
        if self.kind == 'straight' and len(self.legs) != 1:
            raise ValueError('straight bet must be one leg')
        if self.kind == 'teaser':
            if not 2 <= len(self.legs) <= 10 or self.teaser_points <= 0:
                raise ValueError('invalid teaser size/points')
            if any(q.market != 'spread' for q in self.legs):
                raise ValueError('teaser must use spreads')
            if len({q.game_id for q in self.legs}) != len(self.legs):
                raise ValueError('teasers with same game unsupported')


def ticket_profit(ticket:Ticket, results:dict[str,GameResult]) -> float:
    statuses=[]
    for q in ticket.legs:
        if q.game_id not in results: raise ValueError('missing outcome')
        if ticket.kind=='teaser':
            from dataclasses import replace
            q=replace(q,line=q.line+ticket.teaser_points)
        statuses.append(grade(q,results[q.game_id]))
    if 'loss' in statuses:
        return -ticket.stake
    if all(s=='win' for s in statuses):
        return ticket.stake*odds_multiple(ticket.american)
    if ticket.kind == 'straight':
        return 0.0
    if ticket.push_policy == 'unknown':
        raise ValueError('sportsbook push policy not documented; cannot price')
    if ticket.push_policy == 'lose_ticket':
        return -ticket.stake
    if ticket.push_policy == 'void_ticket':
        return 0.0
    if ticket.push_policy == 'reprice_from_legs':
        # Only ordinary independent-leg parlays with independently quoted odds.
        # Teaser ticket odds CANNOT be repriced as products of straight prices.
        if ticket.kind == 'teaser':
            raise ValueError('teaser requires book-supplied repricing schedule')
        profit_multiple=1.0
        for q,s in zip(ticket.legs,statuses):
            if s == 'win': profit_multiple*=1+odds_multiple(q.american)
        return ticket.stake*(profit_multiple-1)
    raise ValueError('unrecognized push rule')


def round_robin(legs:tuple[BookQuote,...], size:int, stake_each:float, *, push_policy:str='unknown')->tuple[Ticket,...]:
    if len({q.game_id for q in legs})!=len(legs):
        raise ValueError('round robin with same game requires correlation-aware pricing')
    if size<2 or size>len(legs) or not isfinite(stake_each) or stake_each<=0:
        raise ValueError('invalid round robin size/stake')
    tickets=[]
    for idx,subset in enumerate(combinations(legs,size),1):
        decimal=1.0
        for leg in subset: decimal*=1.0+odds_multiple(leg.american)
        b=decimal-1.0
        # Derived book price is illustrative only, rounded integer loses exact pennies.
        american=round(100*b if b>=1 else -100/b)
        tickets.append(Ticket(f'RR_{size}_{idx}',subset,american,stake_each,'parlay',push_policy))
    return tuple(tickets)