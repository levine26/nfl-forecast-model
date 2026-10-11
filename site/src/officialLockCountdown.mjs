/**
 * Presentation-only timing for the versioned T-120 / T-60 official lock target.
 * The immutable receipt, not the browser clock, decides whether a forecast locked.
 * Canonical kickoff_utc is offset-aware; arithmetic on epoch milliseconds is DST-safe.
 * This module never creates, changes, or backdates a prediction lock.
 */
export const OFFICIAL_LOCK_LEAD_MINUTES = 120 // legacy Weeks 1–5
export const PROSPECTIVE_LOCK_LEAD_MINUTES = 60 // Week 6 2026 onward

export function officialLockLeadMinutes(game) {
  let season = Number(game?.season)
  let week = Number(game?.week)
  if (!Number.isInteger(season) || !Number.isInteger(week) || season <= 0 || week <= 0) {
    const id = String(game?.game_id || '').match(/^(\d{4})_(\d{2})_/)
    season = id ? Number(id[1]) : 0
    week = id ? Number(id[2]) : 0
  }
  return season > 2026 || (season === 2026 && week >= 6)
    ? PROSPECTIVE_LOCK_LEAD_MINUTES : OFFICIAL_LOCK_LEAD_MINUTES
}

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
  const scheduledMs = kickoffMs - officialLockLeadMinutes(game) * 60_000
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
