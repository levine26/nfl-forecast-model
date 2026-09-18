import test from 'node:test'
import assert from 'node:assert/strict'
import {
  directionFor,
  formatAmerican,
  formatDifference,
  formatLine,
  formatPercent,
  formatPoints,
  marketFamily,
  primaryMarketPrice,
  propLabel,
  qualityLabel,
  rangeText,
  sortForecasts,
  sortForBrowse,
  sortTopSignals,
  unitFor,
} from '../src/propsPresentation.js'

test('probability and price formatting is deterministic',()=>{
  assert.equal(formatPercent(.618),'61.8%')
  assert.equal(formatPoints(.094),'+9.4 pp')
  assert.equal(formatPoints(-.012),'-1.2 pp')
  assert.equal(formatAmerican(-162),'-162')
  assert.equal(formatAmerican(135),'+135')
})

test('fair-line formatting preserves supplied display unit',()=>{
  assert.equal(formatLine(83.5),'83.5')
  assert.equal(formatDifference(7,'yds'),'+7.0 yds')
  assert.equal(formatDifference(-1.5,'rec'),'-1.5 rec')
  assert.equal(formatDifference(.5,'TD'),'+0.5 TD')
})

test('market labels, range and price helpers support line and TD cards',()=>{
  const line={prop_type:'receiving_yards',market_kind:'OVER_UNDER',market:{over_price_american:-110},model:{prediction_interval:{low:55,high:113,coverage:.8}},data_quality:{state:'HIGH',confidence:'HIGH'}}
  const td={prop_type:'anytime_td',market_kind:'BINARY_TD',market:{td_price_american:120}}
  assert.equal(propLabel('receiving_yards'),'Receiving Yards')
  assert.equal(qualityLabel(line),'HIGH data · HIGH confidence')
  assert.equal(rangeText(line),'80% model range: 55–113')
  assert.equal(formatAmerican(primaryMarketPrice(line)),'-110')
  assert.equal(formatAmerican(primaryMarketPrice(td)),'+120')
  assert.equal(unitFor(line),'YDS')
  assert.equal(marketFamily('receptions'),'RECEPTIONS')
})

test('direction is a presentation of supplied Fair Line versus market and never changes signal state',()=>{
  assert.equal(directionFor({market_kind:'OVER_UNDER',model:{line_difference:7}}),'OVER')
  assert.equal(directionFor({market_kind:'OVER_UNDER',model:{line_difference:-2}}),'UNDER')
  assert.equal(directionFor({market_kind:'OVER_UNDER',model:{line_difference:0}}),'MARKET ALIGNED')
  assert.equal(directionFor({prop_type:'anytime_td',market_kind:'BINARY_TD',model:{td_probability:.64}}),'ANYTIME TD')
})

test('legacy forecast sorting prioritizes supplied signal state then edge magnitude',()=>{
  const rows=[
    {player:'Watch',signal_state:'WATCH',model:{probability_edge:.20}},
    {player:'No signal',signal_state:'NO SIGNAL',model:{probability_edge:.40}},
    {player:'Edge B',signal_state:'MODEL EDGE',model:{probability_edge:.04}},
    {player:'Edge A',signal_state:'MODEL EDGE',model:{probability_edge:.09}},
  ]
  assert.deepEqual(sortForecasts(rows).map(row=>row.player),['Edge A','Edge B','Watch','No signal'])
})

test('Top Signals never promotes WATCH or NO SIGNAL rows',()=>{
  const rows=[
    {forecast_id:'watch',player:'Watch',signal_state:'WATCH',model:{probability_edge:.50},data_quality:{state:'HIGH'},kickoff_utc:'2026-09-20T17:00:00Z'},
    {forecast_id:'edge-medium',player:'Edge Medium',signal_state:'MODEL EDGE',model:{probability_edge:.10},data_quality:{state:'MEDIUM'},kickoff_utc:'2026-09-20T17:00:00Z'},
    {forecast_id:'edge-high',player:'Edge High',signal_state:'MODEL EDGE',model:{probability_edge:.10},data_quality:{state:'HIGH'},kickoff_utc:'2026-09-20T17:00:00Z'},
    {forecast_id:'no',player:'No Signal',signal_state:'NO SIGNAL',model:{probability_edge:.90},data_quality:{state:'HIGH'},kickoff_utc:'2026-09-20T17:00:00Z'},
  ]
  assert.deepEqual(sortTopSignals(rows).map(row=>row.player),['Edge High','Edge Medium'])
})

test('All Props browse sorting is deterministic',()=>{
  const rows=[
    {forecast_id:'b',player:'Beta',signal_state:'WATCH',kickoff_utc:'2026-09-20T20:00:00Z',model:{line_difference:1}},
    {forecast_id:'a',player:'Alpha',signal_state:'MODEL EDGE',kickoff_utc:'2026-09-20T18:00:00Z',model:{line_difference:3}},
  ]
  assert.deepEqual(sortForBrowse(rows,'player').map(row=>row.player),['Alpha','Beta'])
  assert.deepEqual(sortForBrowse(rows,'kickoff').map(row=>row.player),['Alpha','Beta'])
  assert.deepEqual(sortForBrowse(rows,'fair-line-gap').map(row=>row.player),['Alpha','Beta'])
})
