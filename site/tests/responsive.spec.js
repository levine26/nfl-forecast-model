import { expect, test } from '@playwright/test'

const viewports = [
  ['wide desktop', 1440, 1000],
  ['laptop', 1180, 820],
  ['compact desktop', 1024, 900],
  ['tablet', 768, 1024],
  ['large mobile', 430, 900],
  ['standard mobile', 390, 844],
  ['narrow mobile', 320, 700],
]

for (const [name, width, height] of viewports) {
  test(`${name}: Sunday Signal hierarchy fits and matchup routing is usable`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('./')

    await expect(page.locator('.ss-brand-lockup:visible').first().getByText('SUNDAY SIGNAL')).toBeVisible()
    await expect(page.getByText(/BETTER INFORMATION/i)).toBeVisible()
    await expect(page.getByText('FIND YOUR GAME')).toBeVisible()
    await expect(page.locator('.ss-exp-top-signals:visible').getByText('TOP SIGNALS')).toBeVisible()
    await expect(page.getByText('Largest Edge vs Market', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: 'Win Probability', exact: true })).toBeVisible()
    if (width > 768) {
      await expect(page.locator('.ss-exp-board-labels:visible').getByText('LEVLINE FAIR SPREAD', { exact: true })).toBeVisible()
      await expect(page.locator('.ss-exp-board-labels:visible').getByText('SPORTSBOOK SPREAD', { exact: true })).toBeVisible()
    } else {
      await expect(page.locator('.ss-exp-mobile-board:visible').first()).toBeVisible()
      await expect(page.locator('.ss-exp-mobile-board:visible').first().getByText('Fair spread', { exact: true })).toBeVisible()
    }
    await expect(page.getByText('Fair line', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Model Line', { exact: true })).toHaveCount(0)
    await expect(page.getByText(/BIGGEST EDGE/i)).toHaveCount(0)
    await expect(page.getByText('#VALUE!', { exact: true })).toHaveCount(0)

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    const openRows = width <= 768 ? page.locator('.ss-exp-mobile-board:visible button') : page.locator('.ss-exp-board-rows:visible button')
    await openRows.first().click()
    await expect(page.locator('.ss-matchup-page')).toBeVisible()
    const clarity = page.locator('.ss-clarity-shell:visible').first()
    await expect(clarity).toBeVisible()
    await expect(clarity.locator('.ss-clarity-head').getByText('LEVLINE FORECAST', { exact: true })).toBeVisible()
    await expect(clarity.getByText('LEVLINE FAIR SPREAD', { exact: true })).toBeVisible()
    await expect(clarity.getByText('SPORTSBOOK SPREAD', { exact: true })).toBeVisible()
    await expect(clarity.getByText('WIN-PROBABILITY EDGE', { exact: true })).toBeVisible()
    await expect(clarity.getByText('FORECAST TIER', { exact: true })).toBeVisible()
    await expect(clarity.getByText('SINCE LAST FORECAST', { exact: true })).toBeVisible()
    await expect(page.locator('.ss-exp-lifecycle:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-signal:visible').getByText('THE SIGNAL', { exact: true })).toBeVisible()
    await expect(page.locator('.ss-exp-movement-context:visible')).toBeVisible()
    await expect(clarity.locator('.ss-clarity-share')).toBeVisible()
    await expect(page.getByText('WHY LEVLINE?', { exact: true })).toHaveCount(0)
    await expect(page).toHaveURL(/#\/game\//)

    const matchupOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(matchupOverflow).toBeLessThanOrEqual(1)

    await page.getByRole('button', { name: /How LevLine works/i }).first().click()
    await expect(page.getByText('WHY LEVLINE?', { exact: true })).toBeVisible()
  })
}

test('desktop slate values use readable non-condensed UI typography', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('./')
  const team = page.locator('.ss-exp-board-rows:visible .ss-exp-team-pair b').first()
  await expect(team).toBeVisible()
  const typography = await team.evaluate(element => {
    const style = getComputedStyle(element)
    return { fontFamily: style.fontFamily, fontStretch: style.fontStretch, letterSpacing: style.letterSpacing }
  })
  expect(typography.fontFamily).not.toMatch(/Arial Narrow|Roboto Condensed/i)
  expect(['normal', '100%']).toContain(typography.fontStretch)
  expect(['normal', '0px']).toContain(typography.letterSpacing)
})

test('governance-approved Impact Monitor renders as explainability-only context', async ({ page }) => {
  await page.goto('./')
  const gameId = await page.evaluate(async () => {
    const response = await fetch('./data/public_forecasts.json')
    const payload = await response.json()
    return payload.games[0].game_id
  })

  await page.route('**/data/impact_monitor.json', async route => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        schema_version: 1,
        mode: 'research_explainability_only',
        probability_feature_authorized: false,
        source_governance_review_status: 'approved_for_publication',
        games: [{
          game_id: gameId,
          probability_feature_authorized: false,
          players: [{
            game_id: gameId,
            team: 'TEST',
            player_id: '00-test',
            player_name: 'Publication Safe Player',
            position: 'WR',
            observed_statistics: [],
            suppressed_observed_statistics: 1,
            levline_impacts: [{
              metric: 'research_modeled_context',
              interpretation: 'Research-only modeled player context.',
              research_only: true,
              probability_feature_authorized: false,
            }],
            availability: null,
            data_quality: { identity_confidence: 'stable_id' },
            research_only: true,
            probability_feature_authorized: false,
          }],
        }],
      }),
    })
  })

  await page.goto(`./?impact-monitor-qa=1#/game/${encodeURIComponent(gameId)}`)
  await expect(page.getByText('IMPACT MONITOR')).toBeVisible()
  await expect(page.getByText('Publication Safe Player')).toBeVisible()
  await expect(page.getByText(/explainability only/i)).toBeVisible()
  await expect(page.getByText(/not an authorized F-ST probability feature/i)).toBeVisible()
})

test('matchup presentation reads the canonical official probability and official-winner surface', async ({ page }) => {
  await page.goto('./')
  const game = await page.evaluate(async () => {
    const response = await fetch('./data/public_forecasts.json')
    const payload = await response.json()
    return payload.games[0]
  })
  await page.goto(`./#/game/${encodeURIComponent(game.game_id)}`)
  await expect(page.locator('.ss-matchup-page')).toBeVisible()
  const clarity = page.locator('.ss-clarity-shell:visible')
  await expect(clarity).toBeVisible()
  await expect(clarity.locator('.ss-clarity-pick')).toContainText(game.official_winner === game.home_team || game.official_winner === game.away_team ? Number(game.official_winner_probability * 100).toFixed(1) : '')
  await expect(clarity.locator('.ss-clarity-pick strong')).toHaveText(`${(Number(game.official_winner_probability) * 100).toFixed(1)}%`)
  await expect(clarity.locator('.ss-clarity-pick span')).toContainText(/win probability/i)
  await expect(clarity).toContainText(game.official_winner)
})

test('History remains a first-class 2026 receipts surface with calibration and signal-tier accountability', async ({ page }) => {
  await page.goto('./#/history')
  await expect(page.getByText(/2026 PICKS OF RECORD/i)).toBeVisible()
  await expect(page.getByText(/Immutable pregame receipts/i)).toBeVisible()
  await expect(page.getByText('PERFORMANCE BY SIGNAL TIER')).toBeVisible()
  await expect(page.getByText('PROBABILITY CALIBRATION')).toBeVisible()
  await expect(page.getByText('THE SUNDAY SIGNAL STANDARD')).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})

test('Power Ratings exposes the richer published team profile without changing ranking authority', async ({ page }) => {
  await page.goto('./#/power')
  await expect(page.getByText('LEAGUE LENS')).toBeVisible()
  await expect(page.getByText('OFF EPA')).toBeVisible()
  await expect(page.getByText('DEF EPA ALLOWED')).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})