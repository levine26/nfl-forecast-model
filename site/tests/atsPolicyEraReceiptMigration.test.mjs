import test from 'node:test'
import assert from 'node:assert/strict'

import { buildBetLedger } from '../src/betTrackerMath.js'

test('Sep 27 policy-era receipt reconstructs ATS side from frozen receipt inputs only', () => {
  const ledger = buildBetLedger([{
    game_id:'2026_03_KC_MIA', season:'2026', week:'3', gameday:'2026-09-27', lock_status:'LOCKED',
    away_team:'KC', home_team:'MIA', pick:'KC', final_home_prob:'0.14',
    expected_margin:'-3.6876', spread_line:'-10.0', locked_home_moneyline:'+500',
  }])

  assert.equal(ledger.length, 1)
  assert.equal(ledger[0].spread.side, 'MIA')
  assert.equal(ledger[0].spread.marketSpread, 10)
  assert.equal(ledger[0].spread.gradingSource, 'policy_era_frozen_receipt_migration')
  assert.equal(ledger[0].spread.result, 'pending')
})

test('pre-policy receipt with no dedicated ATS fields remains ungraded', () => {
  const ledger = buildBetLedger([{
    game_id:'2026_03_ATL_GB', season:'2026', week:'3', gameday:'2026-09-24', lock_status:'LOCKED',
    away_team:'ATL', home_team:'GB', pick:'GB', final_home_prob:'0.61',
    expected_margin:'4.97', spread_line:'4.5',
  }])

  assert.equal(ledger.length, 1)
  assert.equal(ledger[0].spread, null)
})
