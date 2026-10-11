"""Manual research CLI. No betting actions, injury feeds, or production writes."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from hashlib import sha256
from .ledger import verify_ledger
from .pricing import BookQuote, expected_net, implied_probability,proportional_devig
from .settlement import GameResult,Ticket
from .scenarios import Scenario, price_ticket, portfolio_distribution
from .risk import Candidate,recommend_simulated_allocation
from .joint_simulator import GameInputs, synthetic_joint_slate
from .live_board import analyze_live_slate, save_report, render_markdown
from .levline_scout import make_scout_report,save_scout,render_scout_markdown
from .historical_games import audit_game_csv, save_audit
from .external_props import REGISTRY, combine_external_forecasts


def run_demo(seed:int=20261010,n:int=2000):
    """Entirely synthetic, no actual event probabilities or actual sportsbook odds."""
    inputs=[GameInputs('synthetic_game',24,21,{'demo_home_rb':.3,'demo_home_wr':.2},{'demo_away_rb':.35})]
    scores=synthetic_joint_slate(inputs,n,seed)
    when='2026-10-11T05:30:00Z'
    q1=BookQuote('synthetic_spread','synthetic_game','spread','Synthetic home -3.5',-110,
        '2026-10-11T05:25:00Z','SYNTHETIC_TEST_ONLY','2026-10-11T17:00:00Z','home',-3.5,bookmaker='SYNTHETIC_TEST_ONLY')
    q2=BookQuote('synthetic_td','synthetic_game','player_td','Synthetic WR TD yes',+240,
        '2026-10-11T05:25:00Z','SYNTHETIC_TEST_ONLY','2026-10-11T17:00:00Z','yes',player_id='demo_home_wr',bookmaker='SYNTHETIC_TEST_ONLY')
    for q in [q1,q2]:q.validate(when)
    ticket=Ticket('DEMO_JOINT_TICKET',(q1,q2),500,10,'parlay','void_ticket')
    return {'engine':'LevLine Betting Lab v0.2 research','no_real_bets':True,
      'all_odds_and_games_synthetic':True,'simulator_calibrated':False,
      'joint_ticket':price_ticket(ticket,scores),
      'simulated_allocation':recommend_simulated_allocation([Candidate(q1,.6,0,'UNVALIDATED')],when,45,45),
      'notes':'NEVER use synthetic demonstration probabilities as real-game betting edges.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='cmd',required=True)
    demo=sub.add_parser('demo',help='run explicitly synthetic end-to-end smoke test')
    demo.add_argument('--samples',type=int,default=2000)
    demo.add_argument('--out',type=Path)
    ledger=sub.add_parser('ledger',help='verify implementation ledger')
    ledger.add_argument('--path',type=Path,default=Path(__file__).resolve().parents[1]/'docs/IMPLEMENTATION_LOG.jsonl')
    board=sub.add_parser('board',help='research-only actual LevLine CSV + manual sportsbook quote report')
    board.add_argument('--slate',type=Path,required=True,help='LevLine outputs/this_week.csv')
    board.add_argument('--quotes',type=Path,required=True,help='exact-time manual operator quote JSON')
    board.add_argument('--outdir',type=Path,required=True,help='immutable output folder (create-only)')
    scout=sub.add_parser('scout',help='full-slate LevLine model-opinion watchlist; requires no invented bookmaker quotes')
    scout.add_argument('--slate',type=Path,required=True,help='actual LevLine forecast outputs/this_week.csv')
    scout.add_argument('--date',type=str,required=True,help='exact YYYY-MM-DD slate date')
    scout.add_argument('--outdir',type=Path,required=True,help='immutable report output directory')
    scout.add_argument('--status',type=Path,help='optional actual outputs/status.json for market timestamp audit')
    hist=sub.add_parser('historical-games',help='historical 2021-25 game-market evaluation on pregame forecast+result CSV')
    hist.add_argument('--csv',type=Path,required=True,help='joined pregame OOF forecast+game results CSV (not outcome-derived forecasts)')
    hist.add_argument('--out',type=Path,required=True,help='create-only report JSON destination')
    providers=sub.add_parser('prop-providers',help='review external model provider qualification (no odds/orders)')
    providers.add_argument('--out',type=Path,help='optional create-only JSON output')
    prop=sub.add_parser('external-prop-consensus',help='compare authorized externally supplied forecasts; no inferred provider outputs')
    prop.add_argument('--input',type=Path,required=True,help='JSON array, each forecast with source/time/license evidence')
    prop.add_argument('--out',type=Path,required=True,help='create-only comparison output')
    args=parser.parse_args()
    if args.cmd=='historical-games':
        report=audit_game_csv(args.csv);save_audit(report,args.out)
        print(json.dumps({'created':str(args.out),'qualified_games':report['qualified_games'],
                          'source_sha256':report['source_sha256'],'excluded':len(report['excluded']),
                          'roi_available':False},indent=2))
        return
    if args.cmd in ('prop-providers','external-prop-consensus'):
        report={'status':'COMPARISON_ONLY_NOT_AUTOMATIC_BETTING_ELIGIBLE',
                'providers':{k:{**v,'markets':list(v['markets'])} for k,v in REGISTRY.items()}} if args.cmd=='prop-providers' else {
                'status':'UNVALIDATED_THIRD_PARTY_CONSENSUS','rows':combine_external_forecasts(json.loads(args.input.read_text()))}
        out=getattr(args,'out',None)
        if out:
            out.parent.mkdir(parents=True,exist_ok=True)
            with out.open('x',encoding='utf8') as fh:json.dump(report,fh,indent=2,sort_keys=True)
        else:print(json.dumps(report,indent=2))
        return
    if args.cmd=='scout':
        status=json.loads(args.status.read_text()) if args.status else None
        result=make_scout_report(args.slate,args.date,source_status=status)
        print(json.dumps(save_scout(result,args.outdir),sort_keys=True))
        print(render_scout_markdown(result))
        return
    if args.cmd=='board':
        report=analyze_live_slate(args.slate,args.quotes)
        print(json.dumps(save_report(report,args.outdir),sort_keys=True))
        print(render_markdown(report))
        return
    result=run_demo(n=args.samples) if args.cmd=='demo' else verify_ledger(args.path)
    s=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if getattr(args,'out',None):args.out.write_text(s)
    else:print(s)

if __name__=='__main__':main()