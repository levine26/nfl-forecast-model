import { expect, test } from '@playwright/test'

test('approved forecast UI has one featured section and upcoming-first controls', async ({page}) => {
  await page.goto('./')
  await expect(page.locator('.ss-exp-top-signals:visible')).toHaveCount(1)
  await expect(page.locator('.ss-plus-top-signals')).toHaveCount(0)
  await expect(page.getByRole('button',{name:'Next Up',exact:true})).toBeVisible()
  await expect(page.locator('.ss-exp-board-labels:visible').getByText('PROBABILITY-IMPLIED LINE')).toBeVisible()
  const first=page.locator('.ss-exp-board-rows:visible > button').first()
  await expect(first).toBeVisible()
  await expect(first.locator('.ss-exp-edge')).toContainText(/pp|—/)
  await first.click()
  await expect(page.locator('.ss-ats-betting-note:visible')).toContainText('Betting value: not verified')
  await expect(page.locator('.ss-clarity-shell:visible .ss-clarity-metrics').getByText('PROBABILITY-IMPLIED LINE',{exact:true})).toBeVisible()
})

test('Performance Lab is descriptive and does not present an on-time-only claim', async ({page}) => {
  await page.goto('./#/history')
  const panel=page.locator('.ss-exp-performance:visible')
  await expect(panel).toBeVisible()
  await expect(panel.getByText('PERFORMANCE LAB · 2026')).toBeVisible()
  await expect(panel.getByText(/late locks/i)).toBeVisible()
  await expect(panel.getByText('LEVLINE BRIER')).toBeVisible()
  await expect(panel.getByText('MARKET BRIER')).toBeVisible()
})

test('approved mobile cards expose distinct implied spread and percentage-point comparison', async ({page}) => {
  await page.setViewportSize({width:390,height:844})
  await page.goto('./')
  const card=page.locator('.ss-exp-mobile-board:visible > button').first()
  await expect(card).toBeVisible()
  await expect(card.getByText('Implied line')).toBeVisible()
  await expect(card.getByText('Prob. difference')).toBeVisible()
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
  expect(overflow).toBeLessThanOrEqual(1)
})
