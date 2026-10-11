import test from "node:test";
import assert from "node:assert/strict";
import {parseCsv, kickoffUtc, lockLeadMinutes, planTick, healthReport} from "./lib.mjs";
import {runTick} from "./worker.mjs";

const R = (id="2026_06_BAL_ATL",date="2026-10-18",time="13:00") => {
  const parts = id.split("_");
  return {game_id:id, season:parts[0], week:String(Number(parts[1])), gameday:date, gametime:time};
};
const csv = (rows) => {
  const cols = ["game_id","season","week","gameday","gametime","lock_status"];
  return cols.join(",") + "\n" + rows.map(r => cols.map(c => r[c] || "").join(",")).join("\n") + "\n";
};

test("strict RFC CSV preserves quoted commas and rejects malformed rows", () => {
  assert.deepEqual(parseCsv('a,b\r\n"x,y","z""q"\r\n'), [{a:"x,y",b:'z"q'}]);
  assert.throws(() => parseCsv("a,b\n1\n"), /column mismatch/);
  assert.throws(() => parseCsv('a,b\n"broken,1\n'), /unterminated/);
  assert.throws(() => parseCsv(""), /empty/);
});

test("kickoff UTC crosses Eastern daylight-saving boundaries safely", () => {
  assert.equal(new Date(kickoffUtc(R())).toISOString(), "2026-10-18T17:00:00.000Z");
  assert.equal(new Date(kickoffUtc(R("2026_15_BAL_ATL","2026-12-13","13:00"))).toISOString(), "2026-12-13T18:00:00.000Z");
  assert.equal(new Date(kickoffUtc(R("2026_06_BAL_ATL","2026-10-15","20:15"))).toISOString(), "2026-10-16T00:15:00.000Z");
  assert.throws(() => kickoffUtc({...R(), gametime:"25:00"}));
});

test("2026 Week 6 changes only prospective official lead to T-60", () => {
  assert.equal(lockLeadMinutes(R("2026_05_BAL_ATL")), 120);
  assert.equal(lockLeadMinutes(R()), 60);
  assert.equal(lockLeadMinutes(R("2027_01_BAL_ATL")), 60);
  assert.throws(() => lockLeadMinutes({...R(),week:"5"}), /mismatch/);
});

test("one shared kickoff dispatches once without revisiting locked games", () => {
  const both=[R(), R("2026_06_CIN_MIA")];
  const target=Date.parse("2026-10-18T16:00:00Z");
  const preflight=planTick(both,[],target-35*60_000);
  assert.equal(preflight.preflight.length,2);
  assert.equal(preflight.lock.length,0);
  assert.equal(planTick(both,[],target-60_000).lock.length,0);
  assert.equal(planTick(both,[],target).lock.length,2);
  const history=[{game_id:both[0].game_id,lock_status:"LOCKED"}];
  assert.deepEqual(planTick(both,history,target).lock.map(z=>z.game_id),[both[1].game_id]);
  assert.deepEqual(planTick(both,history,target+11*60_000).missing.map(z=>z.game_id),[both[1].game_id]);
  assert.equal(planTick(both,history,target+61*60_000).missing.length,0);
  assert.throws(()=>planTick([both[0],both[0]],[],target),/duplicate/);
});

function kit({forecast=[R(),R("2026_06_CIN_MIA")],history=[],failure=false}={}) {
  const kv=new Map();
  const requests=[];
  const env={
    GITHUB_DISPATCH_TOKEN:"test-token", ALERT_WEBHOOK_URL:"https://hooks.test/example",
    HEALTH_TOKEN:"test-health", LOCK_WATCH_STATE:{
      get:async k=>kv.get(k)||null,
      put:async(k,v)=>{kv.set(k,v)}
    }
  };
  const http=async(url,init)=>{
    requests.push({url,method:init.method||"GET",body:init.body});
    if(url.startsWith("https://hooks.test"))return {ok:true,status:200};
    if(failure)return {ok:false,status:503};
    if(url.includes("/contents/")){
      const rows=url.includes("this_week")?forecast:history;
      return {ok:true,status:200,json:async()=>({encoding:"base64",content:Buffer.from(csv(rows),"utf8").toString("base64")})};
    }
    return {ok:true,status:204};
  };
  return {env,http,requests,kv};
}

test("Cloudflare scheduler dispatches ONE existing guarded lock workflow per shared game window",async()=>{
  const k=kit(),target=Date.parse("2026-10-18T16:00:00Z");
  const result=await runTick(k.env,target,k.http);
  assert.equal(result.lock,2);
  assert.equal(k.requests.filter(x=>x.url.endsWith("fast_official_lock.yml/dispatches")).length,1);
  assert.equal(k.requests.filter(x=>x.method==="POST" && x.url.includes("github")).length,1);
  assert.equal(k.requests.filter(x=>x.url.startsWith("https://hooks")).length,0);
  assert.ok(k.kv.get("last_success_utc"));
});

test("preflight dispatches once per distinct slate and receipt KV prevents repeated full rebuilds",async()=>{
  const k=kit(),time=Date.parse("2026-10-18T15:24:00Z");
  await runTick(k.env,time,k.http);
  await runTick(k.env,time+60_000,k.http);
  assert.equal(k.requests.filter(x=>x.url.endsWith("pregame.yml/dispatches")).length,1);
});

test("missing immutable locks create independent off-GitHub alerts only once",async()=>{
  const k=kit(),target=Date.parse("2026-10-18T16:00:00Z");
  await runTick(k.env,target+11*60_000,k.http);
  await runTick(k.env,target+16*60_000,k.http);
  assert.equal(k.requests.filter(x=>x.url.startsWith("https://hooks")).length,1);
  assert.equal(k.requests.filter(x=>x.url.endsWith("fast_official_lock.yml/dispatches")).length,0);
});

test("GitHub outage notifies independently and leaves watchdog unhealthy",async()=>{
  const k=kit({failure:true});
  await assert.rejects(runTick(k.env,Date.parse("2026-10-18T16:00:00Z"),k.http),/GitHub API/);
  assert.equal(k.requests.filter(x=>x.url.startsWith("https://hooks")).length,1);
  assert.equal(k.kv.has("last_success_utc"),false);
});

test("health is independent of green GitHub research jobs and never grants publication",()=>{
  const now=Date.parse("2026-10-18T16:00:00Z");
  assert.equal(healthReport(null,now).scheduler_healthy,false);
  assert.equal(healthReport(new Date(now-13*60_000).toISOString(),now).scheduler_healthy,false);
  assert.equal(healthReport(new Date(now-6*60_000).toISOString(),now).scheduler_healthy,true);
  assert.equal(healthReport(new Date(now).toISOString(),now).release_authority,false);
});


test("delayed cron execution evaluates against the actual runtime clock",async()=>{
  // The live handler must not pass a potentially delayed scheduledTime to
  // runTick. Pure runTick/planTick behavior is independently tested above.
  const {readFile} = await import("node:fs/promises");
  const source = await readFile(new URL("./worker.mjs",import.meta.url),"utf8");
  assert.match(source,/scheduled\\(event, env, ctx\\)[\\s\\S]*?runTick\\(env, Date\\.now\\(\\)\\)/);
  assert.doesNotMatch(source,/runTick\\(env,\\s*Number\\(event\\.scheduledTime/);
});
