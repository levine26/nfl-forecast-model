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
    await expect(page.locator('.ss-plus-top-signals').getByText('TOP SIGNALS')).toBeVisible()
    await expect(page.getByText('MODEL VS MARKET').first()).toBeVisible()
    if (width > 1024) await expect(page.locator('.ss-board-labels:visible').getByText('LEVLINE PICK', { exact: true })).toBeVisible()
    else await expect(page.locator('.ss-mobile-card:visible').first().getByText('LEVLINE FORECAST')).toBeVisible()
    await expect(page.getByText('Fair line', { exact: true })).toHaveCount(0)
    await expect(page.getByText('Model Line', { exact: true })).toHaveCount(0)
    await expect(page.getByText(/BIGGEST EDGE/i)).toHaveCount(0)
    await expect(page.getByText('#VALUE!', { exact: true })).toHaveCount(0)

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.locator('[data-game-open]:visible').first().click()
    await expect(page.locator('.ss-matchup-page')).toBeVisible()
    await expect(page.getByText('LEVLINE FORECAST').first()).toBeVisible()
    await expect(page.getByText('Probability-Implied Line').first()).toBeVisible()
    await expect(page.locator('.ss-flow:visible').getByText('Football Signal')).toBeVisible()
    await expect(page.locator('.ss-flow:visible').getByText('Market Signal')).toBeVisible()
    await expect(page.locator('.ss-plus-signal:visible').getByText('THE SIGNAL', { exact: true })).toBeVisible()
    await expect(page.getByText('SIGNAL STRENGTH', { exact: true })).toBeVisible()
    await expect(page.getByText('WHAT CHANGED', { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: /Share this Sunday Signal matchup/i })).toBeVisible()
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
  const team = page.locator('.ss-game-row:visible .ss-row-matchup > span > b').first()
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
  await expect(page.locator('.ss-pick')).toBeVisible()
  await expect(page.getByText(`${Math.round(Number(game.official_winner_probability) * 100)}%`, { exact: true }).first()).toBeVisible()
  await expect(page.getByText('WIN PROBABILITY', { exact: true }).first()).toBeVisible()
  await expect(page.locator('.ss-plus-game-command')).toContainText(game.official_winner)
})

test('History remains a first-class 2026 receipts surface with signal-tier accountability', async ({ page }) => {
  await page.goto('./#/history')
  await expect(page.getByText(/2026 PICKS OF RECORD/i)).toBeVisible()
  await expect(page.getByText(/Immutable pregame receipts/i)).toBeVisible()
  await expect(page.getByText('PERFORMANCE BY SIGNAL TIER')).toBeVisible()
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
