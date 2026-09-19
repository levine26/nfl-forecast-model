import { test, expect } from '@playwright/test'
import { readFileSync } from 'node:fs'

const propsSource = readFileSync(new URL('../src/PropsResearchBeta.jsx', import.meta.url), 'utf8')

const fixtureRequired = process.env.PROPS_FIXTURE_REQUIRED === '1'

async function hasFixture(page) {
  return fixtureRequired || await page.locator('.lp-board-row > summary .lp-row-player strong').filter({hasText:'Puka Nacua'}).first().isVisible().catch(()=>false)
}

function boardRow(scope,name) {
  return scope.locator('.lp-board-row').filter({hasText:name}).first()
}

test('Performance page is empirical-data gated and retains immutable receipts',async({page})=>{
  test.setTimeout(60000)
  for (const label of [
    'Prospective validation, with receipts.',
    'Projection Accuracy',
    'Probability Calibration',
    'Market Performance',
    'Betting Performance',
    'INSUFFICIENT EVALUATION DATA',
    'Original sportsbook line / price',
    'Forecast timestamp',
    'Model version',
  ]) expect(propsSource).toContain(label)

  await page.goto('./#/props/history')
  const performance=page.locator('.lp-performance')
  await expect(performance).toBeVisible()
  await expect(performance.locator('.lp-performance-head h1')).toHaveCount(1)
  await expect(performance.locator('.lp-performance-concepts article')).toHaveCount(4)
  await expect(performance.locator('.lp-performance-concepts article b')).toHaveCount(4)

  const receipts=performance.locator('.lp-receipt')
  if (fixtureRequired) await expect(receipts).toHaveCount(4)
  const receiptDetails=receipts.first()
  if (await receiptDetails.isVisible().catch(()=>false)) {
    await receiptDetails.locator(':scope > summary').click()
    await expect(receiptDetails).toHaveJSProperty('open',true)
    await expect(receiptDetails.locator('.lp-receipt-grid .lp-metric')).toHaveCount(8)
  }
})

for (const width of [320,390,430,768,1440]) {
  test('Props board has no essential horizontal overflow at ' + width + 'px',async({page})=>{
    await page.setViewportSize({width,height:1000})
    await page.goto('./#/props')
    await expect(page.getByRole('button',{name:'LevLine Props Research Beta'})).toBeVisible()
    await expect(page.getByRole('heading',{name:'Player markets through the LevLine lens.'})).toBeVisible()

    if (await hasFixture(page)) {
      await expect(page.getByText("ON LEVLINE'S RADAR",{exact:true})).toBeVisible()
      await expect(page.getByText('FULL MARKET',{exact:true})).toBeVisible()
      const puka=boardRow(page,'Puka Nacua')
      await expect(puka.locator(':scope > summary')).toContainText('76.5')
      await expect(puka.locator(':scope > summary')).toContainText('83.5')
      await expect(puka.locator(':scope > summary')).toContainText('OVER')
      await expect(puka.locator(':scope > summary')).toContainText('MODEL EDGE')

      await puka.locator(':scope > summary').click()
      await expect(puka.getByRole('img',{name:/Market line 76.5.*LevLine Fair Line 83.5/i})).toBeVisible()
      await expect(puka.getByText('THE SIGNAL',{exact:true})).toBeVisible()
      await expect(puka.locator('.lp-advanced > summary')).toBeVisible()
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
  await expect(radar.locator('.lp-row-player strong',{hasText:'Puka Nacua'}).first()).toBeVisible()
  await expect(radar.locator('.lp-row-player strong',{hasText:'Christian McCaffrey'}).first()).toBeVisible()
  await expect(radar.locator('.lp-row-player strong',{hasText:'Josh Allen'}).first()).toBeVisible()
  await expect(radar.locator('.lp-row-player strong',{hasText:'Research Fixture Receiver'})).toHaveCount(0)
  await expect(radar.locator('.lp-board-row.model-edge').first()).toBeVisible()
  await expect(radar.locator('.lp-board-row.watch').first()).toBeVisible()
})

test('Games is a matchup index before opening a game-specific board',async({page})=>{
  await page.goto('./#/props/games')
  await expect(page.getByRole('heading',{name:'Browse the slate, then go deep.'})).toBeVisible()
  if (!fixtureRequired && !await page.locator('.lp-game-index-row').first().isVisible().catch(()=>false)) {
    await expect(page.getByText(/No game-level Props slate is published yet/i)).toBeVisible()
    return
  }

  await expect(page.locator('.lp-row-player strong',{hasText:'Josh Allen'})).toHaveCount(0)
  const allenGame=page.locator('.lp-game-index-row').filter({hasText:'BUF'}).filter({hasText:'MIA'}).first()
  await expect(allenGame).toBeVisible()
  await allenGame.click()
  await expect(page).toHaveURL(/#\/props\/games\//)

  const allen=boardRow(page,'Josh Allen')
  await expect(allen.locator(':scope > summary')).toContainText('WATCH')
  await allen.locator(':scope > summary').click()
  await expect(allen.getByText('Expected dropbacks').first()).toBeVisible()
})

test('Full Market filters, search, sort, and progressive disclosure are interactive',async({page})=>{
  await page.goto('./#/props/all')
  if (!await hasFixture(page)) return

  const full=page.locator('.lp-full-market')
  await full.getByLabel('Search players').fill('Puka')
  await expect(full.locator('.lp-row-player strong',{hasText:'Puka Nacua'}).first()).toBeVisible()
  await expect(full.locator('.lp-row-player strong',{hasText:'Josh Allen'})).toHaveCount(0)
  await full.getByLabel('Search players').fill('')

  await full.getByLabel('Signal').selectOption('WATCH')
  await expect(full.locator('.lp-row-player strong',{hasText:'Josh Allen'}).first()).toBeVisible()
  await expect(full.locator('.lp-row-player strong',{hasText:'Puka Nacua'})).toHaveCount(0)

  await full.getByLabel('Signal').selectOption('ALL')
  await full.getByLabel('Sort').selectOption('player')
  const puka=boardRow(full,'Puka Nacua')
  await puka.locator(':scope > summary').click()
  await puka.locator('.lp-advanced > summary').click()
  await expect(puka.getByText('Model distribution')).toBeVisible()
  await expect(puka.getByText('Forecast timestamp')).toBeVisible()
  await expect(puka.getByText('Market captured')).toBeVisible()
})

test('TD markets use probability and price language instead of a continuous Fair Line chart',async({page})=>{
  await page.goto('./#/props')
  if (!await hasFixture(page)) return

  const cmc=boardRow(page,'Christian McCaffrey')
  await expect(cmc.locator(':scope > summary')).toContainText('-120')
  await expect(cmc.locator(':scope > summary')).toContainText('64.0%')
  await cmc.locator(':scope > summary').click()
  await expect(cmc.getByText('ANYTIME TD',{exact:true})).toBeVisible()
  await expect(cmc.getByText(/64\.0%/).first()).toBeVisible()
  await expect(cmc.locator('.lp-fair-viz')).toHaveCount(0)
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
