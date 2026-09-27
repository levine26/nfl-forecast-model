import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildBetLedger,
  summarizeBets,
  summarizeCombined,
} from '../src/betTrackerMath.js'

function favoriteReceipt(overrides={}) {
  return {
    game_id:'2026_03_DOG_FAV',
    season:'2026',
    week:'3',
    gameday:'2026-09-27',
    lock_status:'LOCKED',
    away_team:'DOG',
    home_team:'FAV',
    pick:'FAV',
    final_home_prob:'0.65',
    expected_margin:'7.5',
    spread_line:'3.5',
    locked_ats_status:'VALUE',
    locked_ats_pick_team:'FAV',
    locked_ats_pick_market_spread:'-3.5',
    locked_ats_model_margin_home:'7.5',
    locked_ats_market_margin_home:'3.5',
    locked_ats_home_edge_points:'4.0',
    locked_home_moneyline:'-150',
    ...overrides,
  }
}

test('favorite winning by five covers locked market -3.5 even though LevLine model line is -7.5', () => {
  const [entry]=buildBetLedger([favoriteReceipt({actual_home_score:'24',actual_away_score:'19'})])
  assert.equal(entry.spread.marketSpread,-3.5)
  assert.equal(entry.spread.modelMarginHome,7.5)
  assert.equal(entry.spread.result,'win')
})

test('changing only LevLine model/fair margin cannot change an already locked ATS grade', () => {
  const base=favoriteReceipt({actual_home_score:'24',actual_away_score:'19'})
  const [first]=buildBetLedger([base])
  const [second]=buildBetLedger([{
    ...base,
    expected_margin:'20.0',
    locked_model_spread:'20.0',
    locked_ats_model_margin_home:'20.0',
    locked_ats_home_edge_points:'16.5',
  }])

  assert.equal(first.spread.marketSpread,-3.5)
  assert.equal(second.spread.marketSpread,-3.5)
  assert.equal(first.spread.result,'win')
  assert.equal(second.spread.result,'win')
})

test('favorite non-cover is a loss at the locked sportsbook number', () => {
  const [entry]=buildBetLedger([favoriteReceipt({actual_home_score:'23',actual_away_score:'20'})])
  assert.equal(entry.spread.result,'loss')
})

test('exact equality at a whole-number locked spread is a push', () => {
  const [entry]=buildBetLedger([favoriteReceipt({
    locked_ats_pick_market_spread:'-3',
    locked_ats_market_margin_home:'3',
    actual_home_score:'23',
    actual_away_score:'20',
  })])
  assert.equal(entry.spread.result,'push')
})

test('underdog cover and outright underdog win use the selected-team positive market spread', () => {
  const cover=buildBetLedger([favoriteReceipt({
    locked_ats_pick_team:'DOG',
    locked_ats_pick_market_spread:'3.5',
    locked_ats_market_margin_home:'3.5',
    locked_ats_home_edge_points:'-4.0',
    actual_home_score:'24',
    actual_away_score:'22',
  })])[0]
  const outright=buildBetLedger([favoriteReceipt({
    locked_ats_pick_team:'DOG',
    locked_ats_pick_market_spread:'3.5',
    locked_ats_market_margin_home:'3.5',
    locked_ats_home_edge_points:'-4.0',
    actual_home_score:'20',
    actual_away_score:'24',
  })])[0]

  assert.equal(cover.spread.marketSpread,3.5)
  assert.equal(cover.spread.result,'win')
  assert.equal(outright.spread.result,'win')
})

test('malformed explicit ATS receipt fails closed rather than falling back to model or market fields', () => {
  const [entry]=buildBetLedger([favoriteReceipt({
    locked_ats_pick_market_spread:'',
    actual_home_score:'24',
    actual_away_score:'19',
  })])
  assert.equal(entry.spread,null)
})

test('ATS summaries expose numeric settled counts for downstream record aggregation', () => {
  const ledger=buildBetLedger([favoriteReceipt({
    actual_home_score:'24',
    actual_away_score:'19',
  })])
  const spread=summarizeBets(ledger,'spread')
  const combined=summarizeCombined(ledger)

  assert.equal(spread.settled,1)
  assert.equal(typeof spread.settled,'number')
  assert.equal(combined.settled,2)
  assert.equal(typeof combined.settled,'number')
})
