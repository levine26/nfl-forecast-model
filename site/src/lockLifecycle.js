/** Canonical T-120 public-lock presentation. Never computes or writes locks. */
export const LOCK_LEAD_MS = 120 * 60 * 1000

export function scheduledLockUtc(game) {
  const kickoff = Date.parse(game?.kickoff_utc || '')
  return Number.isFinite(kickoff) ? new Date(kickoff - LOCK_LEAD_MS).toISOString() : null
}

function displayedTime(iso) {
  const parsed = Date.parse(iso || '')
  if (!Number.isFinite(parsed)) return 'unavailable'
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'short', month: 'short', day: 'numeric',
    hour: 'numeric', minute: '2-digit',
    timeZone: 'America/Los_Angeles', timeZoneName: 'short',
  }).format(parsed)
}

function remaining(until, now) {
  const minutes = Math.ceil((until - now) / 60000)
  if (minutes <= 0) return null
  const days = Math.floor(minutes / 1440)
  const hours = Math.floor((minutes % 1440) / 60)
  const mins = minutes % 60
  if (days > 0) return days + 'd ' + hours + 'h'
  if (hours > 0) return hours + 'h ' + mins + 'm'
  return mins + 'm'
}

/** Correct device-clock skew using a same-origin HTTP Date response. */
export function clockOffsetFromHttpDate(header, beforeMs, afterMs) {
  const serverMs = Date.parse(header || '')
  if (!Number.isFinite(serverMs) || !Number.isFinite(beforeMs) ||
      !Number.isFinite(afterMs) || afterMs < beforeMs) return null
  return Math.round(serverMs - (beforeMs + afterMs) / 2)
}

/** Report actual lock receipts before displaying any projected T-120 deadline. */
export function readLockLifecycle(game, nowMs = Date.now()) {
  const status = String(game?.lifecycle_status || '')
  const actual = Date.parse(game?.lock_timestamp_utc || '')
  const hasActual = Number.isFinite(actual)
  const lockUtc = scheduledLockUtc(game)
  const scheduledMs = lockUtc ? Date.parse(lockUtc) : null
  const kickoff = Date.parse(game?.kickoff_utc || '')
  const locked = game?.immutable === true || status === 'FINAL_PREGAME' || hasActual

  if (status === 'GRADED')
    return {key: 'final', label: 'FINAL', detail: hasActual
      ? 'Pregame forecast locked ' + displayedTime(game.lock_timestamp_utc)
      : 'Historical lock receipt unavailable'}
  if (status === 'IN_PROGRESS')
    return {key: 'live', label: 'GAME IN PROGRESS', detail: hasActual
      ? 'Pregame forecast locked ' + displayedTime(game.lock_timestamp_utc)
      : 'Official pregame lock not verified'}
  if (locked) {
    const late = hasActual && Number.isFinite(scheduledMs) && actual > scheduledMs
    return {key: 'locked', label: 'LOCKED', detail: hasActual
      ? 'Locked ' + displayedTime(game.lock_timestamp_utc) + (late ? ' · after T-120' : '')
      : 'Immutable lock reported; timestamp unavailable'}
  }
  if (!Number.isFinite(kickoff) || !Number.isFinite(scheduledMs))
    return {key: 'pending', label: 'LOCK TIME UNAVAILABLE',
      detail: 'Verified kickoff timestamp required'}
  if (nowMs >= kickoff)
    return {key: 'overdue', label: 'KICKOFF PASSED',
      detail: 'No immutable official lock receipt verified'}
  if (nowMs >= scheduledMs)
    return {key: 'overdue', label: 'LOCK DUE',
      detail: 'T-120 deadline passed (' + displayedTime(lockUtc) + '); awaiting immutable receipt'}
  const left = remaining(scheduledMs, nowMs)
  return {key: 'forecast', label: 'LIVE FORECAST',
    detail: left ? 'Locks in ' + left : 'Official lock scheduled ' + displayedTime(lockUtc)}
}
