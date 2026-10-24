import unittest
from betlab.joint_simulator import GameInputs,synthetic_joint_slate
from betlab.settlement import Ticket
from betlab.pricing import BookQuote
from betlab.scenarios import price_ticket
from betlab.risk import Candidate,recommend_simulated_allocation
from betlab.ledger import verify_ledger
from pathlib import Path

K='2026-10-11T17:00:00Z';NOW='2026-10-11T05:30:00Z'
def q(id,market,side,line,player=''):
 return BookQuote(id,'g',market,id,-110,'2026-10-11T05:25:00Z','synthetic',K,side,line,player_id=player,bookmaker='TestBook')
class JointAndRisk(unittest.TestCase):
 def test_joint_td_and_spread(self):
    sc=synthetic_joint_slate([GameInputs('g',25,18,{'p':.4},{'q':.3})],200,seed=7)
    self.assertEqual(sc,synthetic_joint_slate([GameInputs('g',25,18,{'p':.4},{'q':.3})],200,seed=7))
    a=q('a','spread','home',-3)
    b=q('b','player_td','yes',None,'p')
    t=Ticket('same_game',(a,b),200,10,'parlay','void_ticket')
    price=price_ticket(t,sc)
    self.assertEqual(price['outcome_count'],200)
    self.assertFalse(price['calibrated'])
 def test_share_overflow(self):
    with self.assertRaises(ValueError):synthetic_joint_slate([GameInputs('g',21,18,{'p':.8,'r':.8},{})])
 def test_no_data_no_stakes(self):
    c=Candidate(q('spread','spread','home',-3),.7,0,'v1')
    result=recommend_simulated_allocation([c],NOW,45)
    self.assertEqual(result['simulated_total_risk'],0)
    self.assertEqual(result['picks'][0]['decision'],'NO_BET')
 def test_qualified_paper_cap(self):
    c=Candidate(q('spread','spread','home',-3),.8,0,'test-v1','synthetic-receipt',True)
    result=recommend_simulated_allocation([c]*4,NOW,1000,session_cap=45)
    self.assertLessEqual(result['simulated_total_risk'],45)
    self.assertEqual(result['actual_bets_placed'],0)
 def test_ledger(self):
    path=Path(__file__).parents[1]/'docs'/'IMPLEMENTATION_LOG.jsonl'
    self.assertGreaterEqual(verify_ledger(path)['records'],3)
if __name__=='__main__':unittest.main()