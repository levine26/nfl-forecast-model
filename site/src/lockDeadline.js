/** Official deadline policy for public display only.
 * The canonical schedule supplies UTC kickoff and model/lock code owns the
 * immutable receipt. Never manufacture a lock timestamp from the deadline.
 */
export const LOCK_LEAD_MINUTES = 120

export function scheduledLockMillis(game) {
  const kickoff = Date.parse(game?.kickoff_utc || '')
  if (!Number.isFinite(kickoff)) return null
  return kickoff - LOCK_LEAD_MINUTES * 60 * 1000
}

export function lockCountdownState(game, nowMillis = Date.now()) {
  const actualLock = Date.parse(game?.lock_timestamp_utc || '')
  const immutable = game?.immutable === true ||
    game?.lifecycle_status === 'FINAL_PREGAME' ||
    game?.lifecycle_status === 'GRADED'
  if (immutable) {
    return { phase: 'locked', actualLockMillis: Number.isFinite(actualLock) ? actualLock : null }
  }
  const deadline = scheduledLockMillis(game)
  const kickoff = Date.parse(game?.kickoff_utc || '')
  if (deadline == null) return { phase: 'unknown', deadlineMillis: null }
  if (nowMillis >= kickoff) return { phase: 'missed', deadlineMillis: deadline }
  if (nowMillis >= deadline) return { phase: 'overdue', deadlineMillis: deadline }
  return { phase: 'upcoming', deadlineMillis: deadline }
}
