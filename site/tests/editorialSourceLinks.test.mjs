import test from 'node:test'
import assert from 'node:assert/strict'
import { canonicalReportLink } from '../src/editorialSourceLinks.mjs'

test('direct publisher article URLs are retained', () => {
  assert.equal(canonicalReportLink('https://www.nfl.com/news/football-report'), 'https://www.nfl.com/news/football-report')
  assert.equal(canonicalReportLink('https://www.espn.com/nfl/story/_/id/12345/report'), 'https://www.espn.com/nfl/story/_/id/12345/report')
  assert.equal(canonicalReportLink('https://www.chargers.com/news/chiefs-preview'), 'https://www.chargers.com/news/chiefs-preview')
})
test('intermediary URLs and generic landing pages cannot appear as verified citations', () => {
  for (const url of [
    'https://news.google.com/rss/articles/CBMihwFB',
    'https://www.bing.com/news/apiclick.aspx?ref=FexRss',
    'https://www.nfl.com/teams/buffalo-bills/',
    'https://www.espn.com/nfl/team/_/name/buf',
    'https://www.cbssports.com/nfl/standings/',
    'https://example.com/nfl/news',
  ]) assert.equal(canonicalReportLink(url), null, url)
})
test('Bing links unwrap only when the embedded publisher URL is direct', () => {
  const original = 'https://www.nfl.com/news/original-report'
  assert.equal(canonicalReportLink('https://www.bing.com/news/apiclick.aspx?url='+encodeURIComponent(original)),original)
  assert.equal(canonicalReportLink('https://www.bing.com/news/apiclick.aspx?url='+encodeURIComponent('https://www.msn.com/sports/example')),null)
})
test('invalid or non-HTTPS article targets are rejected',()=>{
  assert.equal(canonicalReportLink('http://www.nfl.com/news/report'),null)
  assert.equal(canonicalReportLink(''),null)
})
