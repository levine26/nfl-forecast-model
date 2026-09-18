import { test, expect } from '@playwright/test'

const fixtureRequired = process.env.PROPS_FIXTURE_REQUIRED === '1'

for (const width of [320,390,768,1440]) {
  test('Props V1 has no essential horizontal overflow at ' + width + 'px',async({page})=>{
    await page.setViewportSize({width,height:1000})
    await page.goto('./#/props')
    await expect(page.getByRole('button',{name:'LevLine Props Research Beta'})).toBeVisible()
    await expect(page.getByText('Fair lines first. Market comparison second.')).toBeVisible()

    const puka=page.getByText('Puka Nacua')
    if (fixtureRequired || await puka.isVisible().catch(()=>false)) {
      await expect(puka).toBeVisible()
      await expect(page.getByText('Christian McCaffrey')).toBeVisible()
      await expect(page.getByText('MODEL EDGE').first()).toBeVisible()
      await expect(page.getByText('OVER 76.5')).toBeVisible()
      await expect(page.getByRole('img',{name:/Market line 76.5.*LevLine Fair Line 83.5/i})).toBeVisible()
    } else {
      await expect(page.getByText(/Props publication is waiting for a valid forecast artifact/i)).toBeVisible()
    }

    expect(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)).toBeFalsy()
  })
}

test('Top Signals contains only upstream MODEL EDGE forecasts and handles an empty filtered state',async({page})=>{
  await page.goto('./#/props')
  if (!fixtureRequired && !await page.getByText('Puka Nacua').isVisible().catch(()=>false)) return
  await expect(page.getByText('Puka Nacua')).toBeVisible()
  await expect(page.getByText('Christian McCaffrey')).toBeVisible()
  await expect(page.getByText('Josh Allen')).toHaveCount(0)
  await expect(page.getByText('Research Fixture Receiver')).toHaveCount(0)

  await page.getByRole('button',{name:'QB',exact:true}).click()
  await expect(page.getByText(/No MODEL EDGE forecasts match this view/i)).toBeVisible()
  await expect(page.getByText(/not promoting a WATCH or NO SIGNAL forecast/i)).toBeVisible()
})

test('Games view groups the slate and preserves WATCH and NO SIGNAL states',async({page})=>{
  await page.goto('./#/props/games')
  if (!fixtureRequired && !await page.getByText('Josh Allen').isVisible().catch(()=>false)) return
  await expect(page.getByText('Josh Allen')).toBeVisible()
  await expect(page.getByText('Research Fixture Receiver')).toBeVisible()
  await expect(page.getByText('WATCH').first()).toBeVisible()
  await expect(page.getByText('NO SIGNAL').first()).toBeVisible()

  const allen=page.getByText('Josh Allen').locator('xpath=ancestor::summary')
  const allenDetails=allen.locator('xpath=ancestor::details')
  await allen.click()
  await expect(allenDetails.getByText('Expected dropbacks').first()).toBeVisible()
})

test('All Props filters, search, sort, and progressive disclosure are interactive',async({page})=>{
  await page.goto('./#/props/all')
  if (!fixtureRequired && !await page.getByText('Puka Nacua').isVisible().catch(()=>false)) return

  await page.getByLabel('Search players').fill('Puka')
  await expect(page.getByText('Puka Nacua')).toBeVisible()
  await expect(page.getByText('Josh Allen')).toHaveCount(0)
  await page.getByLabel('Search players').fill('')

  await page.getByRole('button',{name:'Watch',exact:true}).click()
  await expect(page.getByText('Josh Allen')).toBeVisible()
  await expect(page.getByText('Puka Nacua')).toHaveCount(0)

  await page.getByRole('button',{name:'All',exact:true}).last().click()
  await page.getByLabel('Sort props').selectOption('player')
  const pukaSummary=page.getByText('Puka Nacua').locator('xpath=ancestor::summary')
  const pukaDetails=pukaSummary.locator('xpath=ancestor::details')
  await pukaSummary.click()
  await expect(pukaDetails.getByText('Model distribution')).toBeVisible()
  await expect(pukaDetails.getByText('Forecast timestamp')).toBeVisible()
  await expect(pukaDetails.getByText('Market captured')).toBeVisible()
})

test('TD markets use probability language rather than forcing a continuous Fair Line chart',async({page})=>{
  await page.goto('./#/props')
  if (!fixtureRequired && !await page.getByText('Christian McCaffrey').isVisible().catch(()=>false)) return
  const card=page.getByText('Christian McCaffrey').locator('xpath=ancestor::article')
  await expect(card.locator('.lp-direction').getByText('ANYTIME TD',{exact:true})).toBeVisible()
  await expect(card.getByText('64.0%').first()).toBeVisible()
  await expect(card.locator('.lp-fair-viz')).toHaveCount(0)
})

test('Performance page is empirical-data gated and retains immutable receipts',async({page})=>{
  await page.goto('./#/props/history')
  await expect(page.getByText('Prospective validation, with receipts.')).toBeVisible()
  await expect(page.getByText('Projection Accuracy')).toBeVisible()
  await expect(page.getByText('Probability Calibration')).toBeVisible()
  await expect(page.getByText('Market Performance')).toBeVisible()
  await expect(page.getByText('Betting Performance')).toBeVisible()
  await expect(page.getByText('INSUFFICIENT EVALUATION DATA').first()).toBeVisible()

  const pukaName=page.getByText('Puka Nacua',{exact:true}).first()
  if (fixtureRequired || await pukaName.isVisible().catch(()=>false)) {
    const receiptDetails=pukaName.locator('xpath=ancestor::details[contains(@class,"lp-receipt")][1]')
    await expect(receiptDetails).toBeVisible()
    await receiptDetails.evaluate(element=>{ element.open=true })
    await expect(receiptDetails.getByText('Original sportsbook line / price')).toBeVisible()
    await expect(receiptDetails.getByText('Forecast timestamp')).toBeVisible()
    await expect(receiptDetails.getByText('Model version')).toBeVisible()
  }
})

test('Props navigation supports keyboard activation and returns to canonical Sunday Signal route',async({page})=>{
  await page.goto('./#/props')
  const allProps=page.getByRole('button',{name:'All Props'})
  await allProps.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#\/props\/all$/)

  await page.getByRole('button',{name:/Sunday Signal/i}).click()
  await expect(page).toHaveURL(/#\/forecasts$/)
})
