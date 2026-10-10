import assert from 'node:assert/strict'
import test from 'node:test'
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

test('complete validated provider Read with two direct publisher families is eligible',()=>{
  assert.equal(hasPublishedHumanRead(preview()),true)
})

test('deterministic template text cannot masquerade as an accepted human Read',()=>{
  const a=preview()
  a.editorial_voice.copilot_researched=false
  a.headline='Bears–Packers centers on CHI: injury status'
  assert.equal(hasPublishedHumanRead(a),false)
})

test('a provider flag cannot bypass direct attribution or two-paragraph shape',()=>{
  const a=preview()
  a.reported_sources=[
    {source_url:'https://news.google.com/rss/articles/abc'},
    {source_url:'https://www.bing.com/news/search?q=example'},
  ]
  assert.equal(hasPublishedHumanRead(a),false)
  a.reported_sources=preview().reported_sources
  a.paragraphs=['only one paragraph']
  assert.equal(hasPublishedHumanRead(a),false)
})

test('two URLs from one publisher are not independent',()=>{
  const a=preview()
  a.reported_sources=[
    {source_url:'https://www.espn.com/nfl/story/_/id/12345/article'},
    {source_url:'https://www.espn.com/nfl/story/_/id/45678/other'},
  ]
  assert.equal(hasPublishedHumanRead(a),false)
})

test('missing preview is a pending Read, not an excuse to render templates',()=>{
  assert.equal(hasPublishedHumanRead(null),false)
  assert.equal(hasPublishedHumanRead({headline:'An NFL preview',paragraphs:['a','b']}),false)
})
