import { test, expect } from '@playwright/test'

const fixtureRequired = process.env.PROPS_FIXTURE_REQUIRED === '1'

for (const width of [390,1440]) {
  test(`Props research beta is readable without horizontal overflow at ${width}px`,async({page})=>{
    await page.setViewportSize({width,height:1000})
    await page.goto('./#/props')
    await expect(page.getByRole('button',{name:'LEVLINE PROPS RESEARCH BETA'})).toBeVisible()
    await expect(page.getByText('RESEARCH BETA').first()).toBeVisible()

    const fairLine=page.getByText('LEVLINE FAIR LINE').first()
    if (fixtureRequired || await fairLine.isVisible().catch(()=>false)) {
      await expect(fairLine).toBeVisible()
      await expect(page.getByText('Puka Nacua')).toBeVisible()
      await expect(page.getByText('NO SIGNAL').first()).toBeVisible()
    } else {
      await expect(page.getByText(/Props publication is waiting for a valid forecast artifact/i)).toBeVisible()
    }

    expect(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)).toBeFalsy()
  })
}

test('Props history route preserves original-versus-closing concepts',async({page})=>{
  await page.goto('./#/props/history')
  await expect(page.getByText('Immutable forecast history')).toBeVisible()
  const populated=page.getByText(/Original published forecasts never change/i)
  if (fixtureRequired || await populated.isVisible().catch(()=>false)) {
    await expect(populated).toBeVisible()
  } else {
    await expect(page.getByText(/Grading never rewrites the original forecast/i)).toBeVisible()
  }
})

test('Props beta can return to canonical Sunday Signal without modifying winner route',async({page})=>{
  await page.goto('./#/props')
  await page.getByRole('button',{name:/Sunday Signal/i}).click()
  await expect(page).toHaveURL(/#\/forecasts$/)
})
