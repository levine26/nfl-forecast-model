import assert from 'node:assert/strict'
import test from 'node:test'
import {OFFICIAL_LOCK_LEAD_MINUTES, officialLockTiming, serverClockOffsetMs} from '../src/officialLockCountdown.mjs'

const game = (kickoff_utc, rest = {}) => ({kickoff_utc, lifecycle_status:'LIVE_FORECAST', immutable:false, ...rest})

test('counts down to official T-120, not kickoff (early Week 5 game)', () => {
  const target = officialLockTiming(game('2026-10-11T13:30:00Z'), Date.parse('2026-10-10T15:30:00Z'))
  assert.equal(OFFICIAL_LOCK_LEAD_MINUTES, 120)
  assert.equal(target.state, 'countdown')
  assert.equal(target.scheduledLockUtc, '2026-10-11T11:30:00.000Z')
  assert.equal(Date.parse('2026-10-11T13:30:00Z')-Date.parse(target.scheduledLockUtc), 120*60_000)
})

test('per-game kickoff differences produce distinct lock times', () => {
  const early=officialLockTiming(game('2026-10-11T13:30:00Z'),0)
  const late=officialLockTiming(game('2026-10-12T00:20:00Z'),0)
  assert.equal(early.scheduledLockUtc,'2026-10-11T11:30:00.000Z')
  assert.equal(late.scheduledLockUtc,'2026-10-11T22:20:00.000Z')
})

test('missed deadline remains LOCK DUE, never a false final or kickoff countdown', () => {
  const at=officialLockTiming(game('2026-10-11T13:30:00Z'), Date.parse('2026-10-11T11:30:00Z'))
  const late=officialLockTiming(game('2026-10-11T13:30:00Z'), Date.parse('2026-10-11T12:10:00Z'))
  assert.equal(at.state,'due')
  assert.equal(late.state,'due')
  assert.equal(late.scheduledLockUtc,'2026-10-11T11:30:00.000Z')
})

test('immutable locks use actual receipt and have no active countdown even if late', () => {
  const locked=officialLockTiming(game('2026-10-11T13:30:00Z',{immutable:true,lifecycle_status:'FINAL_PREGAME',lock_timestamp_utc:'2026-10-11T13:11:00Z'}),Date.parse('2026-10-11T12:00:00Z'))
  assert.deepEqual(locked,{state:'locked',actualLockUtc:'2026-10-11T13:11:00Z',scheduledLockUtc:null})
})

test('a postponement changes an unlocked game deadline without rewriting receipts', () => {
  const now=Date.parse('2026-10-11T12:00:00Z')
  assert.equal(officialLockTiming(game('2026-10-11T13:30:00Z'),now).state,'due')
  const postponed=officialLockTiming(game('2026-10-11T19:30:00Z'),now)
  assert.equal(postponed.state,'countdown')
  assert.equal(postponed.scheduledLockUtc,'2026-10-11T17:30:00.000Z')
})

test('UTC arithmetic survives daylight saving transitions and offset inputs', () => {
  assert.equal(officialLockTiming(game('2026-11-01T13:00:00Z'),0).scheduledLockUtc,'2026-11-01T11:00:00.000Z')
  assert.equal(officialLockTiming(game('2026-11-01T08:00:00-05:00'),0).scheduledLockUtc,'2026-11-01T11:00:00.000Z')
})

test('missing/invalid kickoff never starts a fabricated countdown', () => {
  assert.equal(officialLockTiming(game(''),0).state,'unavailable')
  assert.equal(officialLockTiming(game('not-a-date'),0).state,'unavailable')
})

test('client-clock variations affect displayed due status but cannot create a receipt', () => {
  const g=game('2026-10-11T13:30:00Z')
  assert.equal(officialLockTiming(g,Date.parse('2026-10-11T11:29:00Z')).state,'countdown')
  assert.equal(officialLockTiming(g,Date.parse('2026-10-11T11:31:00Z')).state,'due')
  assert.equal(officialLockTiming(g,Date.parse('2026-10-11T11:31:00Z')).actualLockUtc,null)
})

test('in-progress game without immutable receipt must not claim a lock', () => {
  const result=officialLockTiming(game('2026-10-11T13:30:00Z',{lifecycle_status:'IN_PROGRESS'}),Date.parse('2026-10-11T14:00:00Z'))
  assert.equal(result.state,'due')
})


test('server Date corrects a five-minute-slow client clock', () => {
  const remote='Sat, 10 Oct 2026 16:00:00 GMT'
  const start=Date.parse('2026-10-10T15:54:59Z')
  const finish=Date.parse('2026-10-10T15:55:01Z')
  assert.equal(serverClockOffsetMs(remote,start,finish),5*60_000)
  const realDeadline=Date.parse('2026-10-11T11:30:00Z')
  const localClock=realDeadline-5*60_000
  const g=game('2026-10-11T13:30:00Z')
  assert.equal(officialLockTiming(g,localClock).state,'countdown')
  assert.equal(officialLockTiming(g,localClock+serverClockOffsetMs(remote,start,finish)).state,'due')
})

test('invalid or backwards server timing does not invent clock correction', () => {
  const begin=Date.parse('2026-10-10T15:59:00Z')
  assert.equal(serverClockOffsetMs('',begin,begin+100),null)
  assert.equal(serverClockOffsetMs('Sat, 10 Oct 2026 16:00:00 GMT',begin+100,begin),null)
})
