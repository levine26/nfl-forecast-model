import unittest
from dataclasses import replace
from betlab.pricing import BookQuote
from betlab.settlement import GameResult
from betlab.evaluation import Prediction, grade_records, closing_line_value, block_bootstrap_roi,compare_fixed_splits

NOW='2026-10-11T05:30:00Z'; KO='2026-10-11T17:00:00Z'

def pr(id='q',result=None):
    q=BookQuote(id,'g','spread',id,-110,'2026-10-11T05:25:00Z','fixture',KO,'home',-3,bookmaker='TestBook')
    return Prediction(q,NOW,'2026-10-11T05:28:00Z','2026-10-11T05:10:00Z',.55,.03,result or GameResult(21,17),2026,5,1,model_version='fixed-v1')

class Evaluation(unittest.TestCase):
    def test_grade_brier_and_roi(self):
        report=grade_records([pr('a'),pr('b',GameResult(17,20))])
        self.assertEqual(report['win'],1);self.assertEqual(report['loss'],1)
        self.assertLess(report['roi_on_risk'],0)
        self.assertIsNotNone(report['brier_nonpush'])
    def test_reject_leakage(self):
        a=pr(); a=replace(a,feature_cutoff_utc='2026-10-11T06:00:00Z')
        with self.assertRaises(ValueError):a.validate()
        with self.assertRaises(ValueError):replace(a,feature_cutoff_utc=KO).validate()
    def test_quote_clv(self):
        a=pr()
        closing=replace(a.quote,line=-4.5,observed_utc='2026-10-11T16:59:00Z')
        self.assertAlmostEqual(closing_line_value(replace(a,closing_quote=closing)),1.5)
    def test_bootstrap(self):
        rows=[replace(pr(str(i)),week=(i//2)+1) for i in range(8)]
        bs=block_bootstrap_roi(rows,draws=100,seed=3)
        self.assertEqual(bs['blocks'],4)
    def test_split(self):
        rows=[{'id':str(i),'season':y} for i,y in enumerate([2022,2023,2024,2025])]
        s=compare_fixed_splits(rows,2023,2024,2025)
        self.assertEqual(len(s['holdout']),1)
        with self.assertRaises(ValueError):compare_fixed_splits(rows,2024,2023,2025)
if __name__=='__main__':unittest.main()