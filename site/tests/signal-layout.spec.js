import { expect, test } from '@playwright/test'

for (const [name, width, height] of [['desktop',1440,1000], ['mobile',390,844]]) {
  test(`${name}: numerical matchup replaces Read without creating page overflow`, async ({page}) => {
    await page.setViewportSize({width,height})
    await page.goto('./')
    const openRows = width <= 768
      ? page.locator('.ss-exp-mobile-board:visible > button')
      : page.locator('.ss-exp-board-rows:visible > button')
    await expect(openRows.first()).toBeVisible()
    await openRows.first().click()
    await expect(page.locator('.ss-matchup-page:visible')).toBeVisible()
    await expect(page.locator('.ss-clarity-shell:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-movement-context:visible')).toBeVisible()
    await expect(page.locator('.ss-exp-signal, .ss-plus-signal, .ss-the-signal')).toHaveCount(0)
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}
