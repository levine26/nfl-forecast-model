import csv
import json
import tempfile
import unittest
from pathlib import Path
from betlab.levline_scout import make_scout_report,render_scout_markdown,save_scout

class ScoutTests(unittest.TestCase):
    def setUp(self):
        self.work=tempfile.TemporaryDirectory()
        self.addCleanup(self.work.cleanup)
        self.root=Path(self.work.name)
        self.slate=self.root/'this_week.csv'
        columns=['game_id','gameday','away_team','home_team','final_home_prob','expected_margin','margin_sigma',
                 'expected_total','total_sigma','market_home_prob','spread_line','total_line',
                 'final_probability_strategy','model_version','prediction_timestamp_utc']
        games=[['2026_05_CHI_GB','2026-10-11','CHI','GB','.4716','-4.3025','12.89','44.3','13.64','.51','-1.5','46.5','F-ST-01-FROZEN-2026','v0','2026-10-11T04:26Z'],
               ['2026_05_PHI_JAX','2026-10-11','PHI','JAX','.7665','10.69','12.89','48.3','13.64','.77','7.5','41.5','F-ST-01-FROZEN-2026','v0','2026-10-11T04:26Z'],
               ['2026_05_TB_DAL','2026-10-08','TB','DAL','.8','4','12.89','45','13.64','.79','7.5','41.5','F-ST-01-FROZEN-2026','v0','2026-10-08T04:26Z']]
        with self.slate.open('w',newline='') as f:
            w=csv.writer(f);w.writerow(columns);w.writerows(games)

    def test_filter_excludes_played_day(self):
        report=make_scout_report(self.slate,'2026-10-11')
        self.assertEqual(report['games'],2)
        self.assertEqual(len(report['model_opinions_by_market']['spread']),2)
        self.assertNotIn('TB @ DAL',render_scout_markdown(report))

    def test_correct_home_away_spread_sign(self):
        report=make_scout_report(self.slate,'2026-10-11')
        spreads=report['model_opinions_by_market']['spread']
        self.assertIn('CHI -1.5',[r['model_opinion'] for r in spreads])
        self.assertIn('JAX -7.5',[r['model_opinion'] for r in spreads])
        self.assertTrue(all(r['recommended_dollars']==0 for r in spreads))

    def test_frozen_prob_market_only_reference(self):
        report=make_scout_report(self.slate,'2026-10-11')
        ml=report['model_opinions_by_market']['moneyline']
        self.assertTrue(ml[0]['model_opinion'].startswith('CHI ML (relative to archived market'))
        self.assertEqual(ml[0]['official_fst_most_likely_winner'],'CHI')
        self.assertAlmostEqual(ml[0]['official_fst_moneyline_prob_home'],.4716)
        self.assertNotIn('winner_margin_split',ml[0])
        self.assertFalse(any(x['book_price_verified'] for x in ml))

    def test_extreme_total_marks_caution(self):
        report=make_scout_report(self.slate,'2026-10-11')
        ja=next(r for r in report['model_opinions_by_market']['total'] if r['game_id'].endswith('PHI_JAX'))
        self.assertNotIn('EXTREME_TOTAL_DISAGREEMENT_INDEPENDENT_VALIDATION_REQUIRED',ja['flags'])
        self.assertTrue(ja['model_opinion'].startswith('Over 41.5'))

    def test_moneyline_cannot_determine_ats(self):
        before=make_scout_report(self.slate,'2026-10-11')
        # The winner probability can flip independent of margin and ATS outcome.
        self.slate.write_text(self.slate.read_text().replace(',.4716,',',.95,'))
        after=make_scout_report(self.slate,'2026-10-11')
        def ats(r):
            return next(x for x in r['model_opinions_by_market']['spread'] if x['game_id'].endswith('CHI_GB'))
        self.assertEqual(ats(before)['model_opinion'],ats(after)['model_opinion'])
        self.assertEqual(ats(before)['exploratory_cover_probability'],ats(after)['exploratory_cover_probability'])
        self.assertEqual(before['model_opinions_by_market']['moneyline'][0]['official_fst_moneyline_prob_home'],.4716)
        self.assertNotEqual(before['model_opinions_by_market']['moneyline'][0]['official_fst_moneyline_prob_home'],.95)

    def test_margin_can_change_without_moneyline_probability_change(self):
        before=make_scout_report(self.slate,'2026-10-11')
        self.slate.write_text(self.slate.read_text().replace(',-4.3025,',',5.0,'))
        after=make_scout_report(self.slate,'2026-10-11')
        def selected(r,market):
            return next(x for x in r['model_opinions_by_market'][market] if x['game_id'].endswith('CHI_GB'))
        self.assertEqual(selected(before,'moneyline')['official_fst_moneyline_prob_home'],selected(after,'moneyline')['official_fst_moneyline_prob_home'])
        self.assertNotEqual(selected(before,'spread')['model_opinion'],selected(after,'spread')['model_opinion'])

    def test_no_winner_margin_conflict_flags(self):
        r=make_scout_report(self.slate,'2026-10-11')
        for rows in r['model_opinions_by_market'].values():
            for x in rows:
                self.assertNotIn('WINNER_MARGIN_DISAGREEMENT',x.get('flags',[]))

    def test_spread_push_mass_integer_line(self):
        self.slate.write_text(self.slate.read_text().replace(',7.5,41.5',',7,41.5'))
        r=make_scout_report(self.slate,'2026-10-11')
        j=next(x for x in r['model_opinions_by_market']['spread'] if x['game_id'].endswith('PHI_JAX'))
        self.assertGreater(j['exploratory_push_probability'],0)
        self.assertLessEqual(j['exploratory_cover_probability']+j['exploratory_push_probability'],1)

    def test_immutable_save(self):
        report=make_scout_report(self.slate,'2026-10-11')
        out=self.root/'reports';p=save_scout(report,out)
        self.assertTrue(Path(p['json']).exists())
        with self.assertRaises(FileExistsError): save_scout(report,out)
        self.assertEqual(len(list(out.iterdir())),2)

    def test_missing_date_rejected(self):
        with self.assertRaises(ValueError):make_scout_report(self.slate,'2026-10-13')

    def test_no_market_time_preserved(self):
        r=make_scout_report(self.slate,'2026-10-11',source_status={'market_snapshot_timestamp_utc':None,'market_freshness_status_counts':{'unknown':2}})
        self.assertIsNone(r['market_snapshot_timestamp_utc'])
        self.assertEqual(r['market_freshness_counts'],{'unknown':2})

if __name__=='__main__':unittest.main()