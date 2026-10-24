import unittest
from dataclasses import replace
from betlab.pricing import BookQuote, implied_probability, proportional_devig, expected_net, fractional_kelly
from betlab.settlement import GameResult, grade, Ticket, ticket_profit, round_robin
from betlab.scenarios import Scenario,price_ticket,portfolio_distribution

NOW='2026-10-11T05:30:00Z'; KICK='2026-10-11T17:00:00Z'

def q(id='q',kind='spread', side='home',line=-3.0,american=-110,game='g',**kwargs):
    return BookQuote(id,game,kind,id,american,'2026-10-11T05:26:00Z','test fixture',KICK,side,line,bookmaker='TestBook',**kwargs)

class PricingSettlementTests(unittest.TestCase):
    def test_devig(self):
        p=proportional_devig({'home':-110,'away':-110})
        self.assertAlmostEqual(p['home'],.5)
        self.assertAlmostEqual(sum(p.values()),1.)
    def test_implied_and_ev(self):
        self.assertAlmostEqual(implied_probability(-110),11/21)
        self.assertAlmostEqual(expected_net(11/21,0,-110),0)
        self.assertAlmostEqual(expected_net(.5,.05,-110),.5/1.1-.45)
    def test_kelly(self):
        self.assertEqual(fractional_kelly(.4,.6,-110),0)
        self.assertGreater(fractional_kelly(.6,.4,-110),0)
    def test_quote_fresh(self):
        q().validate(NOW)
        with self.assertRaises(ValueError):q().validate('2026-10-11T09:00:00Z')
        with self.assertRaises(ValueError):replace(q(),observed_utc='2026-10-11T06:00:00Z').validate(NOW)
    def test_spread_push(self):
        self.assertEqual(grade(q(),GameResult(24,21)),'push')
        self.assertEqual(grade(q(),GameResult(31,21)),'win')
        self.assertEqual(grade(q(),GameResult(20,21)),'loss')
        self.assertEqual(grade(replace(q(),side='away',line=3.0),GameResult(24,21)),'push')
    def test_total(self):
        t=q(kind='total',side='over',line=44.5)
        self.assertEqual(grade(t,GameResult(24,21)),'win')
        self.assertEqual(grade(replace(t,side='under'),GameResult(24,21)),'loss')
    def test_moneyline_tie(self):
        m=q(kind='moneyline',side='away',line=None)
        self.assertEqual(grade(m,GameResult(3,3)),'push')
        self.assertEqual(grade(replace(m,moneyline_tie='three_way'),GameResult(3,3)),'loss')
    def test_td(self):
        t=q(kind='player_td',side='yes',line=None,player_id='p1')
        self.assertEqual(grade(t,GameResult(30,10,{'p1':2})),'win')
        with self.assertRaises(ValueError):grade(t,GameResult(30,10))
    def test_parlay_push_reprice(self):
        a=q(id='a',game='g1',kind='moneyline',side='home',line=None,american=-200)
        b=q(id='b',game='g2',kind='spread',side='home',line=-3,american=-110)
        ticket=Ticket('t',(a,b),200,10,'parlay','reprice_from_legs')
        self.assertAlmostEqual(ticket_profit(ticket,{'g1':GameResult(21,7),'g2':GameResult(24,21)}),5)
        self.assertEqual(ticket_profit(ticket,{'g1':GameResult(7,14),'g2':GameResult(24,21)}),-10)
    def test_teaser_unknown_push_blocked(self):
        a=q(id='a',game='g1',line=-8)
        b=q(id='b',game='g2',line=2.5)
        t=Ticket('teaser',(a,b),-110,10,'teaser','unknown',6)
        with self.assertRaises(ValueError):ticket_profit(t,{'g1':GameResult(24,22),'g2':GameResult(24,7)})
        t=replace(t,push_policy='lose_ticket')
        self.assertEqual(ticket_profit(t,{'g1':GameResult(24,22),'g2':GameResult(24,7)}),-10)
        with self.assertRaises(ValueError):ticket_profit(replace(t,push_policy='reprice_from_legs'),{'g1':GameResult(24,22),'g2':GameResult(24,7)})
    def test_joint_scenarios(self):
        a=q(id='a',game='g',kind='spread',side='home',line=-3)
        b=q(id='b',game='g',kind='total',side='over',line=44.5)
        ticket=Ticket('sgp',(a,b),200,10,'parlay','void_ticket')
        sc=(Scenario(.4,{'g':GameResult(31,21)}),Scenario(.6,{'g':GameResult(20,17)}))
        p=price_ticket(ticket,sc)
        self.assertAlmostEqual(p['expected_net_dollars'],2) # .4*20 - .6*10
        self.assertAlmostEqual(p['probability_profit'],.4)
    def test_portfolio_budget(self):
        t=Ticket('single',(q(),),-110,30)
        with self.assertRaises(ValueError):portfolio_distribution((t,t),(Scenario(1,{'g':GameResult(23,13)}),),45)
    def test_roundrobin(self):
        legs=(q(id='1',game='g1'),q(id='2',game='g2'),q(id='3',game='g3'))
        t=round_robin(legs,2,10,push_policy='reprice_from_legs')
        self.assertEqual(len(t),3)
        self.assertEqual(sum(x.stake for x in t),30)

if __name__=='__main__':unittest.main()