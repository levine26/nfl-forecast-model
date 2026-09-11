import { expect, test } from '@playwright/test'

const viewports = [
  ['wide desktop', 1440, 1000],
  ['laptop', 1180, 820],
  ['tablet', 768, 1024],
  ['standard mobile', 390, 844],
  ['narrow mobile', 320, 700],
]

for (const [name, width, height] of viewports) {
  test(`${name}: forecast hierarchy fits and game details are usable`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('./')

    await expect(page.getByText('LEVLINE FORECAST').first()).toBeVisible()
    await expect(page.getByText('One forecast. Clear signals.')).toBeVisible()
    await expect(page.getByText('Probability-implied line').first()).toBeVisible()
    await expect(page.getByText('Fair line', { exact: true })).toHaveCount(0)
    await expect(page.locator('.co-game-card').first()).toBeVisible()

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.locator('.co-game-card').first().click()
    await expect(page.locator('.co-modal')).toBeVisible()
    await expect(page.getByText('FOOTBALL SIGNAL')).toBeVisible()
    await expect(page.getByText('MARKET SIGNAL')).toBeVisible()
    await expect(page.getByText('WHY LEVLINE?')).toBeVisible()
    await expect(page.getByText(/not expected margin/i).first()).toBeVisible()

    const modalOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(modalOverflow).toBeLessThanOrEqual(1)
  })
}

test('LevLine 3.0 launch identity and immutable history are public', async ({ page }) => {
  await page.goto('./')

  await expect(page).toHaveTitle('Sunday Signal — Powered by LevLine 3.0')
  await expect(page.locator('html')).toHaveAttribute('data-levline-version', '3.0')
  await expect(page.locator('.co-brand small')).toContainText('powered by LevLine')
  await expect(page.locator('.co-header-state b')).toContainText('LevLine')

  await page.getByRole('button', { name: 'History', exact: true }).click()
  await expect(page.getByText('OFFICIAL HISTORY')).toBeVisible()
  await expect(page.getByText('Immutable pregame receipts.')).toBeVisible()
  await expect(page.getByText('official locks')).toBeVisible()
  await expect(page.locator('.co-table-wrap table')).toBeVisible()
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

  await page.reload()
  await page.locator('.co-game-card').first().click()
  await expect(page.getByText('IMPACT MONITOR')).toBeVisible()
  await expect(page.getByText('Publication Safe Player')).toBeVisible()
  await expect(page.getByText(/explainability only/i)).toBeVisible()
  await expect(page.getByText(/not an authorized F-ST probability feature/i)).toBeVisible()
})
