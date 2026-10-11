"""Sunday scout: use *existing* LevLine forecasts without inventing sportsbook prices.

This is a ranked MODEL-OPINION watchlist, never an automated bet recommendation.
Prior LevLine audits are negative/mixed for incremental ATS; a market-only null
remains the research benchmark. No historical backfit or production mutation.
"""
from __future__ import annotations

import json
from datetime import date
from hashlib import sha256
from math import isfinite
from pathlib import Path
from typing import Any

from .live_board import load_slate
from .market_probabilities import approximate_integer_line_outcomes

RESEARCH_ID='LEVLINE-SCOUT-THREE-MARKETS-V02-2026-10-10'
RESEARCH_EVIDENCE={
  'comparison':'2022-2025 OOS retrospective research; not a betting ROI demonstration',
  'legacy_raw_ats_hit_rate_ex_push':0.4877,
  'legacy_margin_mae':9.962,
  'historical_market_spread_mae':9.494,
  'ats_q1_v1':'REJECTED: failed positive market-relative quantile gate',
  'ats_q2_v1':'REJECTED: invalid numeric PMF support',
  'ats_q3_v1':'REJECTED: failed market-relative CPL log loss gate',
  'winner_model':'F-ST chronology-clean 741/1087 versus market 735/1087, uncertainty includes zero',
  'frozen_levline_production':'F-ST-01-FROZEN-2026',
  'provenance':[
   'research/ats-nextgen/FINAL_PHASE1_RECEIPT.md',
   'research/ats-nextgen/PHASE3_EVIDENCE_SYNTHESIS.md',
   'research/levline3_chronological_accuracy_audit_v1.json',
   'outputs/this_week.csv'
  ],
  'interpretation':'Diagnostics only: no proven incremental market-edge or optimal betting thresholds.'
}


def _f(row:dict,key:str)->float|None:
    value=row.get(key)
    if value is None or value=='':return None
    try:
        p=float(value)
        return p if isfinite(p) else None
    except (ValueError,TypeError):return None


def _pretty_spread(x:float)->str:
    # Exact home-team market spread is NEGATIVE of market home expected margin.
    val=0 if abs(x)<1e-10 else x
    return ('+' if val>0 else '')+('%g'%val)


def _game_research_rows(row:dict)->list[dict]:
    """Independently evaluate ML WIN probability, ATS cover, and O/U result.

    An official F-ST moneyline favorite is NOT an ATS pick. The archived market
    spread is NOT timestamp-qualified; all cover/total probabilities below are
    uncalibrated integer-normal thought experiments, not validated trading odds.
    """
    gid=row['game_id']; home=row['home_team']; away=row['away_team'];
    mu=row['expected_margin']; center=_f(row,'spread_line'); total=_f(row,'total_line')
    p_home=row['final_home_prob']; p_market=_f(row,'market_home_prob');mu_total=row['expected_total']
    p_away=1.0-p_home
    fav_team=home if p_home>=.5 else away
    fav_prob=max(p_home,p_away)
    common={'game_id':gid,'game':away+' @ '+home,'date':row.get('gameday'),
            'model_timestamp_utc':row.get('prediction_timestamp_utc'),
            'official_prediction_strategy':row.get('final_probability_strategy'),
            'forecast_model_label':row.get('model_version'),
            'official_fst_moneyline_prob_home':round(p_home,6),
            'official_fst_moneyline_prob_away':round(p_away,6),
            'official_fst_most_likely_winner':fav_team,
            'official_fst_favorite_probability':round(fav_prob,6),
            'book_quote_attached':False,'book_price_verified':False,'execution_ready':False,
            'recommended_dollars':0,'pricing_status':'MISSING_CURRENT_EXECUTABLE_TWO_SIDED_QUOTES',
            'scientific_status':'EXPLORATORY_UNCALIBRATED_NOT_A_POSITIVE_EV_CLAIM'}
    results=[]
    # ATS: A margin relative to a handicap, NOT the official winner probability.
    if center is not None:
        delta=mu-center
        side='home' if delta>=0 else 'away'; selected=home if side=='home' else away
        # Forecast home margin - away; market home handicap = -center.
        home_handicap=-center
        spread=home_handicap if side=='home' else center
        res=approximate_integer_line_outcomes(mu,row['margin_sigma'],center,
                                              'over' if side=='home' else 'under')
        flags=['UNVALIDATED_MARGIN_DISTRIBUTION_KEY_NUMBER_CALIBRATION']
        if abs(delta)<1:flags.append('LOW_PROJECTED_SPREAD_DISAGREEMENT')
        results.append({**common,'market':'spread','side':side,
            'model_opinion':f'{selected} {_pretty_spread(spread)}',
            'both_sides_reference_spread':{home:home_handicap,away:center},
            'directional_model_disagreement':round(abs(delta),3),'disagreement_unit':'points',
            'levline_expected_margin_home':round(mu,3),'levline_market_reference_home_margin':round(center,3),
            'exploratory_cover_probability':round(res['win'],6),
            'exploratory_push_probability':round(res['push'],6),
            'exploratory_noncover_probability':round(res['loss'],6),
            'flags':flags,'calibration':'FAILED_PRIOR_ATS_INCREMENTAL_MARKET_TESTS'})
    else:
        results.append({**common,'market':'spread','model_opinion':None,'flags':['MISSING_MODEL_MARKET_REFERENCE']})
    # Totals: an independent score-total distribution.
    if total is not None:
        diff=mu_total-total; side='over' if diff>=0 else 'under'
        res=approximate_integer_line_outcomes(mu_total,row['total_sigma'],total,side)
        flags=['UNVALIDATED_TOTAL_DISTRIBUTION']
        if abs(diff)>=8:flags.append('EXTREME_TOTAL_DISAGREEMENT_INDEPENDENT_VALIDATION_REQUIRED')
        if abs(diff)<1:flags.append('LOW_PROJECTED_TOTAL_DISAGREEMENT')
        results.append({**common,'market':'total','side':side,
            'model_opinion':('Over' if diff>=0 else 'Under')+' '+'%g'%total,
            'directional_model_disagreement':round(abs(diff),3),'disagreement_unit':'points',
            'levline_total_projection':round(mu_total,3),'levline_market_reference_total':round(total,3),
            'exploratory_total_win_probability':round(res['win'],6),
            'exploratory_total_push_probability':round(res['push'],6),
            'flags':flags,'calibration':'UNVALIDATED_TOTAL_DISTRIBUTION_AND_OUTLIER_AUDIT'})
    else:
        results.append({**common,'market':'total','model_opinion':None,'flags':['MISSING_MODEL_MARKET_REFERENCE']})
    # ML: an independent forecast of which team wins, NEVER an ATS probability.
    if p_market is not None:
        p_diff=p_home-p_market
        side='home' if p_diff>=0 else 'away';selected=home if side=='home' else away
        results.append({**common,'market':'moneyline','side':side,
            'model_opinion':f'{selected} ML (relative to archived market, not necessarily ML favorite)',
            'directional_model_disagreement':round(abs(p_diff),6),'disagreement_unit':'probability',
            'levline_selected_win_probability':round(p_home if side=='home' else p_away,6),
            'market_no_vig_probability_reference':round(p_market if side=='home' else 1-p_market,6),
            'flags':['TINY_PROBABILITY_DIFFERENCE'] if abs(p_diff)<.02 else [],
            'calibration':'FST_HISTORICAL_INCREMENTAL_ADVANTAGE_STATISTICALLY_UNPROVEN'})
    else:
        results.append({**common,'market':'moneyline','model_opinion':None,'flags':['MISSING_MODEL_MARKET_REFERENCE']})
    return results


def make_scout_report(slate:Path, target_date:str, *, source_status:dict|None=None)->dict:
    date.fromisoformat(target_date)
    parsed=load_slate(slate)
    eligible=[r for r in parsed.values() if r.get('gameday')==target_date]
    if not eligible:raise ValueError('no games for exact target date')
    if source_status is not None:
        if source_status.get('market_snapshot_timestamp_utc') is not None:
            timestamp=source_status['market_snapshot_timestamp_utc']
        else:timestamp=None
        market_status=source_status.get('market_freshness_status_counts')
    else: timestamp=None;market_status=None
    rows=[a for r in eligible for a in _game_research_rows(r)]
    # Ranking is separated by market because points and probability differences
    # cannot be compared or pooled as a single numerical edge.
    buckets={}
    for typ in ('moneyline','spread','total'):
        subset=[x for x in rows if x['market']==typ]
        subset.sort(key=lambda x:(x.get('directional_model_disagreement',0)),reverse=True)
        buckets[typ]=subset
    return {'id':RESEARCH_ID,'research_only':True,'target_date':target_date,'games':len(eligible),
        'no_bookmaker_prices':True,'no_qualified_wagers':True,'automated_staking_disabled':True,
        'forecast_file_sha256':sha256(slate.read_bytes()).hexdigest(),
        'market_snapshot_timestamp_utc':timestamp,'market_freshness_counts':market_status,
        'requires_current_operator_prices_and_independent_prospective_validation':True,
        'prior_levline_research':RESEARCH_EVIDENCE,'model_opinions_by_market':buckets}


def render_scout_markdown(report:dict)->str:
    out=['# LevLine Scout — Sunday model opinions','',f"**Slate date:** {report['target_date']} · **Games:** {report['games']}",
         '', '**Status:** Model-relative watchlist, NOT qualified sportsbook prices or calibrated wagering recommendations.',
         'The historical ATS challengers failed to establish incremental advantage versus market-only baselines. The existing winner model is market-heavy and its small advantage is statistically unresolved.',
         'Moneyline entries show MARKET-RELATIVE shades alongside OFFICIAL F-ST winner probabilities. A shade can favor an underdog without making it the most likely winner.',
         'Spread entries are evaluated strictly against the handicap and do NOT use F-ST moneyline win probability for ATS.',
         'ATS and total cover chances are exploratory push-aware rounded-normal approximations. They are NOT validated NFL ATS/total distributions.',
         'The LevLine embedded spread/total references are not timestamp-qualified executable offers. Projections may lag current injuries and odds (injuries intentionally out of scope).',
         '', '**Model-implied candidates sorted by magnitude of disagreement, not by demonstrated profitability:**']
    for name in ('moneyline','spread','total'):
        if name=='moneyline':
            out.extend(['','## Moneyline (outright wins; not spread covers)','',
                '| Game | Official F-ST ML (home / away) | F-ST favored winner | Relative ML shade vs stored market | Model-market difference |',
                '|---|---|---|---|---:|'])
            for row in report['model_opinions_by_market'][name]:
                ph=row['official_fst_moneyline_prob_home'];pa=row['official_fst_moneyline_prob_away']
                x=row.get('directional_model_disagreement')
                out.append(f"| {row['game']} | {ph:.1%} / {pa:.1%} | {row['official_fst_most_likely_winner']} ({row['official_fst_favorite_probability']:.1%}) | {row.get('model_opinion') or 'Unavailable'} | "+('—' if x is None else f'{100*x:.2f} pp')+' |')
        else:
            title='Spread (cover the handicap; independent of ML)' if name=='spread' else 'Total (over/under; independent of ML)'
            probkey='exploratory_cover_probability' if name=='spread' else 'exploratory_total_win_probability'
            out.extend(['','## '+title,'',
                '| Game | Archived model-reference angle | Projected difference | Exploratory chance of cover / total result | Push chance | Caveats |',
                '|---|---|---:|---:|---:|---|'])
            for row in report['model_opinions_by_market'][name]:
                edge=row.get('directional_model_disagreement')
                p=row.get(probkey);push=row.get('exploratory_push_probability' if name=='spread' else 'exploratory_total_push_probability')
                out.append('| '+row['game']+' | '+(row.get('model_opinion') or 'Unavailable')+' | '+('—' if edge is None else f'{edge:.2f} pts')+' | '+('—' if p is None else f'{p:.1%}')+' | '+('—' if push is None else f'{push:.1%}')+' | '+(', '.join(row.get('flags',[])) or 'None')+' |')
    out.extend(['','## What happens next',
     '1. Check current sportsbook prices and actual game availability. Never treat these model-reference lines as live book quotes.',
     '2. Run `python -m betlab.cli board --slate ... --quotes ... --outdir ...` with directly observed, timestamped prices for a quote-specific sensitivity analysis.',
     '3. Store an immutable pregame record and later grade it prospectively; do not assert actual ROI or edge until verified.',
     '', 'No bets were placed, no model promoted, and no automatic staking was performed.',
     f"Forecast SHA-256: `{report['forecast_file_sha256']}`",''])
    return '\n'.join(out)


def save_scout(report:dict,directory:Path)->dict:
    directory.mkdir(parents=True,exist_ok=True)
    tag=sha256((report['id']+report['target_date']+report['forecast_file_sha256']).encode()).hexdigest()
    jp=directory/(tag+'.scout.json'); mp=directory/(tag+'.scout.md')
    # Create only; fail loudly on a duplicated immutable snapshot. Roll back only own writes.
    written=[]
    try:
        with jp.open('x',encoding='utf-8') as f:
            written.append(jp); json.dump(report,f,sort_keys=True,indent=2);f.write('\n')
        with mp.open('x',encoding='utf-8') as f:
            written.append(mp);f.write(render_scout_markdown(report))
    except BaseException:
        for f in written:f.unlink(missing_ok=True)
        raise
    return {'json':str(jp),'markdown':str(mp),'snapshot_id':tag}