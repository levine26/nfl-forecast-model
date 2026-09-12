import { expect, test } from '@playwright/test'

for (const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
  test(`${name}: forecast explorer and game experience stay scannable`, async ({ page }) => {
    await page.setViewportSize({width,height})
    await page.goto('./')

    await expect(page.locator('.ss-exp-top-signals:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-forecast-explorer:visible')).toBeVisible()
    await expect(page.getByRole('button',{name:'Win Probability',exact:true})).toBeVisible()
    await expect(page.getByRole('button',{name:'Edge',exact:true})).toBeVisible()

    const openRows=width<=768?page.locator('.ss-exp-mobile-board:visible > button'):page.locator('.ss-exp-board-rows:visible > button')
    await expect(openRows.first()).toBeVisible()
    await openRows.first().click()

    await expect(page).toHaveURL(/#\/game\//)
    await expect(page.locator('.ss-clarity-shell:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-lifecycle:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-signal:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-movement-context:visible')).toBeVisible()
    await expect(page.locator('.ss-plus-signal')).toBeHidden()

    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}

test('history adds calibration and immutable receipt navigation when receipts exist', async ({ page }) => {
  await page.goto('./#/history')
  await expect(page.locator('section.ss-exp-history:visible')).toBeVisible()
  await expect(page.getByText('PROBABILITY CALIBRATION',{exact:true})).toBeVisible()

  const receipts=page.locator('.ss-exp-history-list > button')
  if (await receipts.count()) {
    await receipts.first().click()
    await expect(page).toHaveURL(/#\/receipt\//)
    await expect(page.locator('.ss-exp-receipt-page:visible')).toBeVisible()
    await expect(page.getByText(/OFFICIAL PREGAME RECEIPT/)).toBeVisible()
    await expect(page.getByText('PICK OF RECORD',{exact:true})).toBeVisible()
  }
})
