import csv, tempfile, unittest
from pathlib import Path
from betlab.historical_games import audit_game_csv,save_audit

HEAD='game_id,season,week,gameday,game_type,kickoff_utc,prediction_timestamp_utc,home_score,away_score,final_home_prob,market_home_prob,expected_margin,expected_total,spread_line,total_line\n'
class HistoricalSprintTests(unittest.TestCase):
    def make(self,data):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);p=Path(t.name)/'games.csv';p.write_text(HEAD+data);return p
    def test_market_home_margin_sign_and_push(self):
        p=self.make('2022_01_A_B,2022,1,2022-09-11,REG,2022-09-11T17:00:00Z,2022-09-11T15:00:00Z,24,17,0.7,0.6,10,45,7,40\n')
        a=audit_game_csv(p);self.assertEqual(a['headline']['spread_pushes'],1);self.assertEqual(a['headline']['total_wins'],1);self.assertEqual(a['headline']['moneyline_graded'],1);self.assertEqual(a['headline']['spread_wins'],0)
    def test_normal_cover_and_year_2021(self):
        p=self.make('2021_01_A_B,2021,1,2021-09-10,REG,2021-09-10T20:00:00Z,2021-09-10T19:00:00Z,20,17,0.51,0.60,4,40,2.5,38\n')
        a=audit_game_csv(p);self.assertEqual(a['seasons']['2021']['spread_wins'],1);self.assertEqual(a['seasons']['2021']['total_losses'],1)
    def test_outcome_after_prediction_or_missing_kick_excluded(self):
        p=self.make('2022_01_A_B,2022,1,2022-09-11,REG,2022-09-11T17:00:00Z,2022-09-11T18:00:00Z,20,17,0.51,0.60,4,40,2.5,38\n')
        a=audit_game_csv(p);self.assertEqual(a['qualified_games'],0);self.assertEqual(len(a['excluded']),1)
    def test_no_fabricated_roi(self):
        p=self.make('2022_01_A_B,2022,1,2022-09-11,REG,2022-09-11T17:00:00Z,2022-09-11T16:00:00Z,24,17,0.7,0.6,10,45,7.5,41\n')
        a=audit_game_csv(p);self.assertIsNone(a['headline']['moneyline_actual_price_roi']);self.assertIsNone(a['headline']['spread_actual_price_roi'])
    def test_create_only_output(self):
        p=self.make('2022_01_A_B,2022,1,2022-09-11,REG,2022-09-11T17:00:00Z,2022-09-11T16:00:00Z,24,17,0.7,0.6,10,45,7.5,41\n')
        report=audit_game_csv(p);dest=p.parent/'report.json';save_audit(report,dest)
        with self.assertRaises(FileExistsError):save_audit(report,dest)
    def test_duplicate_detection(self):
        row='2022_01_A_B,2022,1,2022-09-11,REG,2022-09-11T17:00:00Z,2022-09-11T16:00:00Z,24,17,0.7,0.6,10,45,7.5,41\n'
        p=self.make(row+row)
        with self.assertRaises(ValueError):audit_game_csv(p)