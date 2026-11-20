import tempfile
import unittest
from pathlib import Path
from betlab.fst_archive_audit import audit_fst_archives, save_report

FIELDS='game_id,season,week,home_team,away_team,home_win,fst_prob,market_prob\n'
class FstArchiveAuditTests(unittest.TestCase):
    def make(self,dev='2022_01_A_B,2022,1,B,A,1,0.75,0.6\n',diag='2025_01_A_B,2025,1,B,A,0,0.25,0.4\n'):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        root=Path(tmp.name);a=root/'development.csv';b=root/'diag.csv';a.write_text(FIELDS+dev);b.write_text(FIELDS+diag)
        return a,b,root
    def test_distinct_moneyline_predictions(self):
        a,b,_=self.make();x=audit_fst_archives(a,b,enforce_expected_counts=False)
        self.assertEqual(x['overall']['games'],2)
        self.assertEqual(x['overall']['FST']['correct'],2)
        self.assertEqual(x['overall']['MARKET']['correct'],2)
        self.assertNotEqual(x['overall']['FST']['brier'],x['overall']['MARKET']['brier'])
        self.assertIsNone(x['real_world_betting_roi'])
    def test_duplicate_rejected(self):
        a,b,_=self.make(diag='2022_01_A_B,2022,1,B,A,0,0.25,0.4\n')
        with self.assertRaisesRegex(ValueError,'duplicate'):audit_fst_archives(a,b,enforce_expected_counts=False)
    def test_horizon_and_season_rejected(self):
        a,b,_=self.make(diag='2024_01_A_B,2024,1,B,A,0,0.25,0.4\n')
        with self.assertRaisesRegex(ValueError,'misplaced archive season'):audit_fst_archives(a,b,enforce_expected_counts=False)
    def test_no_historical_sample_inflation(self):
        a,b,_=self.make()
        with self.assertRaisesRegex(ValueError,'incomplete frozen coverage'):audit_fst_archives(a,b)
    def test_invalid_prob_rejected(self):
        a,b,_=self.make(dev='2022_01_A_B,2022,1,B,A,1,1.2,0.6\n')
        with self.assertRaisesRegex(ValueError,'invalid fst_prob'):audit_fst_archives(a,b,enforce_expected_counts=False)
    def test_create_only(self):
        a,b,root=self.make();x=audit_fst_archives(a,b,enforce_expected_counts=False)
        p=root/'result.json';save_report(x,p)
        with self.assertRaises(FileExistsError):save_report(x,p)
if __name__=='__main__':unittest.main()