// Independent, read-only scheduling decisions. No LevLine model or lock writer here.
// This file runs both in Cloudflare Workers and Node's built-in test runner.

export function parseCsv(source) {
  if (typeof source !== "string" || source.length > 8_000_000) throw Error("invalid CSV input");
  const rows = [];
  let row = [], value = "", quoted = false;
  for (let i = 0; i < source.length; ++i) {
    const ch = source[i];
    if (ch === '"') {
      if (quoted && source[i + 1] === '"') { value += '"'; ++i; }
      else quoted = !quoted;
    } else if (!quoted && ch === ",") {
      row.push(value); value = "";
    } else if (!quoted && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && source[i + 1] === "\n") ++i;
      row.push(value); value = "";
      if (row.some(x => x)) rows.push(row);
      row = [];
    } else { value += ch; }
  }
  if (quoted) throw Error("unterminated CSV quote");
  if (row.length || value) { row.push(value); rows.push(row); }
  if (rows.length < 1) throw Error("empty CSV");
  const header = rows.shift();
  if (new Set(header).size !== header.length) throw Error("duplicate CSV headers");
  return rows.map((cells, index) => {
    if (cells.length !== header.length) throw Error("CSV column mismatch row " + (index + 2));
    return Object.fromEntries(header.map((key, i) => [key, cells[i]]));
  });
}

function partsInNewYork(date) {
  const formatter = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", year: "numeric", month: "2-digit",
    day: "2-digit", hour: "2-digit", minute: "2-digit",
    hourCycle: "h23", timeZoneName: "shortOffset"
  });
  return Object.fromEntries(formatter.formatToParts(date).map(p => [p.type, p.value]));
}

export function kickoffUtc(row) {
  const date = String(row.gameday || "");
  const time = String(row.gametime || "");
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) {
    throw Error("invalid game date/time for " + row.game_id);
  }
  const naive = Date.parse(date + "T" + time + ":00Z");
  if (!Number.isFinite(naive)) throw Error("invalid date");
  // Iteratively convert an Eastern wall clock into UTC. Iterate for DST
  // offset transition days, then verify the Eastern wall clock round-trips.
  let corrected = naive;
  for (let i = 0; i < 3; ++i) {
    const offset = partsInNewYork(new Date(corrected)).timeZoneName;
    const match = /^GMT([+-])(\d{1,2})(?::(\d{2}))?$/.exec(offset);
    if (!match) throw Error("unrecognized America/New_York timezone offset");
    const mins = (Number(match[2]) * 60 + Number(match[3] || 0))
      * (match[1] === "+" ? 1 : -1);
    corrected = naive - mins * 60_000;
  }
  const local = partsInNewYork(new Date(corrected));
  if ([local.year, local.month, local.day].join("-") !== date
      || local.hour + ":" + local.minute !== time) {
    throw Error("unresolvable Eastern kickoff clock");
  }
  return corrected;
}

export function lockLeadMinutes(row) {
  const gid = /^(\d{4})_(\d{2})_[A-Z]+_[A-Z]+$/.exec(String(row.game_id || ""));
  if (!gid) throw Error("malformed canonical game id");
  const season = Number(gid[1]), week = Number(gid[2]);
  if (Number(row.season) !== season || Number(row.week) !== week
      || season < 2000 || week < 1 || week > 22) {
    throw Error("canonical game identity mismatch");
  }
  return season > 2026 || (season === 2026 && week >= 6) ? 60 : 120;
}

export function planTick(current, history, nowMs) {
  if (!Number.isFinite(nowMs)) throw Error("invalid scheduler clock");
  if (!Array.isArray(current) || !current.length || !Array.isArray(history)) {
    throw Error("empty or invalid canonical scheduling inputs");
  }
  const canonical = new Set();
  const closed = new Set(history.filter(row =>
    ["LOCKED", "RECOVERED_MISSED_LOCK"].includes(row.lock_status)
  ).map(row => row.game_id));
  const plan = {preflight: [], lock: [], missing: []};
  for (const row of current) {
    if (canonical.has(row.game_id)) throw Error("duplicate canonical forecast game");
    canonical.add(row.game_id);
    const target = kickoffUtc(row) - lockLeadMinutes(row) * 60_000;
    const untilTarget = target - nowMs;
    const untilKickoff = kickoffUtc(row) - nowMs;
    if (closed.has(row.game_id) || untilKickoff <= 0) continue;
    // Preflight one roughly 100-90 minutes before kickoff for T-60,
    // using the existing guarded FINAL/pregame workflow.
    if (untilTarget > 30 * 60_000 && untilTarget <= 40 * 60_000) {
      plan.preflight.push({game_id: row.game_id, target});
    }
    // Dispatches are idempotent on the canonical GitHub lock writer.
    // Three 5-minute cron opportunities span T-60 through T-50.
    if (untilTarget <= 0 && untilTarget > -10 * 60_000) {
      plan.lock.push({game_id: row.game_id, target});
    }
    if (untilTarget <= -10 * 60_000 && untilTarget > -30 * 60_000) {
      plan.missing.push({game_id: row.game_id, target});
    }
  }
  return plan;
}

export function healthReport(lastSuccessIso, nowMs) {
  const ts = Date.parse(lastSuccessIso || "");
  return {
    scheduler_healthy: Number.isFinite(ts) && nowMs >= ts && nowMs - ts <= 12 * 60_000,
    last_success_utc: Number.isFinite(ts) ? new Date(ts).toISOString() : null,
    policy: "T-120 through 2026 Week 5; T-60 from Week 6",
    release_authority: false
  };
}
