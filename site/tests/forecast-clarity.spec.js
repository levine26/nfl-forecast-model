import { expect, test } from '@playwright/test'

for (const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
  test(`${name}: game forecast explains probabilities, market edge, and model roles`, async ({ page }) => {
    await page.setViewportSize({width,height})
    await page.goto('./')
    await page.locator('[data-game-open]:visible').first().click()

    const clarity=page.locator('.ss-clarity-shell:visible').first()
    await expect(clarity).toBeVisible()
    await expect(clarity.getByText('LEVLINE FORECAST',{exact:true})).toBeVisible()
    await expect(clarity.getByText('LEVLINE FAIR SPREAD',{exact:true})).toBeVisible()
    await expect(clarity.getByText('SPORTSBOOK SPREAD',{exact:true})).toBeVisible()
    await expect(clarity.getByText('WIN-PROBABILITY EDGE',{exact:true})).toBeVisible()
    await expect(clarity.getByText('MODEL SCORE ESTIMATE',{exact:true})).toBeVisible()
    await expect(clarity.getByText('FORECAST TIER',{exact:true})).toBeVisible()
    await expect(clarity.getByText('MODEL AGREEMENT',{exact:true})).toBeVisible()

    const probabilityLabels=clarity.locator('.ss-clarity-prob-labels span')
    await expect(probabilityLabels).toHaveCount(2)
    const labelText=await probabilityLabels.allTextContents()
    expect(labelText.join(' ')).toMatch(/\d+\.\d%/)

    await clarity.locator('.ss-clarity-model-details summary').click()
    await expect(clarity.getByText('FOOTBALL FACTORS',{exact:true})).toBeVisible()
    await expect(clarity.getByText('MARKET FACTORS',{exact:true})).toBeVisible()
    await expect(clarity.getByText('LEVLINE FORECAST',{exact:true}).last()).toBeVisible()
    await expect(clarity.getByText(/not values that are added together/i)).toBeVisible()

    await expect(page.locator('.ss-matchup-page > .ss-forecast-hero')).toBeHidden()
    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}
