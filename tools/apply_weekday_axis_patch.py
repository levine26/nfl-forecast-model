from pathlib import Path

path = Path('site/src/AppPublicationVNext.jsx')
text = path.read_text(encoding='utf-8')

old = '''function ForecastMovement({ game, runs }) {
  const trend=runs.filter(row=>row.game_id===game.game_id).sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc)).map((row,index)=>({
    run:index+1,
    label:`${index+1}`,
    lev:pickProbability(game,row.final_home_prob),
    market:pickProbability(game,row.market_home_prob),
  })).filter(row=>row.lev!=null)
  return <section className="pub-trend vnext-trend"><div><span>FORECAST MOVEMENT</span><h3>How LevLine and the market moved through the week</h3></div><div>{trend.length>1?<ResponsiveContainer width="100%" height={230}><LineChart data={trend} margin={{top:10,right:10,left:-10,bottom:0}}><CartesianGrid stroke="#183041" strokeDasharray="3 5" vertical={false}/><XAxis dataKey="label" tickLine={false} axisLine={false}/><YAxis domain={[0.35,.85]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip formatter={(v,name)=>[pct(v),name==='lev'?'LevLine':'Market']}/><Area dataKey="lev" fill="#68d8c718" stroke="none"/><Line dataKey="lev" type="monotone" stroke="#68d8c7" strokeWidth={3} dot={false}/><Line dataKey="market" type="monotone" stroke="#9caebb" strokeWidth={2} strokeDasharray="5 4" dot={false}/></LineChart></ResponsiveContainer>:<p className="pub-empty">Movement appears after the second comparable model run.</p>}</div></section>
}
'''

new = '''function ForecastMovement({ game, runs }) {
  const DAY_MS = 86400000
  const DAY_LABELS = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday']
  const pacificParts = value => {
    const date = value instanceof Date ? value : new Date(value)
    if (Number.isNaN(date.getTime())) return null
    const parts = new Intl.DateTimeFormat('en-US', {
      timeZone:'America/Los_Angeles', year:'numeric', month:'2-digit', day:'2-digit',
      hour:'2-digit', minute:'2-digit', second:'2-digit', hourCycle:'h23',
    }).formatToParts(date)
    const shown = Object.fromEntries(parts.map(part => [part.type, part.value]))
    return { year:+shown.year, month:+shown.month, day:+shown.day, hour:+shown.hour, minute:+shown.minute, second:+shown.second }
  }
  const raw = runs
    .filter(row=>row.game_id===game.game_id && row.prediction_timestamp_utc)
    .sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc))
  const kickoff = easternKickoff(game)
  const reference = kickoff || (raw.length ? new Date(raw[raw.length-1].prediction_timestamp_utc) : new Date())
  const ref = pacificParts(reference)
  const refSerial = ref ? Date.UTC(ref.year,ref.month-1,ref.day) : Date.now()
  const refDow = new Date(refSerial).getUTCDay()
  let mondaySerial = refSerial - (((refDow + 6) % 7) * DAY_MS)
  if (refDow === 1 && raw.length) {
    const first = pacificParts(raw[0].prediction_timestamp_utc)
    const firstSerial = first ? Date.UTC(first.year,first.month-1,first.day) : mondaySerial
    if (firstSerial < mondaySerial) mondaySerial -= 7 * DAY_MS
  }
  const weekX = value => {
    const p = pacificParts(value)
    if (!p) return null
    const serial = Date.UTC(p.year,p.month-1,p.day)
    return (serial-mondaySerial)/DAY_MS + p.hour/24 + p.minute/1440 + p.second/86400
  }
  const prepared = raw.map(row=>({
    x:weekX(row.prediction_timestamp_utc),
    timestamp:row.prediction_timestamp_utc,
    lev:pickProbability(game,row.final_home_prob),
    market:pickProbability(game,row.market_home_prob),
  })).filter(row=>row.x!=null && row.lev!=null)
  const kickoffX = kickoff ? weekX(kickoff) : null
  const latestObserved = prepared.length ? Math.max(...prepared.map(row=>row.x)) : 0
  const axisEnd = kickoffX != null && kickoffX >= 6 ? Math.max(6.15,kickoffX) : Math.max(6.85,latestObserved)
  const prior = [...prepared].filter(row=>row.x<0).pop()
  const trend = prepared.filter(row=>row.x>=0 && row.x<=axisEnd)
  if (prior && (!trend.length || trend[0].x>0)) trend.unshift({...prior,x:0,timestamp:null})
  const ticks = [0,1,2,3,4,5,6].filter(value=>value<=axisEnd+0.001)
  const labelForTick = value => DAY_LABELS[Math.round(value)] || ''
  const tooltipTime = payload => {
    const timestamp = payload?.[0]?.payload?.timestamp
    if (!timestamp) return 'Monday · start of chart'
    const date = new Date(timestamp)
    return new Intl.DateTimeFormat('en-US', {
      weekday:'long', hour:'numeric', minute:'2-digit', timeZone:'America/Los_Angeles', timeZoneName:'short',
    }).format(date)
  }
  return <section className="pub-trend vnext-trend"><div><span>FORECAST MOVEMENT</span><h3>How LevLine and the market moved through the week</h3></div><div>{trend.length>1?<ResponsiveContainer width="100%" height={230}><LineChart data={trend} margin={{top:10,right:10,left:-10,bottom:0}}><CartesianGrid stroke="#183041" strokeDasharray="3 5" vertical={false}/><XAxis type="number" dataKey="x" domain={[0,axisEnd]} ticks={ticks} tickFormatter={labelForTick} tickLine={false} axisLine={false}/><YAxis domain={[0.35,.85]} tickFormatter={v=>`${Math.round(v*100)}%`} tickLine={false} axisLine={false}/><Tooltip labelFormatter={(value,payload)=>tooltipTime(payload)} formatter={(v,name)=>[pct(v),name==='lev'?'LevLine':'Market']}/><Area dataKey="lev" type="stepAfter" fill="#68d8c718" stroke="none"/><Line dataKey="lev" type="stepAfter" stroke="#68d8c7" strokeWidth={3} dot={false}/><Line dataKey="market" type="stepAfter" stroke="#9caebb" strokeWidth={2} strokeDasharray="5 4" dot={false}/></LineChart></ResponsiveContainer>:<p className="pub-empty">Movement appears after the second comparable model run.</p>}</div></section>
}
'''

count = text.count(old)
if count != 1:
    raise SystemExit(f'Expected exactly one ForecastMovement block, found {count}')
path.write_text(text.replace(old, new), encoding='utf-8')
print('Patched forecast movement to a real Pacific-time Monday–Sunday axis.')
