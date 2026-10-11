import {parseCsv, planTick, healthReport} from "./lib.mjs";

const OWNER = "levine26";
const REPO = "nfl-forecast-model";
const API = "https://api.github.com/repos/" + OWNER + "/" + REPO;
const PRIMARY = "fast_official_lock.yml";
const PREFLIGHT = "pregame.yml";

function config(env) {
  if (!env.GITHUB_DISPATCH_TOKEN || !env.ALERT_WEBHOOK_URL || !env.LOCK_WATCH_STATE) {
    throw Error("Missing required external GitHub dispatch token, independent alert webhook or KV binding");
  }
}

async function githubRequest(path, env, init = {}, http = fetch) {
  const headers = {
    "Authorization": "Bearer " + env.GITHUB_DISPATCH_TOKEN,
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "sunday-signal-independent-lock-watch",
    "Cache-Control": "no-store",
    ...(init.headers || {}),
  };
  const response = await http(API + path, {...init, headers, cache: "no-store"});
  if (!response.ok) {
    // Do not include response bodies, request headers or secrets in alerts.
    throw Error("GitHub API " + path.split("?")[0] + " HTTP " + response.status);
  }
  return response;
}

async function readCanonicalCsv(path, env, http) {
  const response = await githubRequest("/contents/" + path + "?ref=main", env, {}, http);
  const data = await response.json();
  if (!data || data.encoding !== "base64" || typeof data.content !== "string") {
    throw Error("GitHub did not return canonical encoded CSV: " + path);
  }
  const binary = atob(data.content.replace(/\s/g, ""));
  const bytes = Uint8Array.from(binary, char => char.charCodeAt(0));
  return parseCsv(new TextDecoder().decode(bytes));
}

async function dispatchWorkflow(name, env, http) {
  await githubRequest("/actions/workflows/" + name + "/dispatches", env, {
    method: "POST",
    body: JSON.stringify({ref: "main"}),
    headers: {"Content-Type": "application/json"},
  }, http);
}

async function postAlert(message, env, http) {
  if (!env.ALERT_WEBHOOK_URL) throw Error("Independent alert webhook is not configured");
  // Supports Slack's text and Discord's content fields. Never send credentials.
  const response = await http(env.ALERT_WEBHOOK_URL, {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({text: message, content: message}),
  });
  if (!response.ok) throw Error("Off-GitHub notification failed with HTTP " + response.status);
}

export async function runTick(env, nowMs, http = fetch) {
  config(env);
  try {
    const [forecast, history] = await Promise.all([
      readCanonicalCsv("outputs/this_week.csv", env, http),
      readCanonicalCsv("outputs/prediction_history.csv", env, http),
    ]);
    const plan = planTick(forecast, history, nowMs);
    const pendingPreflight = [];
    for (const item of plan.preflight) {
      const key = "preflight:" + item.game_id + ":" + item.target;
      if (!(await env.LOCK_WATCH_STATE.get(key))) pendingPreflight.push({...item, key});
    }
    // One dispatch per slate, not N duplicate jobs when many games share kickoff.
    if (pendingPreflight.length) {
      await dispatchWorkflow(PREFLIGHT, env, http);
      await Promise.all(pendingPreflight.map(item =>
        env.LOCK_WATCH_STATE.put(item.key, new Date(nowMs).toISOString(), {expirationTtl: 86400})
      ));
    }
    if (plan.lock.length) {
      // At least two independent chances within the real, audited lock window.
      // GitHub worker is the only party authorized to mutate immutable receipts.
      await dispatchWorkflow(PRIMARY, env, http);
    }
    const newMissing = [];
    for (const item of plan.missing) {
      const key = "missing:" + item.game_id + ":" + item.target;
      if (!(await env.LOCK_WATCH_STATE.get(key))) newMissing.push({...item, key});
    }
    if (newMissing.length) {
      const names = newMissing.map(item => item.game_id).sort().join(", ");
      await postAlert("P0 Sunday Signal: no immutable official lock by policy T-minus-50 for " + names, env, http);
      await Promise.all(newMissing.map(item =>
        env.LOCK_WATCH_STATE.put(item.key, new Date(nowMs).toISOString(), {expirationTtl: 86400})
      ));
    }
    await env.LOCK_WATCH_STATE.put("last_success_utc", new Date(nowMs).toISOString());
    return {preflight: pendingPreflight.length, lock: plan.lock.length, overdue: newMissing.length};
  } catch (error) {
    try {
      await postAlert("P0 Sunday Signal independent scheduler failed: " + String(error.message || error), env, http);
    } catch (_) { /* Worker error still reaches Cloudflare logs and health monitor. */ }
    throw error;
  }
}

export default {
  scheduled(event, env, ctx) {
    ctx.waitUntil(runTick(env, Number(event.scheduledTime || Date.now())));
  },
  async fetch(request, env) {
    if (!env.HEALTH_TOKEN || request.headers.get("Authorization") !== "Bearer " + env.HEALTH_TOKEN) {
      return new Response("unauthorized", {status: 401});
    }
    if (!env.LOCK_WATCH_STATE) return new Response("KV not configured", {status: 503});
    const state = healthReport(await env.LOCK_WATCH_STATE.get("last_success_utc"), Date.now());
    return Response.json(state, {status: state.scheduler_healthy ? 200 : 503, headers: {"Cache-Control": "no-store"}});
  }
};
