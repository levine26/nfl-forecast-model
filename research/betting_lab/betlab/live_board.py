"""Manual, timestamp-qualified pregame betting research board.

Reads LevLine's existing outputs/this_week.csv plus *operator-verified* manual quote
JSON. No network, no wagering, no injuries, no production writes. In particular,
mean-margin-to-cover conversions are UNCALIBRATED and are explicitly disqualified
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


def exploratory_probability(q: BookQuote, game: dict) -> tuple[float | None, str]:
    """NOT calibrated for wagering; no discrete 3/7 key-number mass."""
    if q.market == 'moneyline':
        if q.moneyline_tie == 'three_way' or q.side not in ('home','away'):
            return None, 'THREE_WAY_MONEYLINE_UNSUPPORTED'
        return (game['final_home_prob'] if q.side == 'home' else 1.0-game['final_home_prob'],
                'FROZEN_FST_WIN_PROBABILITY_HAS_NO_VALIDATED_QUOTE_EDGE')
    if q.market == 'spread':
        margin = game['expected_margin'] * (1 if q.side == 'home' else -1)
        return (_normal_cdf((margin+q.line)/game['margin_sigma']),
                'UNVALIDATED_NORMAL_NO_DISCRETE_KEY_MARGIN_OR_PUSH_MASS')
    if q.market == 'total':
        z=(game['expected_total']-q.line)/game['total_sigma']
        return (_normal_cdf(z if q.side=='over' else -z),
                'UNVALIDATED_NORMAL_NO_DISCRETE_TOTAL_OR_PUSH_MASS')
    return None,'PLAYER_MODEL_NOT_TRAINED_ON_QUALIFIED_NFL_DATA'


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
        p,reason=exploratory_probability(q,row)
        p_market,baseline_reason=_opposite_market_probability(q,parsed)
        p25=(0.75*p_market+0.25*p) if p is not None and p_market is not None else None
        p50=(0.5*p_market+0.5*p) if p is not None and p_market is not None else None
        rows.append({'id':q.id,'game_id':q.game_id,'game':row['away_team']+' @ '+row['home_team'],
                     'book':q.bookmaker,'market':q.market,'selection':q.selection,'line':q.line,
                     'american':q.american,'observed_utc':q.observed_utc,'implied_breakeven_no_push':implied_probability(q.american),
                     'market_reference_no_vig':p_market,
                     'full_levline_exploratory_probability':p,
                     'scenario_25pct_levline':p25,'scenario_50pct_levline':p50,
                     'scenario_25pct_ev_no_push':expected_net(p25,0,q.american) if p25 is not None else None,
                     'scenario_50pct_ev_no_push':expected_net(p50,0,q.american) if p50 is not None else None,
                     'model_limitation':reason,'baseline_limitation':baseline_reason,
                     'decision':'NO_BET_UNVALIDATED_PROBABILITY_AND_PROSPECTIVE_EDGE',
                     'stake_recommended':0.0})
    rows.sort(key=lambda x:(-1 if x['scenario_25pct_ev_no_push'] is None else -x['scenario_25pct_ev_no_push'],x['id']))
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
         '', 'The 25% and 50% LevLine columns are **uncalibrated sensitivity scenarios**; they are not win-probability guarantees. Push mass, NFL key numbers, correlated markets and operator settlement remain unvalidated.',
         '', '| Selection | Price | Market reference | 25% LevLine scenario | 50% LevLine scenario | Status |',
         '|---|---:|---:|---:|---:|---|']
    fmt=lambda p:'—' if p is None else f'{p:.1%}'
    for r in report['rows']:
        out.append('| '+ ' | '.join((r['selection'].replace('|','/'),
                    ('+' if r['american']>0 else '')+str(r['american']),
                    fmt(r['market_reference_no_vig']),fmt(r['scenario_25pct_levline']),
                    fmt(r['scenario_50pct_levline']),'RESEARCH ONLY'))+' |')
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