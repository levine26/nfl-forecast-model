import { expect, test } from '@playwright/test'

const viewports = [
  ['wide desktop', 1440, 1000],
  ['tablet', 768, 1024],
  ['standard mobile', 390, 844],
  ['narrow mobile', 320, 700],
]

for (const [name, width, height] of viewports) {
  test(`${name}: scan-first board and full-page dossier remain usable`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('./week/1')

    await expect(page.getByText('Scan the slate in five seconds.')).toBeVisible()
    await expect(page.locator('.vx-card').first()).toBeVisible()
    await expect(page.getByText('Probability-implied line').first()).toBeVisible()
    await expect(page.locator('[role="dialog"]')).toHaveCount(0)

    let overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.locator('.vx-open').first().click()
    await expect(page).toHaveURL(/\/nfl-forecast-model\/game\//)
    await expect(page.getByText(/GAME DOSSIER/)).toBeVisible()
    await expect(page.getByRole('heading', { name: 'What changed' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Market' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Personnel' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Weather' })).toBeVisible()
    await expect(page.getByRole('heading', { name: 'Sources & freshness' })).toBeVisible()
    await expect(page.getByText(/presentation translation, not expected margin/i)).toBeVisible()

    overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.goBack()
    await expect(page.getByText('Scan the slate in five seconds.')).toBeVisible()
  })
}

test('week board loads the small public contract before dossier-only analytical data', async ({ page }) => {
  const requested=[]
  page.on('request', request => {
    const match=request.url().match(/\/data\/([^?]+)/)
    if(match)requested.push(match[1])
  })
  await page.goto('./week/1')
  await expect(page.locator('.vx-card').first()).toBeVisible()

  expect(requested).toContain('public_forecasts.json')
  expect(requested).toContain('status.json')
  expect(requested).toContain('game_previews.json')
  expect(requested).not.toContain('run_history.csv')
  expect(requested).not.toContain('contextual_evidence.json')
  expect(requested).not.toContain('impact_monitor.json')
  expect(requested).not.toContain('prediction_history.csv')

  await page.locator('.vx-open').first().click()
  await expect(page.getByText(/GAME DOSSIER/)).toBeVisible()
  expect(requested).toContain('run_history.csv')
  expect(requested).toContain('contextual_evidence.json')
  expect(requested).toContain('impact_monitor.json')
})

test('game routes are shareable and browser-local visit deltas persist', async ({ page }) => {
  await page.goto('./week/1')
  const href=await page.locator('.vx-open').first().getAttribute('href')
  expect(href).toMatch(/\/game\//)

  await page.goto(href)
  await expect(page.getByText(/GAME DOSSIER/)).toBeVisible()
  await page.reload()
  await expect(page.getByText(/GAME DOSSIER/)).toBeVisible()

  const storageKeys=await page.evaluate(() => Object.keys(localStorage).filter(key=>key.startsWith('sunday-signal:last-visit:v1:')))
  expect(storageKeys.length).toBeGreaterThan(0)
})

test('viewer-local time is default and PT/ET are explicit options', async ({ page }) => {
  await page.goto('./week/1')
  const select=page.getByLabel('Kickoff times')
  await expect(select).toHaveValue('local')
  await select.selectOption('pt')
  await expect(select).toHaveValue('pt')
  await select.selectOption('et')
  await expect(select).toHaveValue('et')
})

test('accountability is a first-class route with immutable receipts', async ({ page }) => {
  await page.goto('./history')
  await expect(page.getByRole('heading', { name: 'Probability quality, not just a record.' })).toBeVisible()
  await expect(page.getByText('Games scored')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Locked forecast receipts' })).toBeVisible()
})
