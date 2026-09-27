import test from 'node:test'
import assert from 'node:assert/strict'

import { buildBetLedger, gradeSpreadSelection } from '../src/betTrackerMath.js'

test('policy-era grading does not reconstruct a wager from model and generic market fields', () => {
  const ledger = buildBetLedger([{
    game_id:'2026_03_KC_MIA', season:'2026', week:'3', gameday:'2026-09-27', lock_status:'LOCKED',
    away_team:'KC', home_team:'MIA', pick:'KC', final_home_prob:'0.14',
    expected_margin:'-3.6876', spread_line:'-10.0',
    actual_home_score:'20', actual_away_score:'27',
  }])

  assert.equal(ledger.length, 1)
  assert.equal(ledger[0].spread, null)
})

test('dedicated ATS receipt remains authoritative even when generic fields disagree', () => {
  const ledger = buildBetLedger([{
    game_id:'2026_03_KC_MIA', season:'2026', week:'3', gameday:'2026-09-27', lock_status:'LOCKED',
    away_team:'KC', home_team:'MIA', pick:'KC', final_home_prob:'0.14',
    expected_margin:'99', spread_line:'99',
    locked_ats_status:'VALUE', locked_ats_pick_team:'MIA', locked_ats_pick_market_spread:'10',
    locked_ats_model_margin_home:'-3.6876', locked_ats_market_margin_home:'-10.0', locked_ats_home_edge_points:'6.3124',
    actual_home_score:'20', actual_away_score:'27',
  }])

  assert.equal(ledger[0].spread.side, 'MIA')
  assert.equal(ledger[0].spread.marketSpread, 10)
  assert.equal(ledger[0].spread.gradingSource, 'locked_ats_pick_market_spread')
  assert.equal(ledger[0].spread.result, 'win')
})

test('canonical selected-team formula grades favorite -3.5 as WIN when it wins by 5', () => {
  assert.equal(gradeSpreadSelection({
    side:'FAV', marketSpread:-3.5, homeTeam:'FAV', awayTeam:'DOG', finalHomeScore:27, finalAwayScore:22,
  }), 'win')
})
