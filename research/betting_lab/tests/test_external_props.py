import unittest
from betlab.external_props import REGISTRY,combine_external_forecasts,ProviderError

ROW={'provider':'chzn1_td','authorized':True,'independently_captured':True,
 'prediction_utc':'2026-10-10T16:00:00Z','decision_utc':'2026-10-10T17:00:00Z',
 'kickoff_utc':'2026-10-11T17:00:00Z','game_id':'2026_05_X_Y','player_id':'pl001',
 'market':'anytime_td','line':0.5,'side':'over','probability':0.4,'source_ref':'source/abc'}
class ExternalPropsTests(unittest.TestCase):
 def test_real_single_external_provider_comparison_not_bet(self):
  o=combine_external_forecasts([dict(ROW)]);self.assertAlmostEqual(o[0]['model_consensus_p'],0.4);self.assertIn('NOT_BETTING',o[0]['status'])
 def test_denies_unqualified_forecast(self):
  with self.assertRaises(ProviderError):combine_external_forecasts([dict(ROW,authorized=False)])
 def test_denies_markets_as_model_projections(self):
  with self.assertRaises(ProviderError):combine_external_forecasts([dict(ROW,provider='startwho')])
 def test_denies_future_forecast(self):
  with self.assertRaises(ProviderError):combine_external_forecasts([dict(ROW,prediction_utc='2026-10-12T00:00:00Z')])
 def test_weighting_and_no_duplicate_provider(self):
  second=dict(ROW,provider='jmutammara',probability=0.6)
  out=combine_external_forecasts([dict(ROW),second])[0]
  self.assertAlmostEqual(out['model_consensus_p'],(3.5*.4+2.5*.6)/6,places=6)
  with self.assertRaises(ProviderError):combine_external_forecasts([dict(ROW),dict(ROW)])