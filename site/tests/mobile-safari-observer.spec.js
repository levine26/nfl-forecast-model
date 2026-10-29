import { expect, test } from '@playwright/test'
import { readFileSync } from 'node:fs'

// Root-wide MutationObservers run on every child-list change. Writing the
// same textContent unconditionally creates another child-list mutation and
// can keep WebKit in a feedback loop until its renderer is terminated.
test('presentation observer never unconditionally rewrites unchanged help text', async () => {
  const source = readFileSync(new URL('../src/ExperienceLayer.jsx', import.meta.url), 'utf8')
  expect(source).toContain("if(node.textContent!=='How LevLine Works →')node.textContent='How LevLine Works →'")
  expect(source).not.toContain("forEach(node=>{node.textContent='How LevLine Works →'})")
})

for (const [name,width,height] of [['mobile',390,844],['desktop',1440,900]]) {
  test(`${name}: homepage and game route remain interactive without recursive DOM churn`, async ({page}) => {
    await page.setViewportSize({width,height})
    await page.goto('./')
    const rows = width <= 768 ? page.locator('.ss-exp-mobile-board:visible > button') : page.locator('.ss-exp-board-rows:visible > button')
    await expect(rows.first()).toBeVisible()
    await rows.first().click()
    await expect(page).toHaveURL(/#\\/game\\//)
    await expect(page.locator('.ss-clarity-shell:visible')).toBeVisible()
    // Let asynchronous portal/observer updates settle and verify that the page
    // remains capable of navigating (not trapped in a mutation microtask loop).
    await page.waitForTimeout(350)
    await page.evaluate(() => { window.location.hash = '#/forecasts' })
    await expect(page).toHaveURL(/#\\/forecasts/)
    await expect(rows.first()).toBeVisible()
  })
}
