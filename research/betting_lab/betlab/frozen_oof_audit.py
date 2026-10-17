"""Audit frozen 2022-2024 LevLine OOF A0/B0/C0 football results.

These are candidate-development OOF forecasts, *not* the production F-ST forecast
and *not* a wagerable sportsbook line archive. Historical nflverse market rows
have opaque late/closing quote horizons. NFL tied games are excluded from the
binary outright-winner metric, but retained for ATS and total grading.
"""
from __future__ import annotations

import csv
import json
from hashlib import sha256
from math import isfinite, log
from pathlib import Path

YEARS = (2022, 2023, 2024)
KEYS = ('game_id', 'season', 'game_type', 'actual_margin', 'actual_total',
        'spread_line', 'total_line', 'home_moneyline', 'away_moneyline')
CANDIDATES = ('A0', 'B0', 'C0')


def _number(row: dict, key: str) -> float:
    try:
        v = float(row[key])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f'invalid {key}: {row.get(key)!r}') from exc
    if not isfinite(v):
        raise ValueError(f'nonfinite {key}')
    return v


def _american(p: float) -> float:
    if p <= -100:
        return -p / (-p + 100)
    if p >= 100:
        return 100 / (p + 100)
    raise ValueError('invalid American odds')


def _read_csv(source: Path) -> tuple[bytes, list[dict[str, str]]]:
    content = source.read_bytes()
    rows = list(csv.DictReader(content.decode('utf-8-sig').splitlines()))
    if not rows:
        raise ValueError('empty historical input')
    return content, rows


def _side(pred: float, market: float, actual: float) -> str:
    if abs(pred - market) < 1e-10:
        return 'abstain'
    if abs(actual - market) < 1e-10:
        return 'push'
    return 'win' if (pred - market) * (actual - market) > 0 else 'loss'


def _mean(vals: list[float]) -> float | None:
    return round(sum(vals)/len(vals), 6) if vals else None


def _group(rows: list[dict]) -> dict:
    result: dict = {'games':len(rows), 'ml_ties_excluded':sum(x['tie'] for x in rows),
                    'market_reference':'HISTORICAL_LATE_CLOSING_HORIZON_OPAQUE',
                    'actual_bookmaker_roi':None}
    for name in ('MARKET','A0','B0'):
        ml = [r for r in rows if not r['tie']]
        probs = [r['ml_prob'][name] for r in ml]
        labels = [r['home_win'] for r in ml]
        result[name+'_ml_accuracy'] = _mean([int((p >= .5) == bool(y)) for p,y in zip(probs,labels)])
        result[name+'_ml_brier'] = _mean([(p-y)**2 for p,y in zip(probs,labels)])
        result[name+'_ml_logloss'] = _mean([-(y*log(p)+(1-y)*log(1-p)) for p,y in zip(probs,labels)])
    for market in ('margin','total'):
        for name in ('MARKET', 'A0', 'B0', 'C0'):
            result[name+'_'+market+'_mae'] = _mean([abs(r['pred'][market][name]-r[market]) for r in rows])
            if name == 'MARKET':
                continue
            outcomes = {'win':0,'loss':0,'push':0,'abstain':0}
            for r in rows:
                outcomes[_side(r['pred'][market][name],r['pred'][market]['MARKET'],r[market])] += 1
            decided=outcomes['win']+outcomes['loss']
            outcomes['hit_rate_ex_push'] = round(outcomes['win']/decided, 6) if decided else None
            result[name+'_'+market+'_direction'] = outcomes
    return result


def audit_existing_oof(baselines: Path, oof: Path) -> dict:
    base_raw, baseline = _read_csv(baselines)
    oof_raw, candidates = _read_csv(oof)
    if not set(KEYS).issubset(baseline[0]):
        raise ValueError('baseline lacks required columns')
    oof_required={'game_id', 'season','oof_provenance_assertion',
                  'a0_train_through_season','b0_train_through_season','c0_train_through_season',
                  'a0_home_win_probability','b0_home_win_probability',
                  'a0_expected_margin','b0_expected_margin','c0_hybrid_margin',
                  'a0_expected_total','b0_expected_total','c0_hybrid_total',
                  'c0_market_horizon_label'}
    if not oof_required.issubset(candidates[0]):
        raise ValueError('candidate OOF lacks required columns')
    by_id = {r['game_id']:r for r in candidates}
    if len(by_id)!=len(candidates):
        raise ValueError('duplicate candidate game ids')
    game_ids=set()
    joined=[]
    for b in baseline:
        year=int(b['season'])
        if year not in YEARS or b['game_type']!='REG':
            continue
        gid=b['game_id']
        if gid in game_ids:
            raise ValueError('duplicate baseline game id')
        game_ids.add(gid)
        o=by_id.get(gid)
        if not o or int(o['season'])!=year:
            raise ValueError(f'missing or wrong-year candidate: {gid}')
        if o['oof_provenance_assertion'].strip().lower()!='true':
            raise ValueError(f'unproven OOF source: {gid}')
        if o['c0_market_horizon_label']!='historical_closing_late_benchmark_exact_horizon_opaque':
            raise ValueError(f'market horizon mismatch: {gid}')
        for prefix in ('a0','b0','c0'):
            if _number(o,prefix+'_train_through_season')>=year:
                raise ValueError(f'lookahead in {prefix}: {gid}')
        margin=_number(b,'actual_margin')
        total=_number(b,'actual_total')
        if abs(margin-(_number(b,'home_score')-_number(b,'away_score')))>1e-8:
            raise ValueError(f'actual margin sign error: {gid}')
        if abs(total-(_number(b,'home_score')+_number(b,'away_score')))>1e-8:
            raise ValueError(f'actual total sign error: {gid}')
        odds_h=_american(_number(b,'home_moneyline'))
        odds_a=_american(_number(b,'away_moneyline'))
        market_prob=odds_h/(odds_h+odds_a)
        ml={'MARKET':market_prob,'A0':_number(o,'a0_home_win_probability'),
            'B0':_number(o,'b0_home_win_probability')}
        if any(not 0<p<1 for p in ml.values()):
            raise ValueError('invalid winner probability')
        joined.append({'game_id':gid,'season':year,'week':int(b['week']),
                       'margin':margin,'total':total,'home_win':int(margin>0),
                       'tie':abs(margin)<1e-8,'ml_prob':ml,
                       'pred':{'margin':{'MARKET':_number(b,'spread_line'),
                           'A0':_number(o,'a0_expected_margin'),
                           'B0':_number(o,'b0_expected_margin'),
                           'C0':_number(o,'c0_hybrid_margin')},
                         'total':{'MARKET':_number(b,'total_line'),
                           'A0':_number(o,'a0_expected_total'),
                           'B0':_number(o,'b0_expected_total'),
                           'C0':_number(o,'c0_hybrid_total')}}})
    if len(joined)!=len(candidates):
        raise ValueError('OOF candidate set does not match REG baseline set')
    return {'identity':'B08B_FROZEN_OOF_COMPARISON_V1','research_status':'REPRODUCED_ARCHIVED_DEVELOPMENT_EVIDENCE',
      'historical_scope':'2022-2024 NFL REGULAR SEASON',
      'game_rows_matched':len(joined),'forecast_names':['A0','B0','C0'],
      'not_production_fst':True,'no_new_training_or_selection':True,
      'winner_ties_excluded_from_binary_metrics':True,
      'market_quote_horizon':'historical_closing_late_benchmark_exact_horizon_opaque',
      'return_on_wagers':'NOT_AVAILABLE_NO_VERIFIED_EXECUTABLE_SAME_TIME_PRICE',
      'data_sources':[{'path':str(baselines),'sha256':sha256(base_raw).hexdigest()},
                      {'path':str(oof),'sha256':sha256(oof_raw).hexdigest()}],
      'pooled':_group(joined),
      'by_season':{str(s):_group([x for x in joined if x['season']==s]) for s in YEARS},
      'limitations':['Previously used development seasons 2022-2024 are not pristine holdout',
        'Market lines and moneyline prices are late/closing horizon-opaque, not executable betting-time quotes',
        'ATS/total hit rate is diagnostic for directional pick at reference line, not profit',
        'ML tie results excluded from binary outcome scoring; spread and totals retain tied games',
        '2025 F-ST historical winner evaluation is a DIFFERENT model/sample and must not be pooled',
        'No historical touchdown/yardage/other props evaluated']}


def save_audit(report:dict, dest:Path)->None:
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('x',encoding='utf-8') as fh:
        json.dump(report,fh,indent=2,sort_keys=True)
        fh.write('\n')