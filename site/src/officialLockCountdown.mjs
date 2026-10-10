/**
 * Presentation-only timing for the official T-120 lock boundary.
 * The immutable receipt, not the browser clock, decides whether a forecast locked.
 * Canonical kickoff_utc is offset-aware; arithmetic on epoch milliseconds is DST-safe.
 * This module never creates, changes, or backdates a prediction lock.
 */
export const OFFICIAL_LOCK_LEAD_MINUTES = 120

export function officialLockTiming(game, nowMs = Date.now()) {
  const status = String(game?.lifecycle_status || '')
  const hasImmutableReceipt = game?.immutable === true ||
    status === 'FINAL_PREGAME' || status === 'GRADED' ||
    (status === 'IN_PROGRESS' && Boolean(game?.lock_timestamp_utc))
  if (hasImmutableReceipt) {
    return {state: 'locked', actualLockUtc: game?.lock_timestamp_utc || null, scheduledLockUtc: null}
  }
  const kickoffMs = Date.parse(game?.kickoff_utc || '')
  if (!Number.isFinite(kickoffMs)) {
    return {state: 'unavailable', actualLockUtc: null, scheduledLockUtc: null}
  }
  const scheduledMs = kickoffMs - OFFICIAL_LOCK_LEAD_MINUTES * 60_000
  return {
    state: Number.isFinite(nowMs) && nowMs < scheduledMs ? 'countdown' : 'due',
    actualLockUtc: null,
    scheduledLockUtc: new Date(scheduledMs).toISOString(),
  }
}


/**
 * Correct countdowns for an inaccurate device clock using the same-origin
 * HTTP Date header. Network RTT is centered on the local send/receive times.
 * A missing, invalid, or reversed response has no usable clock correction.
 */
export function serverClockOffsetMs(httpDate, requestStartedMs, responseReceivedMs) {
  const remoteMs = Date.parse(httpDate || '')
  if (!Number.isFinite(remoteMs) || !Number.isFinite(requestStartedMs) ||
      !Number.isFinite(responseReceivedMs) || responseReceivedMs < requestStartedMs) {
    return null
  }
  return Math.round(remoteMs - (requestStartedMs + responseReceivedMs) / 2)
}
