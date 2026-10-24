"""Conservative allocation simulation; defaults to $0 for unvalidated evidence.

No automated execution. A user-entered calibration flag is not independently
proof of a real edge. All output remains a research simulation.
"""
from dataclasses import dataclass
from math import isfinite
from .pricing import BookQuote, fractional_kelly, expected_net

@dataclass(frozen=True)
class Candidate:
    quote:BookQuote
    win_lower:float
    push_probability:float
    observed_model_version:str
    calibration_receipt:str|None=None
    sample_qualified:bool=False


def recommend_simulated_allocation(candidates:list[Candidate],decision_utc:str,bankroll:float,
                                   session_cap:float=45.,per_bet_fraction:float=.02,
                                   per_game_fraction:float=.04)->dict:
    if not isfinite(bankroll) or bankroll<=0 or not isfinite(session_cap) or session_cap<0 or session_cap>45:
        raise ValueError('invalid budget')
    if not 0<per_bet_fraction<=.05 or not 0<per_game_fraction<=.1:
        raise ValueError('risk caps must be conservative')
    remaining=min(session_cap,bankroll)
    game_risk={}
    output=[]
    for c in candidates:
        reasons=[]
        try:c.quote.validate(decision_utc)
        except (ValueError,TypeError) as ex:reasons.append(f'QUOTE_REJECTED:{str(ex)}')
        if not c.sample_qualified or not c.calibration_receipt:
            reasons.append('UNQUALIFIED_MODEL_NO_INDEPENDENT_CALIBRATION_RECEIPT')
        if not c.observed_model_version:reasons.append('MISSING_MODEL_IDENTITY')
        if not 0<=c.win_lower<=1 or not 0<=c.push_probability<=1 or c.win_lower+c.push_probability>1:
            reasons.append('INVALID_LOWER_PROBABILITY')
        conservative_ev=expected_net(c.win_lower,c.push_probability,c.quote.american) if not any(r.startswith('INVALID') for r in reasons) else -1
        if conservative_ev<=0.02:reasons.append('ROBUST_EV_NOT_GREATER_THAN_2PCT')
        stake=0.
        if not reasons:
            kelly=fractional_kelly(c.win_lower,1-c.win_lower-c.push_probability,c.quote.american,0.125)
            stake=min(remaining,bankroll*per_bet_fraction,bankroll*kelly,
                      max(0,bankroll*per_game_fraction-game_risk.get(c.quote.game_id,0)))
            stake=round(stake,2)
            remaining-=stake
            game_risk[c.quote.game_id]=game_risk.get(c.quote.game_id,0)+stake
        output.append({'quote_id':c.quote.id,'research_stake':stake,'conservative_ev_per_dollar':round(conservative_ev,5),
                       'decision':'PAPER_ELIGIBLE' if stake>0 else 'NO_BET', 'reasons':reasons})
    return {'research_only':True,'actual_bets_placed':0,'bankroll':bankroll,'hard_cap':session_cap,
            'simulated_total_risk':round(sum(x['research_stake'] for x in output),2),'picks':output}