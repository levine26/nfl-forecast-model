"""Manual, timestamp-qualified pregame betting research board.

Reads LevLine's existing outputs/this_week.csv plus *operator-verified* manual quote
JSON. No network, no wagering, no injuries, no production writes. In particular,
mean-margin-to-cover conversions are independent from moneyline and UNCALIBRATED; disqualified
from automated EV recommendations or staking.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from hashlib import sha256
from math import erf, isfinite, sqrt
from pathlib import Path

from .pricing import BookQuote, expected_net, implied_probability, proportional_devig, quote_time
from .sources import qualified_manual_quote
from .market_probabilities import approximate_integer_line_outcomes

MODEL_COLUMNS = {'game_id', 'away_team', 'home_team', 'final_home_prob', 'expected_margin',
                 'margin_sigma', 'expected_total', 'total_sigma'}
MODEL_VERSION = 'LEVLINE_FST_OFFICIAL_PLUS_UNVALIDATED_MARGIN_SCENARIOS'


def load_slate(path: Path) -> dict[str, dict]:
    """Use a real LevLine CSV, not a reconstructed list of selected picks."""
    with path.open(newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        if not MODEL_COLUMNS <= set(reader.fieldnames or []):
            raise ValueError('forecast CSV missing required LevLine fields')
        games = {}
        for row in reader:
            game_id = row['game_id'].strip()
            if not game_id or game_id in games:
                raise ValueError('missing or duplicate game_id in forecast CSV')
            for field in ('final_home_prob','expected_margin','margin_sigma','expected_total','total_sigma'):
                row[field] = float(row[field])
                if not isfinite(row[field]):
                    raise ValueError('non-finite LevLine value')
            if not 0 < row['final_home_prob'] < 1 or row['margin_sigma'] <= 0 or row['total_sigma'] <= 0:
                raise ValueError('invalid LevLine probability/scale')
            games[game_id] = row
    if not games:
        raise ValueError('empty slate')
    return games


def _normal_cdf(x:float)->float:
    return 0.5*(1+erf(x/sqrt(2.0)))


def exploratory_outcomes(q:BookQuote,game:dict)->tuple[float|None,float|None,str]:
    """Return (win, push, scope); NEVER substitute ML odds for ATS odds.

    NFL game margin and total are discrete integers. We discretize an independent
    uncalibrated normal scenario for ATS/total with whole-line push mass. This is
    NOT a learned model and does not establish tradeable EV.
    """
    if q.market=='moneyline':
        if q.moneyline_tie=='three_way' or q.side not in ('home','away'):
            return None,None,'THREE_WAY_MONEYLINE_UNSUPPORTED'
        p=game['final_home_prob'] if q.side=='home' else 1-game['final_home_prob']
        return p,0.,'FROZEN_FST_MONEYLINE_ONLY_TIE_MASS_NOT_SEPARATELY_MODELED'
    if q.market=='spread':
        # Game expected_margin is home - away. Flip for away and compare the
        # selected team's win margin with its quoted handicap; no ML input.
        mean=game['expected_margin'] if q.side=='home' else -game['expected_margin']
        result=approximate_integer_line_outcomes(mean,game['margin_sigma'],-q.line,'over')
        return result['win'],result['push'],'ATS_EXPLORATORY_DISCRETE_NORMAL_NOT_CALIBRATED_OR_MARKET_QUALIFIED'
    if q.market=='total':
        result=approximate_integer_line_outcomes(game['expected_total'],game['total_sigma'],q.line,q.side)
        return result['win'],result['push'],'TOTAL_EXPLORATORY_DISCRETE_NORMAL_NOT_CALIBRATED_OR_MARKET_QUALIFIED'
    return None,None,'PLAYER_MODEL_NOT_TRAINED_ON_QUALIFIED_NFL_DATA'


def exploratory_probability(q:BookQuote,game:dict)->tuple[float|None,str]:
    """Legacy compatibility only; prefer exploratory_outcomes for push mass."""
    p,push,reason=exploratory_outcomes(q,game)
    return p,reason


def _opposite_market_probability(q: BookQuote, quotes: list[BookQuote]) -> tuple[float | None,str]:
    """Only same operator, line, event and timestamp-captured counterpart qualifies."""
    if q.market not in ('moneyline','spread','total'):
        return None,'NO_QUALIFIED_PLAYER_MARKET_BASELINE'
    other_sides={'home':'away','away':'home','over':'under','under':'over'}
    opposite=other_sides.get(q.side)
    peer=[x for x in quotes if x.id !=q.id and x.game_id ==q.game_id and x.market==q.market
          and x.bookmaker==q.bookmaker and x.side==opposite
          and (q.market=='moneyline' or (q.market=='spread' and abs(x.line+q.line)<1e-9) or (q.market=='total' and x.line==q.line))
          and x.observed_utc==q.observed_utc and x.moneyline_tie==q.moneyline_tie]
    if len(peer)!=1:
        return None, 'MISSING_EXACT_TWO_SIDED_SAME_BOOK_SAME_TIMESTAMP_QUOTE'
    # The normalized two-way implicit forecast is a reference null, NOT sportsbook true probability.
    try:
        probs=proportional_devig({q.side:q.american,opposite:peer[0].american})
    except ValueError:
        return None,'TWO_SIDED_MARKET_UNDERROUND_OR_INVALID'
    return probs[q.side], 'TWO_WAY_MARKET_BASELINE'


def analyze_live_slate(slate_path:Path, quotes_path:Path,*,max_quote_age_seconds:int=1800)->dict:
    source=slate_path.read_bytes()
    qsource=quotes_path.read_bytes()
    games=load_slate(slate_path)
    payload=json.loads(qsource)
    if not isinstance(payload,dict) or not isinstance(payload.get('quotes'),list):
        raise ValueError('manual quote snapshot must have quotes list')
    decision=payload['decision_utc']
    quote_time(decision)
    if payload.get('snapshot_type')!='MANUAL_DIRECT_OPERATOR_QUOTES':
        raise ValueError('requires manually verified direct sportsbook quote provenance')
    parsed=[]
    ids=set()
    for raw in payload['quotes']:
        q=qualified_manual_quote(raw,decision,max_quote_age_seconds)
        if q.id in ids:raise ValueError('duplicate quote ID')
        ids.add(q.id)
        if q.game_id not in games:
            raise ValueError('quote game not in actual LevLine slate: '+q.game_id)
        parsed.append(q)
    if not parsed:
        raise ValueError('no actual bookmaker quotes in snapshot')
    rows=[]
    for q in parsed:
        row=games[q.game_id]
        p,push,reason=exploratory_outcomes(q,row)
        p_market,baseline_reason=_opposite_market_probability(q,parsed)
        # Reference prices are conditional ON NONPUSH for spread/total.
        # Blend that probability, then recover actual cover and push outcomes.
        scenario=None if p is None or push is None or p_market is None else p/(1-push)
        p25=(1-push)*(0.75*p_market+0.25*scenario) if scenario is not None else None
        p50=(1-push)*(0.50*p_market+0.50*scenario) if scenario is not None else None
        rows.append({'id':q.id,'game_id':q.game_id,'game':row['away_team']+' @ '+row['home_team'],
                     'book':q.bookmaker,'market':q.market,'selection':q.selection,'line':q.line,
                     'american':q.american,'observed_utc':q.observed_utc,'implied_breakeven_no_push':implied_probability(q.american),
                     'market_reference_no_vig':p_market,
                     'market_reference_semantics':'NONPUSH_CONDITIONAL_FOR_SPREAD_TOTAL' if q.market in ('spread','total') else 'OUTRIGHT_TWO_WAY_ML_EXCLUDING_UNMODELLED_TIES',
                     'moneyline_probability_source':'FST_OFFICIAL_BINARY_ML' if q.market=='moneyline' else 'NOT_MONEYLINE',
                     'exploratory_push_probability':push,
                     'full_levline_exploratory_probability':p,
                     'scenario_25pct_levline':p25,'scenario_50pct_levline':p50,
                     'scenario_25pct_ev_push_aware':expected_net(p25,push,q.american) if p25 is not None else None,
                     'scenario_50pct_ev_push_aware':expected_net(p50,push,q.american) if p50 is not None else None,
                     'model_limitation':reason,'baseline_limitation':baseline_reason,
                     'decision':'NO_BET_UNVALIDATED_PROBABILITY_AND_PROSPECTIVE_EDGE',
                     'stake_recommended':0.0})
    rows.sort(key=lambda x:(float('inf') if x['scenario_25pct_ev_push_aware'] is None else -x['scenario_25pct_ev_push_aware'],x['id']))
    return {'research_only':True,'wager_orders_placed':0,'actual_wager_recommendations':0,
        'decision_utc':decision,'forecast_input_sha256':sha256(source).hexdigest(),
        'operator_quote_snapshot_sha256':sha256(qsource).hexdigest(),
        'forecast_model_label':MODEL_VERSION,'quotes_total':len(rows),
        'operator_license_and_settlement_not_independently_verified':True,
        'ranking_is_sensitivity_not_verified_positive_ev':True,
        'injury_report_integration':'EXCLUDED_BY_USER',
        'discrete_margin_calibration':'NOT_DONE',
        'rows':rows}


def render_markdown(report:dict)->str:
    out=['# LevLine Betting Lab — Pregame decision board','',
         f"**Decision time:** {report['decision_utc']}",
         f"**Quotes:** {report['quotes_total']} verified as timestamp-qualified manual entries (not externally independently audited)",
         '', '**Verdict:** No wager is qualified as positive-EV under the current scientific standard.',
         '', 'Official F-ST win probabilities are used ONLY for moneyline. ATS/total are independent distributions around margin/total forecasts, not implied by an outright favorite.',
         'The 25% and 50% LevLine columns are **uncalibrated sensitivity scenarios**; rounded-normal push mass is approximated on whole lines, but NFL key-number excess, correlation and operator settlement remain unvalidated.',
         '', '| Market | Selection | Price | Two-sided reference (conditional on nonpush for ATS/total) | 25% LevLine result probability | Estimated push | 50% LevLine result probability | Status |',
         '|---|---|---:|---:|---:|---:|---:|---|']
    fmt=lambda p:'—' if p is None else f'{p:.1%}'
    for r in report['rows']:
        out.append('| '+ ' | '.join((r['market'],r['selection'].replace('|','/'),
                    ('+' if r['american']>0 else '')+str(r['american']),
                    fmt(r['market_reference_no_vig']),fmt(r['scenario_25pct_levline']),
                    fmt(r['exploratory_push_probability']),fmt(r['scenario_50pct_levline']),'RESEARCH ONLY'))+' |')
    out += ['', 'Model and source input hashes:',
            f"- LevLine CSV: `{report['forecast_input_sha256']}`",
            f"- Direct-book quote JSON: `{report['operator_quote_snapshot_sha256']}`",
            '', 'No bets were placed. No profit or model accuracy has been established.']
    return '\n'.join(out)+'\n'


def save_report(report:dict,out_dir:Path)->dict:
    out_dir.mkdir(parents=True,exist_ok=True)
    tag=sha256((report['forecast_input_sha256']+report['operator_quote_snapshot_sha256']+report['decision_utc']).encode()).hexdigest()
    p=out_dir/(tag+'.json');md=out_dir/(tag+'.md')
    # Immutable receipts; never rewrite an earlier recorded decision.
    # If the second create-only write fails, roll back only the file made here.
    created=[]
    try:
        with p.open('x',encoding='utf-8') as f:
            created.append(p)
            json.dump(report,f,indent=2,sort_keys=True)
            f.write('\n')
        with md.open('x',encoding='utf-8') as f:
            created.append(md)
            f.write(render_markdown(report))
    except BaseException:
        for item in reversed(created):item.unlink(missing_ok=True)
        raise
    return {'report_json':str(p),'report_md':str(md),'snapshot_id':tag}