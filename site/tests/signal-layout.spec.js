import { expect, test } from '@playwright/test'

const viewports = [
  ['desktop', 1440, 1000],
  ['mobile', 390, 844],
]

for (const [name, width, height] of viewports) {
  test(`${name}: enhanced The Signal stays in normal document flow`, async ({ page }) => {
    await page.setViewportSize({ width, height })
    await page.goto('./')
    await page.locator('[data-game-open]:visible').first().click()

    const signal = page.locator('.ss-plus-signal:visible').first()
    await expect(signal).toBeVisible()

    const layout = await signal.evaluate(element => {
      const card = element.getBoundingClientRect()
      const head = element.querySelector('.ss-plus-signal-head')?.getBoundingClientRect() || null
      const headline = element.querySelector('h2')?.getBoundingClientRect() || null
      const paragraphs = [...element.querySelectorAll(':scope > p')].map(node => node.getBoundingClientRect())
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
