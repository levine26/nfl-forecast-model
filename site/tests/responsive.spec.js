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
    await expect(page.locator('.co-game-card').first()).toBeVisible()

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)

    await page.locator('.co-game-card').first().click()
    await expect(page.locator('.co-modal')).toBeVisible()
    await expect(page.getByText('FOOTBALL SIGNAL')).toBeVisible()
    await expect(page.getByText('MARKET SIGNAL')).toBeVisible()
    await expect(page.getByText('WHY LEVLINE?')).toBeVisible()

    const modalOverflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(modalOverflow).toBeLessThanOrEqual(1)
  })
}
