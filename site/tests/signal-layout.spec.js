import { expect, test } from '@playwright/test'

const viewports = [
  ['desktop', 1440, 1000],
  ['mobile', 390, 844],
]

for (const [name, width, height] of viewports) {
  test(`${name}: The Signal stays in normal document flow`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('./')
    const openRows = width <= 768
      ? page.locator('.ss-exp-mobile-board:visible > button')
      : page.locator('.ss-exp-board-rows:visible > button')
    await expect(openRows.first()).toBeVisible()
    await openRows.first().click()

    const signal = page.locator('.ss-exp-signal:visible').first()
    await expect(signal).toBeVisible()

    const layout = await signal.evaluate(element => {
      const card = element.getBoundingClientRect()
      const head = element.querySelector(':scope > header')?.getBoundingClientRect() || null
      const headline = element.querySelector(':scope > h2')?.getBoundingClientRect() || null
      const paragraphs = [...element.querySelectorAll(':scope > .ss-exp-bottom-line')].map(node => node.getBoundingClientRect())
      const style = getComputedStyle(element)
      return {
        display: style.display,
        cardWidth: card.width,
        headWidth: head?.width || 0,
        headBottom: head?.bottom || 0,
        headlineWidth: headline?.width || 0,
        headlineTop: headline?.top || 0,
        headlineBottom: headline?.bottom || 0,
        paragraphWidths: paragraphs.map(rect => rect.width),
        firstParagraphTop: paragraphs[0]?.top || 0,
      }
    })

    expect(layout.display).toBe('block')
    expect(layout.headWidth).toBeGreaterThan(layout.cardWidth * 0.7)
    if (layout.headlineWidth) {
      expect(layout.headlineWidth).toBeGreaterThan(layout.cardWidth * 0.55)
      expect(layout.headlineTop).toBeGreaterThanOrEqual(layout.headBottom - 2)
    }
    for (const paragraphWidth of layout.paragraphWidths) {
      expect(paragraphWidth).toBeGreaterThan(layout.cardWidth * 0.55)
    }
    if (layout.firstParagraphTop && layout.headlineBottom) {
      expect(layout.firstParagraphTop).toBeGreaterThanOrEqual(layout.headlineBottom - 2)
    }

    const overflow = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)
    expect(overflow).toBeLessThanOrEqual(1)
  })
}
