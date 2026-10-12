import { expect, test } from '@playwright/test'

const csv = [
  'game_id,season,week,away_team,home_team,pick,final_home_prob,expected_margin,spread_line,lock_status,recovery_source_commit_sha,recovery_source_prediction_timestamp_utc,kickoff_utc,winner_correct,actual_home_score,actual_away_score',
  '2026_05_PHI_JAX,2026,5,PHI,JAX,JAX,0.7729426227299359,10.699215207483226,8.5,RECOVERED_MISSED_LOCK,5f611ab21ab16db51c3e432740fba79c40d647fb,2026-10-11T07:47:30Z,2026-10-11T13:30:00Z,True,19,17',
  '2026_05_FAKE_MIA,2026,5,FAKE,MIA,MIA,0.70,3,1,RECOVERED_MISSED_LOCK,,2026-10-11T14:00:00Z,2026-10-11T13:30:00Z,True,20,14',
].join('\\n') + '\\n'

test('verified missed-lock forecast is visible but excluded from official calibration', async ({page}) => {
  await page.route('**/data/prediction_history.csv', route => route.fulfill({status:200,contentType:'text/csv',body:csv}))
  await page.goto('./#/history')
  const recovered=page.locator('.ss-exp-history-list > button').filter({hasText:'PHI @ JAX'})
  await expect(recovered).toBeVisible()
  await expect(recovered).toContainText('Recovered pregame · no official lock')
  await expect(page.locator('.ss-exp-history-list')).not.toContainText('FAKE @ MIA')
  await expect(page.locator('.ss-exp-calibration')).toContainText('No graded picks')
  await recovered.click()
  await expect(page.locator('.ss-exp-receipt-hero')).toContainText('RECOVERED PREGAME FORECAST')
  await expect(page.locator('.ss-exp-receipt-hero')).toContainText('official lock was missed')
  await expect(page.locator('.ss-exp-receipt-grid')).toContainText('PHI 17 – JAX 19')
  await expect(page.locator('.ss-history-receipt-details')).toContainText('RECOVERED PREGAME FORECAST DETAILS')
})
