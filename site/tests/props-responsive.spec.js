import { expect, test } from '@playwright/test'

const baseForecast = {
  position: 'RB',
  team: 'BUF',
  opponent: 'MIA',
  kickoff_utc: '2026-09-20T20:05:00Z',
  forecast_timestamp_utc: '2026-09-18T17:04:00Z',
  data_horizon_utc: '2026-09-18T16:45:00Z',
  data_quality: { state: 'HIGH', confidence: 'HIGH', notes: [] },
  market_kind: 'CONTINUOUS',
  market: {
    line: 68.5,
    over_price_american: -110,
    under_price_american: -110,
    no_vig_over_probability: .5,
    no_vig_under_probability: .5,
    captured_utc: '2026-09-18T17:00:00Z',
    sportsbook: 'Test Book',
  },
  model: {
    fair_line: 74.2,
    line_difference: 5.7,
    mean: 74.8,
    median: 74.1,
    over_probability: .59,
    under_probability: .41,
    push_probability: 0,
    market_no_vig_probability: .5,
    probability_edge: .09,
    prediction_interval: { low: 45.1, high: 101.6, coverage: .8 },
    simulation_count: 10000,
    version: 'props-test',
  },
  drivers: [
    { label: 'Projected opportunity', direction: 'UP', detail: 'Published opportunity input points above the market baseline.' },
    { label: 'Matchup context', direction: 'UP', detail: 'Published matchup input is favorable in this forecast.' },
    { label: 'Uncertainty', direction: 'NEUTRAL', detail: 'Published distribution remains wide.' },
  ],
}

function forecast(overrides={}) {
  return {
    ...baseForecast,
    forecast_id: overrides.forecast_id || 'f-1',
    game_id: overrides.game_id || 'BUF-MIA',
    player: overrides.player || 'James Cook',
    prop_type: overrides.prop_type || 'rushing_yards',
    signal_state: overrides.signal_state || 'WATCH',
    ...overrides,
    market: { ...baseForecast.market, ...(overrides.market || {}) },
    model: { ...baseForecast.model, ...(overrides.model || {}) },
  }
}

const tdForecast = forecast({
  forecast_id: 'f-td',
  game_id: 'ARI-SEA',
  player: 'Trey McBride',
  position: 'TE',
  team: 'ARI',
  opponent: 'SEA',
  prop_type: 'anytime_td',
  market_kind: 'BINARY_TD',
  market: { line: null, td_price_american: 165, captured_utc: '2026-09-18T17:00:00Z', sportsbook: 'Test Book' },
  model: { fair_line: null, line_difference: null, td_probability: .43, market_no_vig_probability: .37, probability_edge: .06, fair_odds_american: 133, version: 'props-test', simulation_count: 10000 },
})

const noSignal = forecast({
  forecast_id: 'f-2',
  game_id: 'LAR-SF',
  player: 'Puka Nacua',
  position: 'WR',
  team: 'LAR',
  opponent: 'SF',
  prop_type: 'receiving_yards',
  signal_state: 'NO SIGNAL',
  unavailable_reasons: ['publication_gate_not_cleared'],
  market: { line: 79.5 },
  model: { fair_line: 80.1, line_difference: .6, probability_edge: .01 },
})

const payload = {
  generated_utc: '2026-09-18T17:04:00Z',
  forecasts: [forecast(), tdForecast, noSignal],
}

async function mockProps(page, customPayload=payload) {
  await page.route('**/data/props_public.json', route=>route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify(customPayload) }))
  await page.route('**/data/props_history.json', route=>route.fulfill({ status:200, contentType:'application/json', body:JSON.stringify({ records:[] }) }))
}

for (const [name,width,height] of [['desktop',1440,1000],['mobile 430',430,900],['mobile 390',390,844]]) {
  test(name + ': board-first Props is scannable and has no horizontal overflow', async ({ page }) => {
    await page.setViewportSize({ width, height })
    await mockProps(page)
    await page.goto('./#/props')

    await expect(page.getByRole('heading', { name: 'Player markets through the LevLine lens.' })).toBeVisible()
    await expect(page.getByText("ON LEVLINE'S RADAR", { exact:true })).toBeVisible()
    await expect(page.getByText('No MODEL EDGE signals right now.', { exact:true })).toBeVisible()
    await expect(page.getByText('FULL MARKET', { exact:true })).toBeVisible()
    await expect(page.getByText('Top Signals', { exact:true })).toHaveCount(0)
    await expect(page.getByText('All Props', { exact:true })).toHaveCount(0)

    const cook = page.locator('.lp-board-row').filter({ hasText:'James Cook' }).first()
    await expect(cook).toContainText('68.5')
    await expect(cook).toContainText('74.2')
    await expect(cook).toContainText('OVER')
    await expect(cook).toContainText('WATCH')

    const td = page.locator('.lp-board-row').filter({ hasText:'Trey McBride' }).first()
    await expect(td).toContainText('+165')
    await expect(td).toContainText('43.0%')

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await cook.locator('summary').click()
    await expect(cook.getByText('THE SIGNAL', { exact:true })).toBeVisible()
    await expect(cook.getByText('Advanced Analysis', { exact:true })).toBeVisible()
  })
}

test('Games is an index first and opens a game-specific Props board', async ({ page }) => {
  await mockProps(page)
  await page.goto('./#/props/games')
  await expect(page.getByRole('heading', { name:'Browse the slate, then go deep.' })).toBeVisible()
  const game = page.locator('.lp-game-index-row').filter({ hasText:'BUF' }).first()
  await expect(game).toContainText('markets')
  await game.click()
  await expect(page).toHaveURL(/#\/props\/games\//)
  await expect(page.getByText('GAME PROPS', { exact:true })).toBeVisible()
  await expect(page.locator('.lp-board-row').filter({ hasText:'James Cook' })).toBeVisible()
})

test('upstream MODEL EDGE is displayed but the frontend does not create one when absent', async ({ page }) => {
  const withEdge = { ...payload, forecasts:[forecast({ forecast_id:'f-edge', signal_state:'MODEL EDGE' }), tdForecast, noSignal] }
  await mockProps(page,withEdge)
  await page.goto('./#/props')
  await expect(page.locator('.lp-board-row.model-edge').first()).toContainText('MODEL EDGE')
  await expect(page.getByText('No MODEL EDGE signals right now.', { exact:true })).toHaveCount(0)
})

test('legacy Props aliases resolve to the Board', async ({ page }) => {
  await mockProps(page)
  await page.goto('./#/props/all')
  await expect(page.getByRole('heading', { name:'Player markets through the LevLine lens.' })).toBeVisible()
})
