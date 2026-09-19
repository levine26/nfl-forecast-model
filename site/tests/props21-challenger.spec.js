import { test, expect } from '@playwright/test'

for (const width of [320,390,430,768,1440]) {
  test(`Props 2.1 Challenger is readable and honest at ${width}px`, async ({ page }) => {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('./#/props/challenger')
    await expect(page.getByRole('heading', { name: 'A closer look at player opportunity.' })).toBeVisible()
    await expect(page.getByText('PROPS 2.1 CHALLENGER', { exact: true })).toBeVisible()
    await expect(page.getByText(/market superiority have not been established/i)).toBeVisible()
    await expect(page.getByRole('link', { name: /canonical V1 board/i })).toBeVisible()
    await expect(page.locator('.p21-row').first()).toBeVisible({ timeout: 20000 })
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBeFalsy()
  })
}

test('reason tags explain state and never claim a wager edge', async ({ page }) => {
  await page.goto('./#/props/challenger')
  const cooper = page.locator('.p21-row').filter({ hasText: 'Cooper Rush' }).first()
  await expect(cooper).toBeVisible({ timeout: 20000 })
  await cooper.locator(':scope > summary').focus()
  await page.keyboard.press('Enter')
  await expect(cooper).toHaveJSProperty('open', true)
  await expect(cooper.getByText(/research observation, not a validated betting edge/i)).toBeVisible()
  await expect(page.getByText('MODEL EDGE', { exact: true })).toHaveCount(0)
  await expect(cooper.locator('.p21-identity')).toContainText('Player ID')
})
