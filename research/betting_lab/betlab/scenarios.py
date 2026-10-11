"""Joint game/player outcomes: preserve same-game correlation, never multiply marginals.

An explicit scenario distribution is the only interface trusted by the ticket engine.
A toy scenario generator can serve as an engineering fixture, NEVER a calibrated bet forecast.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import isclose,isfinite,sqrt
from .settlement import GameResult,Ticket,ticket_profit

@dataclass(frozen=True)
class Scenario:
    probability: float
    outcomes: dict[str,GameResult]


def price_ticket(ticket:Ticket, scenarios:tuple[Scenario,...]) -> dict:
    if not scenarios: raise ValueError('empty scenarios')
    total=sum(s.probability for s in scenarios)
    if not isclose(total,1.,abs_tol=1e-9):
        raise ValueError('scenario probabilities must sum to 1')
    distribution=[]
    for s in scenarios:
        if not isfinite(s.probability) or s.probability < 0:
            raise ValueError('invalid scenario probability')
        distribution.append((s.probability,ticket_profit(ticket,s.outcomes)))
    ev=sum(p*r for p,r in distribution)
    variance=sum(p*(r-ev)**2 for p,r in distribution)
    return {'expected_net_dollars':ev,'variance_dollars_squared':variance,
            'probability_profit':sum(p for p,r in distribution if r>1e-12),
            'probability_full_loss':sum(p for p,r in distribution if r < -ticket.stake+1e-9),
            'outcome_count':len(distribution),'calibrated':False}


def portfolio_distribution(tickets:tuple[Ticket,...], scenarios:tuple[Scenario,...],budget:float)->dict:
    if budget<0 or sum(t.stake for t in tickets)>budget+1e-9:
        raise ValueError('portfolio exceeds budget')
    if not scenarios or not isclose(sum(s.probability for s in scenarios),1,abs_tol=1e-9):
        raise ValueError('invalid scenario probabilities')
    rows=[]
    for s in scenarios:
        net=sum(ticket_profit(t,s.outcomes) for t in tickets)
        rows.append((s.probability,net))
    mean=sum(p*net for p,net in rows)
    return {'total_risk':sum(t.stake for t in tickets),'budget':budget,
            'expected_net_dollars':mean,
            'probability_loss':sum(p for p,net in rows if net < 0),
            'worst_case_loss':min(net for _,net in rows),
            'variance_dollars_squared':sum(p*(net-mean)**2 for p,net in rows),
            'calibrated':False,'bets_placed':0}