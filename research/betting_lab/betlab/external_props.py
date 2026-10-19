"""Third-party prop forecast comparison: no unauthorized proprietary data access.

This is NOT an independent touchdown model and does not manufacture forecasts.
Only forecasts supplied by a licensed/authorized, timestamped external provider can
participate in an explicitly unvalidated weighted comparison. Market prices are not
model forecasts and cannot masquerade as independent evidence.
"""
from __future__ import annotations
from collections import defaultdict
from math import isfinite

REGISTRY={
 'chzn1_td':{'label':'CHZN1 NFL Anytime Touchdown Model','url':'https://github.com/CHZN1/nfl-anytime-td-model','markets':('anytime_td',),'evidence':'2021-23 train, 2024 selection, 2025 holdout ROC-AUC 0.6876 RF; independent NFL Brier/ROI not established','availability':'CODE_AVAILABLE_NOT_EXECUTED','quality_prior':3.5},
 'custom_venom':{'label':'Custom Venom NFL Fantasy Methodology','url':'https://customvenom.com/methodology','markets':('anytime_td','pass_yards','rush_yards','receiving_yards','receptions'),'evidence':'Public volume-efficiency-range description; quantitative NFL betting calibration/independent feed and identity with Jake Venom unverified','availability':'METHODOLOGY_ONLY_UNQUALIFIED_API','quality_prior':2.0},
 'gameday':{'label':'GameDay Analytics NFL Props','url':'https://nfl.gamedayanalytics.net/props/methodology','markets':('pass_yards','rush_yards','receiving_yards','receptions','pass_tds'),'evidence':'Published sport/market specific evaluation policy; independently reverified prospective performance unavailable','availability':'METHODOLOGY_ONLY_UNQUALIFIED_API','quality_prior':2.5},
 'jmutammara':{'label':'JMutammara NFL Open-Source Player Models','url':'https://github.com/JMutammara/NFL','markets':('anytime_td','pass_yards','rush_yards','receiving_yards'),'evidence':'Open-source heteroscedastic player and Poisson TD architecture; reproducible performance not independently checked','availability':'CODE_AVAILABLE_NOT_EXECUTED','quality_prior':2.5},
 'startwho':{'label':'StartWho / Alexandria market-prop aggregation','url':'https://www.startwho.com/','markets':('anytime_td','pass_yards','rush_yards','receiving_yards','receptions'),'evidence':'Potential multi-book market quotes, overlapping information; source-specific quote timestamps and licensing not verified','availability':'MARKET_CONTEXT_ONLY_NOT_INDEPENDENT_MODEL','quality_prior':0.0}}

class ProviderError(ValueError):pass

def combine_external_forecasts(rows:list[dict],*,weight_floor=0.0)->list[dict]:
    """Weighted descriptive provider consensus, NOT automatically betting-eligible.

    Input rows must explicitly declare permitted usage, source as-of and pregame
    cutoff; provider identity, exact player/game/stat/line/market, and probability.
    Unavailable providers can participate only if a real external prediction is
    supplied and authorized, never inferred from methodology or a market quote.
    """
    if not 0<=weight_floor<=1:raise ValueError('invalid weight_floor')
    groups=defaultdict(list)
    for r in rows:
        provider=r.get('provider');model=REGISTRY.get(provider)
        if model is None or provider=='startwho':raise ProviderError('unknown or market-only provider')
        if not r.get('authorized') or not r.get('independently_captured'):
            raise ProviderError('unlicensed or unverified external prediction')
        from .pricing import quote_time
        try:
            prediction=quote_time(r['prediction_utc']); kickoff=quote_time(r['kickoff_utc'])
            decision=quote_time(r['decision_utc']);p=float(r['probability'])
        except (KeyError,ValueError,TypeError) as e:raise ProviderError('invalid timestamp/probability') from e
        if not (prediction<=decision<kickoff and 0<p<1 and isfinite(p)):
            raise ProviderError('invalid forecast chronology/probability')
        market=r.get('market')
        if market not in model['markets']:raise ProviderError('unsupported provider market')
        label=(r.get('game_id'),r.get('player_id'),market,r.get('line'),r.get('side'))
        if None in label or any(x=='' for x in label):raise ProviderError('incomplete prop selection identity')
        if not r.get('source_ref'):raise ProviderError('missing original forecast citation')
        groups[label].append((provider,p))
    out=[]
    for key,vals in sorted(groups.items(),key=lambda x:str(x[0])):
        if len(vals)!=len({x[0] for x in vals}):raise ProviderError('duplicate provider forecast for same prop')
        w=[REGISTRY[provider]['quality_prior'] for provider,_ in vals]
        if not sum(w):raise ProviderError('no independently forecast-capable provider')
        z=sum(w);p=sum(weight*pred for weight,(_,pred) in zip(w,vals))/z
        out.append({'game_id':key[0],'player_id':key[1],'market':key[2],'line':key[3],
                    'side':key[4],'providers':[name for name,_ in vals],
                    'model_consensus_p':round(p,6),'status':'UNVALIDATED_PROVIDER_CONSENSUS_NOT_BETTING_ELIGIBLE',
                    'weights':{name:round(weight/z,6) for weight,(name,_) in zip(w,vals)}})
    return out