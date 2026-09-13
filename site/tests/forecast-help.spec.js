import { expect, test } from '@playwright/test'

for (const [name,width,height] of [['desktop',1440,1000],['mobile',390,844]]) {
  test(`${name}: forecast help opens and explains the model in first-time-user language`, async ({ page }) => {
    await page.setViewportSize({width,height})
    await page.goto('./')

    const openRows=width<=768?page.locator('.ss-exp-mobile-board:visible > button'):page.locator('.ss-exp-board-rows:visible > button')
    await expect(openRows.first()).toBeVisible()
    await openRows.first().click()
    await expect(page).toHaveURL(/#\/game\//)

    const helpButton=page.locator('.ss-clarity-info:visible').first()
    await expect(helpButton).toBeVisible()
    await helpButton.click()

    const dialog=page.getByRole('dialog',{name:'The 30-second version'})
    await expect(dialog).toBeVisible()
    await expect(dialog.getByText('Who does LevLine pick?',{exact:true})).toBeVisible()
    await expect(dialog.getByText('How does LevLine compare with the market?',{exact:true})).toBeVisible()
    await expect(dialog.getByText('How strong is the signal?',{exact:true})).toBeVisible()
    await expect(dialog.getByText('Win probability',{exact:true})).toBeVisible()
    await expect(dialog.getByText('LevLine fair spread',{exact:true})).toBeVisible()
    await expect(dialog.getByText('Sportsbook spread',{exact:true})).toBeVisible()
    await expect(dialog.getByText('Edge vs market',{exact:true})).toBeVisible()
    await expect(dialog.getByText('Model agreement',{exact:true})).toBeVisible()
    await expect(dialog.getByText(/64% vs 59% = a \+5 percentage-point edge/i)).toBeVisible()
    await expect(helpButton).toHaveAttribute('aria-expanded','true')

    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
    await expect(helpButton).toHaveAttribute('aria-expanded','false')

    const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}
