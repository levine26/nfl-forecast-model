import tempfile,unittest
from pathlib import Path
from betlab.sources import Capture,archive_capture,startwho_prop_inventory,qualified_manual_quote

class Sources(unittest.TestCase):
 def test_no_book_timestamp(self):
    raw={'players':[{'player_id':'p','team':'G','opponent':'@ X','props':[{'prop_type':'receiving_yds','bookmakers':[{'sportsbook':'Book','line':52.5,'over_odds':-110,'under_odds':-110}]}]}]}
    r=startwho_prop_inventory(raw,'2026-10-11T05:20:00Z')
    self.assertEqual(r[0]['eligibility'],'RESEARCH_CONTEXT_ONLY')
    self.assertIsNone(r[0]['quote_observed_utc'])
 def test_immutable_snapshots(self):
    cap=Capture('startwho-com','projections',{'week':5},'2026-10-11T05:30:00Z',None,{'players':[]})
    with tempfile.TemporaryDirectory() as d:
        r=archive_capture(cap,Path(d))
        self.assertTrue(Path(r['payload_path']).exists())
        self.assertEqual(len(r['raw_sha256']),64)
        with self.assertRaises(FileExistsError):archive_capture(cap,Path(d))
 def test_manual_quote_gate(self):
    raw={'id':'s','game_id':'g','market':'moneyline','selection':'home ML','american':-200,
       'observed_utc':'2026-10-11T05:25:00Z','source':'User manually captured operator quote',
       'kickoff_utc':'2026-10-11T17:00:00Z','side':'home','bookmaker':'Book'}
    qualified_manual_quote(raw,'2026-10-11T05:30:00Z')
    with self.assertRaises(ValueError):qualified_manual_quote({**raw,'observed_utc':'2026-10-11T02:30:00Z'},'2026-10-11T05:30:00Z')
    with self.assertRaises(ValueError):qualified_manual_quote({**raw,'source':'synthetic source'},'2026-10-11T05:30:00Z')
if __name__=='__main__':unittest.main()