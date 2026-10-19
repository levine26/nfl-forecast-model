import unittest
from betlab.market_probabilities import approximate_integer_line_outcomes as outcomes


class MarketProbabilityTests(unittest.TestCase):
    def test_whole_number_push_positive_and_sums_one(self):
        for side in ('over','under'):
            r=outcomes(3,12.9,3,side)
            self.assertGreater(r['push'],0)
            self.assertAlmostEqual(sum(r.values()),1,places=10)

    def test_half_points_cannot_push(self):
        for side in ('over','under'):
            r=outcomes(3,12.9,3.5,side)
            self.assertEqual(r['push'],0)
            self.assertAlmostEqual(sum(r.values()),1,places=10)

    def test_complement_home_away(self):
        h=outcomes(5.1,12.9,7,'over')
        a=outcomes(5.1,12.9,7,'under')
        self.assertAlmostEqual(h['win'],a['loss'],places=10)
        self.assertAlmostEqual(h['loss'],a['win'],places=10)
        self.assertAlmostEqual(h['push'],a['push'],places=10)

    def test_quarter_line_rejected(self):
        with self.assertRaises(ValueError):outcomes(0,13,3.25,'over')

    def test_no_moneyline_parameter_can_enter_spread_model(self):
        self.assertNotIn('moneyline',outcomes.__code__.co_varnames)
        self.assertNotIn('final_home_prob',outcomes.__code__.co_varnames)

if __name__=='__main__':unittest.main()