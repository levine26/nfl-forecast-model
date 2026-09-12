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

    await expect(page.getByText('SUNDAY SIGNAL').first()).toBeVisible()
    await expect(page.getByText(/BETTER INFORMATION/i)).toBeVisible()
    await expect(page.getByText('TOP SIGNALS')).toBeVisible()
    await expect(page.getByText('Probability-Implied Line').first()).toBeVisible()
    await expect(page.getByText('Fair line', { exact: true })).toHaveCount(0)

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.locator('[data-game-open]:visible').first().click()
    await expect(page.locator('.ss-matchup-page')).toBeVisible()
    await expect(page.getByText('LEVLINE FORECAST').first()).toBeVisible()
    await expect(page.getByText('Football Signal').first()).toBeVisible()
    await expect(page.getByText('Market Signal').first()).toBeVisible()
    await expect(page.getByText('THE SIGNAL').first()).toBeVisible()
    await expect(page.getByText('WHY LEVLINE?', { exact: true })).toHaveCount(0)
    await expect(page).toHaveURL(/#\/game\//)

    const matchupOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(matchupOverflow).toBeLessThanOrEqual(1)

    await page.getByRole('button', { name: /How LevLine works/i }).first().click()
    await expect(page.getByText('WHY LEVLINE?', { exact: true })).toBeVisible()
  })
}

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

  await page.reload()
  await page.locator('[data-game-open]:visible').first().click()
  await expect(page.getByText('IMPACT MONITOR')).toBeVisible()
  await expect(page.getByText('Publication Safe Player')).toBeVisible()
  await expect(page.getByText(/explainability only/i)).toBeVisible()
  await expect(page.getByText(/not an authorized F-ST probability feature/i)).toBeVisible()
})

test('History remains a first-class 2026 receipts surface', async ({ page }) => {
  await page.goto('./#/history')
  await expect(page.getByText(/2026 PICKS OF RECORD/i)).toBeVisible()
  await expect(page.getByText(/Immutable pregame receipts/i)).toBeVisible()
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})
