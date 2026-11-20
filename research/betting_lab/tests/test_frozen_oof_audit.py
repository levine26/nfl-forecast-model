import csv
import tempfile
import unittest
from pathlib import Path
from betlab.frozen_oof_audit import audit_existing_oof, save_audit

B='game_id,season,week,game_type,actual_margin,actual_total,spread_line,total_line,home_moneyline,away_moneyline,home_score,away_score\n'
O=('game_id,season,oof_provenance_assertion,a0_train_through_season,b0_train_through_season,c0_train_through_season,'
   'a0_home_win_probability,b0_home_win_probability,a0_expected_margin,b0_expected_margin,c0_hybrid_margin,'
   'a0_expected_total,b0_expected_total,c0_hybrid_total,c0_market_horizon_label\n')
H='historical_closing_late_benchmark_exact_horizon_opaque'

class FrozenOOFTests(unittest.TestCase):
    def make(self,base,candidate):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        p=Path(tmp.name); b=p/'baseline.csv';o=p/'oof.csv';b.write_text(B+base);o.write_text(O+candidate)
        return b,o
    def test_independent_moneyline_spread_and_total(self):
        b,o=self.make('2022_01_A_B,2022,1,REG,7,41,6.5,42,-200,180,24,17\n',
             '2022_01_A_B,2022,True,2021,2021,2021,.7,.4,9,5,8,43,39,44,'+H+'\n')
        x=audit_existing_oof(b,o)['pooled']
        self.assertEqual(x['A0_margin_direction']['win'],1)
        self.assertEqual(x['B0_margin_direction']['loss'],1)
        self.assertEqual(x['A0_total_direction']['loss'],1)
        self.assertEqual(x['B0_total_direction']['win'],1)
        self.assertEqual(x['A0_ml_accuracy'],1)
        self.assertEqual(x['B0_ml_accuracy'],0)
        self.assertIsNone(x['actual_bookmaker_roi'])
    def test_tie_excluded_from_ml_not_spread(self):
        b,o=self.make('2022_01_A_B,2022,1,REG,0,40,-3,40,140,-160,20,20\n',
               '2022_01_A_B,2022,True,2021,2021,2021,.6,.4,1,-1,2,43,41,45,'+H+'\n')
        p=audit_existing_oof(b,o)['pooled']
        self.assertEqual(p['ml_ties_excluded'],1)
        self.assertIsNone(p['A0_ml_accuracy'])
        self.assertEqual(p['A0_margin_direction']['win'],1)
        self.assertEqual(p['A0_total_direction']['push'],1)
    def test_lookahead_rejected(self):
        b,o=self.make('2022_01_A_B,2022,1,REG,7,41,6.5,42,-200,180,24,17\n',
               '2022_01_A_B,2022,True,2022,2021,2021,.7,.4,9,5,8,43,39,44,'+H+'\n')
        with self.assertRaisesRegex(ValueError,'lookahead'):audit_existing_oof(b,o)
    def test_market_horizon_rejected(self):
        b,o=self.make('2022_01_A_B,2022,1,REG,7,41,6.5,42,-200,180,24,17\n',
               '2022_01_A_B,2022,True,2021,2021,2021,.7,.4,9,5,8,43,39,44,improper_t120\n')
        with self.assertRaisesRegex(ValueError,'horizon'):audit_existing_oof(b,o)
    def test_create_only(self):
        b,o=self.make('2022_01_A_B,2022,1,REG,7,41,6.5,42,-200,180,24,17\n',
               '2022_01_A_B,2022,True,2021,2021,2021,.7,.4,9,5,8,43,39,44,'+H+'\n')
        out=b.parent/'report.json'
        save_audit(audit_existing_oof(b,o),out)
        with self.assertRaises(FileExistsError):save_audit({},out)

if __name__=='__main__':unittest.main()