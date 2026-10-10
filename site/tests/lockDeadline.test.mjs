import test from 'node:test'
import assert from 'node:assert/strict'
import { scheduledLockMillis, lockCountdownState } from '../src/lockDeadline.js'

test('scheduled lock is exactly two hours before UTC kickoff', () => {
  const game = { kickoff_utc: '2026-10-11T13:30:00+00:00' }
  assert.equal(new Date(scheduledLockMillis(game)).toISOString(), '2026-10-11T11:30:00.000Z')
  assert.equal(lockCountdownState(game, Date.parse('2026-10-11T11:29:59Z')).phase, 'upcoming')
  assert.equal(lockCountdownState(game, Date.parse('2026-10-11T11:30:00Z')).phase, 'overdue')
})
test('does not substitute kickoff as a lock target or conceal a missed lock', () => {
  const game = { kickoff_utc: '2026-10-11T17:00:00Z', lifecycle_status: 'LIVE_FORECAST' }
  assert.equal(lockCountdownState(game, Date.parse('2026-10-11T16:00:00Z')).phase, 'overdue')
  assert.equal(lockCountdownState(game, Date.parse('2026-10-11T17:00:00Z')).phase, 'missed')
})
test('authoritative immutable lock takes precedence over deadline or client time', () => {
  const game = {
    kickoff_utc: '2026-10-09T00:15:00Z',
    lock_timestamp_utc: '2026-10-08T23:55:39Z',
    immutable: true,
    lifecycle_status: 'FINAL_PREGAME',
  }
  const state = lockCountdownState(game, Date.parse('2026-10-09T00:05:00Z'))
  assert.equal(state.phase, 'locked')
  assert.equal(new Date(state.actualLockMillis).toISOString(), '2026-10-08T23:55:39.000Z')
})
test('UTC and daylight-saving offsets are resolved from the canonical kickoff', () => {
  const a = { kickoff_utc: '2026-03-08T18:00:00Z' }
  const b = { kickoff_utc: '2026-11-01T18:00:00Z' }
  assert.equal(new Date(scheduledLockMillis(a)).toISOString(), '2026-03-08T16:00:00.000Z')
  assert.equal(new Date(scheduledLockMillis(b)).toISOString(), '2026-11-01T16:00:00.000Z')
})
test('a postponed kickoff has a new scheduled deadline unless already locked', () => {
  const before = { kickoff_utc: '2026-10-11T17:00:00Z' }
  const after = { kickoff_utc: '2026-10-11T20:00:00Z' }
  assert.equal(scheduledLockMillis(after) - scheduledLockMillis(before), 3 * 60 * 60 * 1000)
  const locked = { ...before, immutable: true, lock_timestamp_utc: '2026-10-11T14:05:00Z' }
  assert.equal(lockCountdownState(locked, Date.parse('2026-10-11T19:00:00Z')).phase, 'locked')
})
test('missing and malformed schedules cannot create false countdowns', () => {
  assert.equal(lockCountdownState({}, Date.now()).phase, 'unknown')
  assert.equal(lockCountdownState({kickoff_utc: 'unparseable'}, Date.now()).phase, 'unknown')
})
