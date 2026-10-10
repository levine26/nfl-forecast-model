import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  scheduledLockUtc,
  readLockLifecycle,
  clockOffsetFromHttpDate,
} from '../src/lockLifecycle.js'

const game = {
  kickoff_utc: '2026-10-11T13:30:00Z',
  lifecycle_status: 'LIVE_FORECAST',
  immutable: false,
  lock_timestamp_utc: null,
}

test('counts down to T-120 rather than the kickoff', () => {
  assert.equal(scheduledLockUtc(game), '2026-10-11T11:30:00.000Z')
  const now = Date.parse('2026-10-11T10:30:00Z')
  assert.deepEqual(readLockLifecycle(game, now), {
    key: 'forecast', label: 'LIVE FORECAST', detail: 'Locks in 1h 0m',
  })
})

test('overdue lock is not advertised as live or a kickoff countdown', () => {
  const state = readLockLifecycle(game, Date.parse('2026-10-11T11:31:00Z'))
  assert.equal(state.key, 'overdue')
  assert.equal(state.label, 'LOCK DUE')
  assert.match(state.detail, /deadline passed/)
})

test('actual lock time and late-lock status win over scheduling', () => {
  const late = {...game, immutable:true, lifecycle_status:'FINAL_PREGAME',
    lock_timestamp_utc:'2026-10-11T13:10:00Z'}
  const state = readLockLifecycle(late, Date.parse('2026-10-11T13:15:00Z'))
  assert.equal(state.label, 'LOCKED')
  assert.match(state.detail, /after T-120/)
  assert.doesNotMatch(state.detail, /Locks in/)
})

test('on-time immutable lock does not display a running countdown', () => {
  const onTime = {...game, immutable:true, lifecycle_status:'FINAL_PREGAME',
    lock_timestamp_utc:'2026-10-11T11:30:00Z'}
  const state = readLockLifecycle(onTime, Date.parse('2026-10-11T13:00:00Z'))
  assert.equal(state.label, 'LOCKED')
  assert.doesNotMatch(state.detail, /after T-120|Locks in/)
})

test('UTC subtraction handles DST boundaries without a hardcoded offset', () => {
  assert.equal(scheduledLockUtc({kickoff_utc:'2026-11-01T18:00:00Z'}),
    '2026-11-01T16:00:00.000Z')
  assert.equal(scheduledLockUtc({kickoff_utc:'2026-03-08T17:00:00Z'}),
    '2026-03-08T15:00:00.000Z')
})

test('postponements recalculate the future lock from the current kickoff', () => {
  const shifted = {...game, kickoff_utc:'2026-10-12T01:30:00Z'}
  assert.equal(scheduledLockUtc(shifted), '2026-10-11T23:30:00.000Z')
  assert.match(readLockLifecycle(shifted, Date.parse('2026-10-11T20:30:00Z')).detail, /Locks in 3h 0m/)
})

test('invalid schedule never invents a time', () => {
  const unknown = {...game, kickoff_utc:''}
  assert.equal(scheduledLockUtc(unknown), null)
  const state = readLockLifecycle(unknown, Date.now())
  assert.equal(state.label, 'LOCK TIME UNAVAILABLE')
})

test('kickoff without a receipt is explicitly called out', () => {
  const state = readLockLifecycle(game, Date.parse('2026-10-11T13:31:00Z'))
  assert.equal(state.label, 'KICKOFF PASSED')
  assert.match(state.detail, /No immutable official lock/)
})

test('server clock skew corrects client clock for deadline calculation', () => {
  const server = 'Sat, 10 Oct 2026 16:00:00 GMT'
  const before = Date.parse('2026-10-10T15:54:59Z')
  const after = Date.parse('2026-10-10T15:55:01Z')
  assert.equal(clockOffsetFromHttpDate(server, before, after), 300000)
  const clientNow = Date.parse('2026-10-11T11:25:00Z')
  assert.equal(readLockLifecycle(game, clientNow + 300000).label, 'LOCK DUE')
  assert.equal(clockOffsetFromHttpDate(null, before, after), null)
})
