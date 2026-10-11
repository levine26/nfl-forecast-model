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

RESEARCH_ID='LEVLINE-SCOUT-MARKET-RELATIVE-V01-2026-10-10'
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
    """Three market opinions derived only from the forecast file, without sportsbook juice."""
    gid=row['game_id']; home=row['home_team'];away=row['away_team'];mu=row['expected_margin'];center=_f(row,'spread_line')
    total=_f(row,'total_line'); p_home=row['final_home_prob'];p_market=_f(row,'market_home_prob'); mu_total=row['expected_total']
    margin_side='home' if mu>0 else 'away'
    winner_side='home' if p_home>0.5 else 'away'
    split=(margin_side!=winner_side)
    common={'game_id':gid,'game':away+' @ '+home,'date':row.get('gameday'),'model_timestamp_utc':row.get('prediction_timestamp_utc'),
            'official_prediction_strategy':row.get('final_probability_strategy'),
            'winner_margin_split':split,'forecast_model_label':row.get('model_version'),
            'book_quote_attached':False,'book_price_verified':False,'execution_ready':False,
            'recommended_dollars':0,'pricing_status':'MISSING_CURRENT_EXECUTABLE_TWO_SIDED_QUOTES',
            'scientific_status':'EXPLORATORY_UNCALIBRATED_NOT_A_POSITIVE_EV_CLAIM'}
    results=[]
    if center is not None:
        edge=mu-center # projected home margin minus home market implied margin
        selected=home if edge>0 else away
        # If home selected, actual home spread = -center; if away selected, away spread = center.
        spread=(-center if edge>0 else center)
        flags=[]
        if split:flags.append('WINNER_MARGIN_DISAGREEMENT')
        if abs(edge)<1:flags.append('LOW_PROJECTED_SPREAD_DISAGREEMENT')
        results.append({**common,'market':'spread','side':'home' if edge>0 else 'away',
            'model_opinion':f'{selected} {_pretty_spread(spread)}',
            'directional_model_disagreement':round(abs(edge),3),'disagreement_unit':'points',
            'levline_expected_margin_home':round(mu,3),'levline_market_reference_home_margin':round(center,3),
            'flags':flags,'calibration':'FAILED_PRIOR_ATS_INCREMENTAL_MARKET_TESTS'})
    else:
        results.append({**common,'market':'spread','model_opinion':None,'flags':['MISSING_MODEL_MARKET_REFERENCE']})
    if total is not None:
        diff=mu_total-total
        flags=[]
        if abs(diff)>=8:flags.append('EXTREME_TOTAL_DISAGREEMENT_INDEPENDENT_VALIDATION_REQUIRED')
        if abs(diff)<1:flags.append('LOW_PROJECTED_TOTAL_DISAGREEMENT')
        results.append({**common,'market':'total','side':'over' if diff>0 else 'under',
            'model_opinion':('Over' if diff>0 else 'Under')+' '+'%g'%total,
            'directional_model_disagreement':round(abs(diff),3),'disagreement_unit':'points',
            'levline_total_projection':round(mu_total,3),'levline_market_reference_total':round(total,3),
            'flags':flags,'calibration':'UNVALIDATED_TOTAL_DISTRIBUTION_AND_OUTLIER_AUDIT'})
    else:
        results.append({**common,'market':'total','model_opinion':None,'flags':['MISSING_MODEL_MARKET_REFERENCE']})
    if p_market is not None:
        p_diff=p_home-p_market
        side='home' if p_diff>0 else 'away';selected=home if side=='home' else away
        results.append({**common,'market':'moneyline','side':side,'model_opinion':f'{selected} ML (relative model-market shade only)',
            'directional_model_disagreement':round(abs(p_diff),5),'disagreement_unit':'probability',
            'levline_selected_win_probability':round(p_home if side=='home' else 1-p_home,5),
            'market_no_vig_probability_reference':round(p_market if side=='home' else 1-p_market,5),
            'flags':(['WINNER_MARGIN_DISAGREEMENT'] if split else [])+(['MODEL_RELATIVE_LEAN_OPPOSES_FST_WINNER_PICK'] if (side!=winner_side) else [])+(['TINY_PROBABILITY_DIFFERENCE'] if abs(p_diff)<.02 else []),
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
         'Moneyline entries are model-minus-market *relative shades*, not the official most-likely winner or a bet to place.',
         'The LevLine embedded spread/total references are not timestamp-qualified executable offers. Projections may lag current injuries and odds (injuries intentionally out of scope).',
         '', '**Model-implied candidates sorted by magnitude of disagreement, not by demonstrated profitability:**']
    for name in ('spread','moneyline','total'):
        out.extend(['', '## '+name.title(),'', '| Model opinion | Disagreement | Audit flags |','|---|---:|---|'])
        for row in report['model_opinions_by_market'][name]:
            edge=row.get('directional_model_disagreement')
            unit=row.get('disagreement_unit','')
            edge_fmt='—' if edge is None else (f'{100*edge:.2f} pp' if unit=='probability' else f'{edge:.2f} pts')
            out.append('| '+(row.get('model_opinion') or 'Unavailable')+' ('+row['game']+') | '+edge_fmt+' | '+(', '.join(row.get('flags',[])) or 'None')+' |')
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