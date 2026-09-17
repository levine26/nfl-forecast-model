import { test, expect } from '@playwright/test'

for (const width of [390,1440]) {
  test(`Props research beta is readable without horizontal overflow at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:1000}); await page.goto('./#/props')
    await expect(page.getByText('LEVLINE PROPS')).toBeVisible(); await expect(page.getByText('RESEARCH BETA')).toBeVisible(); await expect(page.getByText('LEVLINE FAIR LINE').first()).toBeVisible(); await expect(page.getByText('Puka Nacua')).toBeVisible(); await expect(page.getByText('NO SIGNAL').first()).toBeVisible()
    expect(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)).toBeFalsy()
  })
}
test('Props history route preserves original-versus-closing concepts',async({page})=>{await page.goto('./#/props/history');await expect(page.getByText('Immutable forecast history')).toBeVisible();await expect(page.getByText(/Original published forecasts never change/i)).toBeVisible()})
test('Props beta can return to canonical Sunday Signal without modifying winner route',async({page})=>{await page.goto('./#/props');await page.getByRole('button',{name:/Sunday Signal/i}).click();await expect(page).toHaveURL(/#\/forecasts$/)})
