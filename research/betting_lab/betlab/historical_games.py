"""Historical game-market audit. No training, no props, no invented historical odds.

The LevLine ``spread_line`` field is the market HOME MARGIN, not the home
team's sportsbook handicap. For example, home Jaguars -8 corresponds to
spread_line=+8 and a home cover requires actual home margin > +8.

An observation must have a documented pre-kickoff prediction timestamp to be
included in a chronological evaluation. Unsupported/missing rows stay excluded.
"""
from __future__ import annotations
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite, log
from pathlib import Path
from statistics import mean

SEASONS = tuple(range(2021, 2026))
REQUIRED = ('game_id','season','week','gameday','home_score','away_score',
            'prediction_timestamp_utc','final_home_prob','expected_margin',
            'expected_total','spread_line','total_line')

def _value(row,key):
    try:
        x=float(row[key]);return x if isfinite(x) else None
    except (ValueError,TypeError,KeyError):return None

def _time(x):
    if not x: return None
    try:
        d=datetime.fromisoformat(str(x).replace('Z','+00:00'))
        return d.astimezone(timezone.utc) if d.tzinfo else None
    except (ValueError,TypeError):return None

def _close(a,b): return abs(a-b)<1e-7

def _rate(rows,key):
    vals=[r[key] for r in rows if r.get(key) is not None]
    return round(mean(vals),6) if vals else None

def _summary(rows):
    ml=[x for x in rows if x.get('winner_model_correct') is not None]
    mkt=[x for x in rows if x.get('winner_market_correct') is not None]
    return {'games':len(rows),'moneyline_graded':len(ml),'winner_accuracy':_rate(ml,'winner_model_correct'),
            'winner_market_accuracy':_rate(mkt,'winner_market_correct'),
            'winner_brier':_rate(ml,'winner_model_brier'),
            'winner_market_brier':_rate(mkt,'winner_market_brier'),
            'winner_log_loss':_rate(ml,'winner_model_log_loss'),
            'winner_market_log_loss':_rate(mkt,'winner_market_log_loss'),
            'margin_mae':_rate(rows,'margin_abs_error'),
            'market_margin_mae':_rate(rows,'market_margin_abs_error'),
            'total_mae':_rate(rows,'total_abs_error'),
            'market_total_mae':_rate(rows,'market_total_abs_error'),
            'spread_picks':sum(1 for r in rows if r.get('spread_outcome') in ('win','loss','push')),
            'spread_wins':sum(1 for r in rows if r.get('spread_outcome')=='win'),
            'spread_losses':sum(1 for r in rows if r.get('spread_outcome')=='loss'),
            'spread_pushes':sum(1 for r in rows if r.get('spread_outcome')=='push'),
            'total_picks':sum(1 for r in rows if r.get('total_outcome') in ('win','loss','push')),
            'total_wins':sum(1 for r in rows if r.get('total_outcome')=='win'),
            'total_losses':sum(1 for r in rows if r.get('total_outcome')=='loss'),
            'total_pushes':sum(1 for r in rows if r.get('total_outcome')=='push'),
            'moneyline_actual_price_roi':None,'spread_actual_price_roi':None,'total_actual_price_roi':None,
            'roi_reason':'No historical bookmaker-specific odds/decision-time contract is supplied; no -110 substitute.'}

def audit_game_csv(source:Path)->dict:
    data=source.read_bytes(); rows=list(csv.DictReader(data.decode('utf-8-sig').splitlines()))
    if not rows:raise ValueError('empty CSV')
    missing=set(REQUIRED)-set(rows[0]);
    if missing:raise ValueError('missing columns: '+', '.join(sorted(missing)))
    seen=set(); qualified=[]; excluded=[]
    for line,r in enumerate(rows,start=2):
        season=int(r['season']); game_id=r['game_id']
        if season not in SEASONS:continue
        if game_id in seen:raise ValueError('duplicate game_id '+game_id)
        seen.add(game_id)
        if r.get('game_type','REG')!='REG':continue
        p=_time(r['prediction_timestamp_utc']);kick=_time(r.get('kickoff_utc'))
        if p is None or kick is None or p>=kick:
            excluded.append({'game_id':game_id,'line':line,'reason':'MISSING_OR_POSTKICKOFF_PREDICTION_PROVENANCE'});continue
        if 'prediction_training_end_utc' in r and r['prediction_training_end_utc']:
            te=_time(r['prediction_training_end_utc']);
            if te is None or te>=p:
                excluded.append({'game_id':game_id,'line':line,'reason':'TRAINING_END_NOT_EARLIER_THAN_FORECAST'});continue
        keys=['home_score','away_score','final_home_prob','expected_margin','expected_total','spread_line','total_line']
        vals={k:_value(r,k) for k in keys}
        if any(vals[k] is None for k in keys) or not (0<vals['final_home_prob']<1):
            excluded.append({'game_id':game_id,'line':line,'reason':'INVALID_RESULT_OR_MODEL_INPUT'});continue
        h,a=vals['home_score'],vals['away_score']; margin=h-a; total=h+a
        # Matchup identity can be present in next season's schedule and prediction file;
        # this gate specifically checks quote/forecast pre-kickoff chronology and not feature ancestry.
        market_p=_value(r,'market_home_prob')
        if market_p is not None and not (0<market_p<1):market_p=None
        y=1 if margin>0 else 0 if margin<0 else None
        pwin=vals['final_home_prob'];one={'game_id':game_id,'season':season,'week':int(r['week']),
                    'winner_model_correct':(int((pwin>0.5)==bool(y)) if y is not None and pwin!=0.5 else None),
                    'winner_model_brier':((pwin-y)**2 if y is not None else None),
                    'winner_model_log_loss':(-(y*log(pwin)+(1-y)*log(1-pwin)) if y is not None else None),
                    'winner_market_correct':(int((market_p>0.5)==bool(y)) if y is not None and market_p is not None and market_p!=0.5 else None),
                    'winner_market_brier':((market_p-y)**2 if y is not None and market_p is not None else None),
                    'winner_market_log_loss':(-(y*log(market_p)+(1-y)*log(1-market_p)) if y is not None and market_p is not None else None),
                    'margin_abs_error':abs(vals['expected_margin']-margin),'market_margin_abs_error':abs(vals['spread_line']-margin),
                    'total_abs_error':abs(vals['expected_total']-total),'market_total_abs_error':abs(vals['total_line']-total)}
        def grade(model,book,actual):
            if _close(model,book):return None
            if _close(actual,book):return 'push'
            return 'win' if (model-book)*(actual-book)>0 else 'loss'
        one['spread_outcome']=grade(vals['expected_margin'],vals['spread_line'],margin)
        one['total_outcome']=grade(vals['expected_total'],vals['total_line'],total)
        qualified.append(one)
    return {'identity':'LEVLINE_GAME_MARKETS_HISTORICAL_AUDIT_V1','source_sha256':sha256(data).hexdigest(),
            'game_scope':'REG 2021-2025','qualified_games':len(qualified),'excluded':excluded,
            'qualification':'PREGAME_FORECAST_TIMESTAMP_REQUIRED; FEATURE_LINEAGE_NOT_REVERIFIED',
            'market_reference':'historical_closing_late_benchmark_exact_horizon_opaque',
            'no_refit':True,'no_injury_or_prop_analysis':True,
            'headline':_summary(qualified),
            'seasons':{str(s):_summary([r for r in qualified if r['season']==s]) for s in SEASONS},
            'game_rows':qualified}

def save_audit(report:dict,dest:Path)->Path:
    dest.parent.mkdir(parents=True,exist_ok=True)
    content=json.dumps(report,indent=2,sort_keys=True)+'\n'
    with dest.open('x',encoding='utf-8') as f:f.write(content)
    return dest