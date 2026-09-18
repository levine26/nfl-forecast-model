import { test, expect } from '@playwright/test'

const fixtureRequired = process.env.PROPS_FIXTURE_REQUIRED === '1'

async function hasFixture(page) {
  return fixtureRequired || await page.getByText('Puka Nacua').first().isVisible().catch(()=>false)
}

for (const width of [320,390,768,1440]) {
  test('Props board has no essential horizontal overflow at ' + width + 'px',async({page})=>{
    await page.setViewportSize({width,height:1000})
    await page.goto('./#/props')
    await expect(page.getByRole('button',{name:'LevLine Props Research Beta'})).toBeVisible()
    await expect(page.getByRole('heading',{name:'Player markets through the LevLine lens.'})).toBeVisible()
    await expect(page.getByText("ON LEVLINE'S RADAR",{exact:true})).toBeVisible()
    await expect(page.getByText('FULL MARKET',{exact:true})).toBeVisible()

    if (await hasFixture(page)) {
      const puka=page.locator('.lp-board-row').filter({hasText:'Puka Nacua'}).first()
      await expect(puka).toBeVisible()
      await expect(puka).toContainText('76.5')
      await expect(puka).toContainText('83.5')
      await expect(puka).toContainText('OVER')
      await expect(puka).toContainText('MODEL EDGE')

      await puka.locator('summary').click()
      await expect(puka.getByRole('img',{name:/Market line 76.5.*LevLine Fair Line 83.5/i})).toBeVisible()
      await expect(puka.getByText('THE SIGNAL',{exact:true})).toBeVisible()
      await expect(puka.getByText('Advanced Analysis',{exact:true})).toBeVisible()
    } else {
      await expect(page.getByText(/Props publication is waiting for a valid forecast artifact/i)).toBeVisible()
    }

    expect(await page.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth)).toBeFalsy()
  })
}

test('Radar includes only upstream MODEL EDGE and WATCH classifications',async({page})=>{
  await page.goto('./#/props')
  if (!await hasFixture(page)) return

  const radar=page.locator('.lp-radar')
  await expect(radar.getByText('Puka Nacua')).toBeVisible()
  await expect(radar.getByText('Christian McCaffrey')).toBeVisible()
  await expect(radar.getByText('Josh Allen')).toBeVisible()
  await expect(radar.getByText('Research Fixture Receiver')).toHaveCount(0)
  await expect(radar.getByText('MODEL EDGE').first()).toBeVisible()
  await expect(radar.getByText('WATCH').first()).toBeVisible()
})

test('Games is a matchup index before opening a game-specific board',async({page})=>{
  await page.goto('./#/props/games')
  if (!fixtureRequired && !await page.getByText(/BUF|MIA/).first().isVisible().catch(()=>false)) return

  await expect(page.getByRole('heading',{name:'Browse the slate, then go deep.'})).toBeVisible()
  await expect(page.getByText('Josh Allen')).toHaveCount(0)

  const allenGame=page.locator('.lp-game-index-row').filter({hasText:'BUF'}).filter({hasText:'MIA'}).first()
  await expect(allenGame).toBeVisible()
  await allenGame.click()
  await expect(page).toHaveURL(/#\/props\/games\//)

  const allen=page.locator('.lp-board-row').filter({hasText:'Josh Allen'})
  await expect(allen).toContainText('WATCH')
  await allen.locator('summary').click()
  await expect(allen.getByText('Expected dropbacks').first()).toBeVisible()
})

test('Full Market filters, search, sort, and progressive disclosure are interactive',async({page})=>{
  await page.goto('./#/props/all')
  if (!await hasFixture(page)) return

  const full=page.locator('.lp-full-market')
  await full.getByLabel('Search players').fill('Puka')
  await expect(full.getByText('Puka Nacua')).toBeVisible()
  await expect(full.getByText('Josh Allen')).toHaveCount(0)
  await full.getByLabel('Search players').fill('')

  await full.getByLabel('Signal').selectOption('WATCH')
  await expect(full.getByText('Josh Allen')).toBeVisible()
  await expect(full.getByText('Puka Nacua')).toHaveCount(0)

  await full.getByLabel('Signal').selectOption('ALL')
  await full.getByLabel('Sort').selectOption('player')
  const puka=full.locator('.lp-board-row').filter({hasText:'Puka Nacua'})
  await puka.locator('summary').click()
  await puka.getByText('Advanced Analysis',{exact:true}).click()
  await expect(puka.getByText('Model distribution')).toBeVisible()
  await expect(puka.getByText('Forecast timestamp')).toBeVisible()
  await expect(puka.getByText('Market captured')).toBeVisible()
})

test('TD markets use probability and price language instead of a continuous Fair Line chart',async({page})=>{
  await page.goto('./#/props')
  if (!await hasFixture(page)) return

  const cmc=page.locator('.lp-board-row').filter({hasText:'Christian McCaffrey'}).first()
  await expect(cmc).toContainText('-120')
  await expect(cmc).toContainText('64.0%')
  await cmc.locator('summary').click()
  await expect(cmc.getByText('ANYTIME TD',{exact:true})).toBeVisible()
  await expect(cmc.getByText(/64\.0%/).first()).toBeVisible()
  await expect(cmc.locator('.lp-fair-viz')).toHaveCount(0)
})

test('Performance page is empirical-data gated and retains immutable receipts',async({page})=>{
  await page.goto('./#/props/history')
  await expect(page.getByText('Prospective validation, with receipts.')).toBeVisible()
  await expect(page.getByText('Projection Accuracy')).toBeVisible()
  await expect(page.getByText('Probability Calibration')).toBeVisible()
  await expect(page.getByText('Market Performance')).toBeVisible()
  await expect(page.getByText('Betting Performance')).toBeVisible()
  await expect(page.getByText('INSUFFICIENT EVALUATION DATA').first()).toBeVisible()

  if (fixtureRequired || await page.getByText('Puka Nacua').first().isVisible().catch(()=>false)) {
    const receipt=page.getByText('Puka Nacua').first().locator('xpath=ancestor::summary')
    const receiptDetails=receipt.locator('xpath=ancestor::details')
    await receipt.click()
    await expect(receiptDetails.getByText('Original sportsbook line / price')).toBeVisible()
    await expect(receiptDetails.getByText('Forecast timestamp')).toBeVisible()
    await expect(receiptDetails.getByText('Model version')).toBeVisible()
  }
})

test('Props navigation supports keyboard activation and returns to canonical Sunday Signal route',async({page})=>{
  await page.goto('./#/props')
  const games=page.getByRole('button',{name:'Games',exact:true}).first()
  await games.focus()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL(/#\/props\/games$/)

  await page.getByRole('button',{name:/Sunday Signal/i}).click()
  await expect(page).toHaveURL(/#\/forecasts$/)
})

test('legacy Top Signals and All Props aliases resolve to the Board',async({page})=>{
  await page.goto('./#/props/top')
  await expect(page.getByRole('heading',{name:'Player markets through the LevLine lens.'})).toBeVisible()
  await page.goto('./#/props/all')
  await expect(page.getByRole('heading',{name:'Player markets through the LevLine lens.'})).toBeVisible()
})
