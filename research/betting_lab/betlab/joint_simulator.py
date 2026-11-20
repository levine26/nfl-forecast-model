"""Experimental correlation-aware NFL score/TD generator for SOFTWARE TESTING ONLY.

Shared per-game tempo shocks couple home/away scores. TDs for individual
players are assigned conditional on team scoring. Does NOT reflect fitted
NFL score frequencies, injury data, or independently calibrated probabilities.
Never price real wagers from these synthetic probabilities.
"""
from __future__ import annotations
from dataclasses import dataclass,field
from random import Random
from math import isfinite
from .settlement import GameResult
from .scenarios import Scenario

@dataclass(frozen=True)
class GameInputs:
    id:str
    expected_home_points:float
    expected_away_points:float
    home_players:dict[str,float]=field(default_factory=dict)
    away_players:dict[str,float]=field(default_factory=dict)

    def validate(self):
        if not self.id or min(self.expected_home_points,self.expected_away_points)<0 or not all(isfinite(x) for x in (self.expected_home_points,self.expected_away_points)):
            raise ValueError('invalid game scoring inputs')
        for players in (self.home_players,self.away_players):
            if sum(players.values())>1+1e-12 or any(not isfinite(x) or x<0 for x in players.values()):
                raise ValueError('player TD scoring shares must be valid and sum <= 1')
            if any(not k for k in players):raise ValueError('player identifier missing')


def _draw_team_score(expected:float,tempo:float,shares:dict[str,float],rng:Random,drives:int=11)->tuple[int,dict[str,int]]:
    # Fixed illustrative FG opportunity prior, TD intensity solves expected points.
    # No guarantee all team scoring expectations are representable: reject extremes.
    fg=min(.15,expected/(8*drives))
    td=(expected/drives-3*fg)/7
    if td<0 or td+fg>0.95:
        raise ValueError('team score not representable by toy model')
    fg=min(.95,fg*tempo);td=min(1-fg,td*tempo)
    score=0
    tds={k:0 for k in shares}
    for _ in range(drives):
        x=rng.random()
        if x<td:
            score+=7
            p=rng.random();running=0.
            for k,share in shares.items():
                running+=share
                if p<running:
                    tds[k]+=1
                    break
        elif x<td+fg:
            score+=3
    return score,tds


def synthetic_joint_slate(games:list[GameInputs],n:int=1000,seed:int=20261010)->tuple[Scenario,...]:
    if not 2<=n<=100000:raise ValueError('sample count outside safe range')
    if len({g.id for g in games})!=len(games):raise ValueError('duplicate game')
    for g in games:g.validate()
    rng=Random(seed)
    out=[]
    for _ in range(n):
        outcomes={}
        for g in games:
            # Independent across games; within one game both offenses share tempo.
            tempo=rng.choices((.85,1,1.15),weights=(.2,.6,.2))[0]
            hp,htd=_draw_team_score(g.expected_home_points,tempo,g.home_players,rng)
            ap,atd=_draw_team_score(g.expected_away_points,tempo,g.away_players,rng)
            if set(htd).intersection(atd):raise ValueError('player ID collision across teams')
            outcomes[g.id]=GameResult(hp,ap,{**htd,**atd})
        out.append(Scenario(1/n,outcomes))
    return tuple(out)