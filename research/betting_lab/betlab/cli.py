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
    args=parser.parse_args()
    result=run_demo(n=args.samples) if args.cmd=='demo' else verify_ledger(args.path)
    s=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if getattr(args,'out',None):args.out.write_text(s)
    else:print(s)

if __name__=='__main__':main()