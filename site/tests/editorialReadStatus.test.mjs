import assert from 'node:assert/strict'
import test from 'node:test'
import {readFileSync} from 'node:fs'
import {hasPublishedHumanRead} from '../src/editorialReadStatus.mjs'

const preview = () => ({
  headline:'Bills protection faces a test from the Rams front',
  paragraphs:['A distinctive provider-written matchup paragraph.','A canonical forecast paragraph.'],
  editorial_voice:{copilot_researched:true,two_paragraph_contract:true},
  reported_sources:[
    {source_name:'ESPN',source_url:'https://www.espn.com/nfl/story/_/id/12345/article'},
    {source_name:'NFL',source_url:'https://www.nfl.com/news/example-report'},
  ],
})

const accepted = () => ({
  status:'healthy',
  games_expected:15,
  games_with_structurally_eligible_human_reads:15,
  games_rejected:0,
  issues:{},
  article_resolution_verified:true,
  claim_support_verified:true,
})

test('verified full-slate acceptance plus source and provider shape enables HUMAN display',()=>{
  assert.equal(hasPublishedHumanRead(preview(),accepted(),15),true)
})

test('no audit, stale audit or unverified article/claim blocks the HUMAN Read',()=>{
  assert.equal(hasPublishedHumanRead(preview()),false)
  assert.equal(hasPublishedHumanRead(preview(),undefined,15),false)
  const a=accepted()
  a.article_resolution_verified=false
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.article_resolution_verified=true
  a.claim_support_verified=false
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.claim_support_verified=true
  a.status='structurally_eligible'
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.status='healthy'
  a.games_expected=14
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.games_expected=15
  a.games_with_structurally_eligible_human_reads=14
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.games_with_structurally_eligible_human_reads=15
  a.games_rejected=1
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
  a.games_rejected=0
  a.issues={'2026_05_BUF_LA':['unsupported_claim']}
  assert.equal(hasPublishedHumanRead(preview(),a,15),false)
})

test('deterministic template text cannot masquerade as an accepted human Read',()=>{
  const a=preview()
  a.editorial_voice.copilot_researched=false
  a.headline='Bears–Packers centers on CHI: injury status'
  assert.equal(hasPublishedHumanRead(a,accepted(),15),false)
})

test('a provider flag cannot bypass direct attribution or two-paragraph shape',()=>{
  const a=preview()
  a.reported_sources=[
    {source_url:'https://news.google.com/rss/articles/abc'},
    {source_url:'https://www.bing.com/news/search?q=example'},
  ]
  assert.equal(hasPublishedHumanRead(a,accepted(),15),false)
  a.reported_sources=preview().reported_sources
  a.paragraphs=['only one paragraph']
  assert.equal(hasPublishedHumanRead(a,accepted(),15),false)
})

test('two URLs from one publisher are not independent',()=>{
  const a=preview()
  a.reported_sources=[
    {source_url:'https://www.espn.com/nfl/story/_/id/12345/article'},
    {source_url:'https://www.espn.com/nfl/story/_/id/45678/other'},
  ]
  assert.equal(hasPublishedHumanRead(a,accepted(),15),false)
})

test('missing preview is a pending Read, not an excuse to render templates',()=>{
  assert.equal(hasPublishedHumanRead(null,accepted(),15),false)
  assert.equal(hasPublishedHumanRead({headline:'An NFL preview',paragraphs:['a','b']},accepted(),15),false)
})

test('site must load independent acceptance and apply it to board, mobile and matchup reads',()=>{
  const app=readFileSync(new URL('../src/AppSignal.jsx', import.meta.url),'utf8')
  assert.match(app,/fetchJSON\('context_source_status\.json',\{\}\)/)
  assert.match(app,/setEditorialAcceptance\(sourceStatusRows\?\.editorial_acceptance\|\|null\)/)
  assert.match(app,/hasPublishedHumanRead\(preview,acceptance,expectedGames\)/)
  assert.match(app,/<TheSignal preview=\{preview\} compact acceptance=\{acceptance\} expectedGames=\{expectedGames\}\/>/)
  assert.match(app,/<TheSignal preview=\{preview\} acceptance=\{acceptance\} expectedGames=\{expectedGames\}\/>/)
})
