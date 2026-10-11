import csv, json, tempfile, unittest
from pathlib import Path
from betlab.live_board import analyze_live_slate,render_markdown,save_report

class LiveBoardTests(unittest.TestCase):
    def setUp(self):
        self.dir=tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root=Path(self.dir.name)
        self.slate=self.root/'live.csv'
        fields=['game_id','home_team','away_team','final_home_prob','expected_margin','margin_sigma','expected_total','total_sigma']
        with self.slate.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow(dict(zip(fields,['2026_05_PHI_JAX','JAX','PHI','.766','10.7','12.89','48.2','13.64'])))
        self.quotes=self.root/'quotes.json'
        self.snapshot={'snapshot_type':'MANUAL_DIRECT_OPERATOR_QUOTES','decision_utc':'2026-10-11T04:00:00Z',
            'quotes':[{'id':'q1','game_id':'2026_05_PHI_JAX','market':'moneyline', 'selection':'JAX ML','american':-350,
             'observed_utc':'2026-10-11T03:55:00Z','source':'DIRECT_USER_OPERATOR_SCREEN','kickoff_utc':'2026-10-11T13:30:00Z','side':'home','bookmaker':'EXAMPLE_BOOK'},
              {'id':'q2','game_id':'2026_05_PHI_JAX','market':'moneyline', 'selection':'PHI ML','american':+280,
             'observed_utc':'2026-10-11T03:55:00Z','source':'DIRECT_USER_OPERATOR_SCREEN','kickoff_utc':'2026-10-11T13:30:00Z','side':'away','bookmaker':'EXAMPLE_BOOK'}]}
        self.write()
    def write(self):self.quotes.write_text(json.dumps(self.snapshot))
    def test_valid_board(self):
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertEqual(r['quotes_total'],2)
        self.assertIsNotNone(r['rows'][0]['market_reference_no_vig'])
        self.assertTrue(all(x['stake_recommended']==0 for x in r['rows']))
        self.assertIn('RESEARCH ONLY',render_markdown(r))
        proof=save_report(r,self.root/'out')
        self.assertTrue(Path(proof['report_json']).exists())
        with self.assertRaises(FileExistsError):save_report(r,self.root/'out')
    def test_report_partial_collision_does_not_leave_new_json(self):
        r=analyze_live_slate(self.slate,self.quotes)
        import hashlib
        tag=hashlib.sha256((r['forecast_input_sha256']+r['operator_quote_snapshot_sha256']+r['decision_utc']).encode()).hexdigest()
        out=self.root/'out';out.mkdir();md=out/(tag+'.md');md.write_text('preexisting')
        with self.assertRaises(FileExistsError):save_report(r,out)
        self.assertFalse((out/(tag+'.json')).exists())
        self.assertEqual(md.read_text(),'preexisting')
    def test_stale_disqualified(self):
        self.snapshot['decision_utc']='2026-10-11T05:00:00Z';self.write()
        with self.assertRaisesRegex(ValueError,'stale'):analyze_live_slate(self.slate,self.quotes)
    def test_no_dubious_snapshot_type(self):
        self.snapshot['snapshot_type']='ALEXANDRIA_LAST_UPDATED';self.write()
        with self.assertRaisesRegex(ValueError,'direct sportsbook'):analyze_live_slate(self.slate,self.quotes)
    def test_missing_pair_baseline_unavailable(self):
        self.snapshot['quotes']=self.snapshot['quotes'][:1];self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertIsNone(r['rows'][0]['market_reference_no_vig'])
        self.assertIsNone(r['rows'][0]['scenario_25pct_ev_no_push'])
    def test_book_mismatch_cannot_create_devig(self):
        self.snapshot['quotes'][1]['bookmaker']='OTHER_BOOK';self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertTrue(all(x['market_reference_no_vig'] is None for x in r['rows']))
    def test_opposite_spreads_have_opposing_numeric_lines(self):
        self.snapshot['quotes'][0].update(market='spread',side='home',line=-8,american=-110)
        self.snapshot['quotes'][1].update(market='spread',side='away',line=8,american=-110)
        self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertAlmostEqual(r['rows'][0]['market_reference_no_vig'],.5)
        self.assertAlmostEqual(r['rows'][1]['market_reference_no_vig'],.5)
    def test_two_sided_total_requires_same_line(self):
        self.snapshot['quotes'][0].update(market='total',side='over',line=48.5,american=-110)
        self.snapshot['quotes'][1].update(market='total',side='under',line=48.5,american=-110)
        self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertAlmostEqual(r['rows'][0]['market_reference_no_vig'],.5)
        self.snapshot['quotes'][1]['line']=47.5;self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertIsNone(r['rows'][0]['market_reference_no_vig'])
    def test_invalid_quote_game_rejected(self):
        self.snapshot['quotes'][0]['game_id']='WRONG';self.write()
        with self.assertRaisesRegex(ValueError,'not in actual LevLine'):analyze_live_slate(self.slate,self.quotes)
    def test_observed_mismatch_cannot_create_devig(self):
        self.snapshot['quotes'][1]['observed_utc']='2026-10-11T03:54:00Z';self.write()
        r=analyze_live_slate(self.slate,self.quotes)
        self.assertIsNone(r['rows'][0]['market_reference_no_vig'])
    def test_quote_duplicate_id_rejected(self):
        self.snapshot['quotes'][1]['id']='q1';self.write()
        with self.assertRaisesRegex(ValueError,'duplicate quote ID'):analyze_live_slate(self.slate,self.quotes)

if __name__=='__main__':unittest.main()