const BASE = import.meta.env.BASE_URL

export function parseCSV(text) {
  const rows=[]
  let row=[], cell='', quoted=false
  for (let i=0;i<text.length;i+=1) {
    const c=text[i]
    if (quoted) {
      if (c==='"' && text[i+1]==='"') { cell+='"'; i+=1 }
      else if (c==='"') quoted=false
      else cell+=c
    } else if (c==='"') quoted=true
    else if (c===',') { row.push(cell); cell='' }
    else if (c==='\n') { row.push(cell); rows.push(row); row=[]; cell='' }
    else if (c!=='\r') cell+=c
  }
  if (cell.length || row.length) { row.push(cell); rows.push(row) }
  const headers=rows.shift() || []
  return rows.filter(r=>r.some(Boolean)).map(r=>Object.fromEntries(headers.map((key,i)=>[key,r[i]??''])))
}

async function request(name, type='json') {
  const response=await fetch(`${BASE}data/${name}`,{cache:'no-store'})
  if (!response.ok) throw new Error(`${name} unavailable (${response.status})`)
  return type==='csv' ? parseCSV(await response.text()) : response.json()
}

export async function loadBoard() {
  const [forecastPayload,status,previews]=await Promise.all([
    request('public_forecasts.json'),
    request('status.json'),
    request('game_previews.json'),
  ])
  if (!Array.isArray(forecastPayload?.games) || !forecastPayload.games.length) {
    throw new Error('Canonical public forecast contract is unavailable.')
  }
  return {games:forecastPayload.games,status,previews}
}

export async function loadGameDossier(gameId) {
  const [runs,evidence,impact,current]=await Promise.all([
    request('run_history.csv','csv'),
    request('contextual_evidence.json'),
    request('impact_monitor.json'),
    request('this_week.csv','csv'),
  ])
  return {
    runs:runs.filter(row=>row.game_id===gameId),
    evidence:Array.isArray(evidence?.[gameId]) ? evidence[gameId] : [],
    impact:(impact?.games||[]).find(row=>row.game_id===gameId) || null,
    diagnostic:current.find(row=>row.game_id===gameId) || null,
  }
}

export async function loadHistory() {
  const [history,autopsies,models]=await Promise.all([
    request('prediction_history.csv','csv'),
    request('postgame_autopsies.json'),
    request('model_leaderboard.csv','csv'),
  ])
  return {history,autopsies,models}
}

export async function loadTeam(team) {
  const [profiles,editorial]=await Promise.all([
    request('team_profiles.csv','csv'),
    request('power_editorial.json'),
  ])
  return {
    profile:profiles.find(row=>row.team===team) || null,
    editorial:(editorial?.teams||[]).find(row=>row.team===team) || null,
  }
}
