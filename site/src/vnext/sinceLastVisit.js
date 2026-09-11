const PREFIX = 'sunday-signal:last-visit:v1:'

const numberOrNull = value => {
  const n=Number(value)
  return Number.isFinite(n) ? n : null
}

export function visitSnapshot(game, evidence = []) {
  const weather=evidence.find(item=>String(item.category||'').toLowerCase()==='weather')
  const personnel=evidence.filter(item=>['injury','personnel'].includes(String(item.category||'').toLowerCase()))
  return {
    seen_at_utc:new Date().toISOString(),
    forecast_timestamp_utc:game.forecast_timestamp_utc || game.lock_timestamp_utc || null,
    official_winner:game.official_winner || null,
    official_probability:numberOrNull(game.official_winner_probability),
    market_probability:numberOrNull(game.market_home_win_probability),
    personnel_signal_count:personnel.length,
    latest_weather_timestamp:weather?.as_of || null,
  }
}

export function readLastVisit(gameId) {
  try {
    const raw=window.localStorage.getItem(`${PREFIX}${gameId}`)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function writeLastVisit(gameId, snapshot) {
  try { window.localStorage.setItem(`${PREFIX}${gameId}`,JSON.stringify(snapshot)) } catch { /* storage is optional */ }
}

export function visitChanges(previous, current) {
  if (!previous) return []
  const changes=[]
  if (previous.official_winner && current.official_winner && previous.official_winner!==current.official_winner) {
    changes.push({kind:'forecast',label:`Official winner changed ${previous.official_winner} → ${current.official_winner}`})
  }
  if (previous.official_probability!=null && current.official_probability!=null) {
    const delta=(current.official_probability-previous.official_probability)*100
    if (Math.abs(delta)>=0.05) changes.push({kind:'forecast',label:`LevLine ${delta>=0?'+':''}${delta.toFixed(1)} pp`})
  }
  if (previous.market_probability!=null && current.market_probability!=null) {
    const delta=(current.market_probability-previous.market_probability)*100
    if (Math.abs(delta)>=0.05) changes.push({kind:'market',label:`Market home probability ${delta>=0?'+':''}${delta.toFixed(1)} pp`})
  }
  if ((current.personnel_signal_count||0)>(previous.personnel_signal_count||0)) {
    changes.push({kind:'personnel',label:'New personnel context'})
  }
  if (current.latest_weather_timestamp && previous.latest_weather_timestamp!==current.latest_weather_timestamp) {
    changes.push({kind:'weather',label:'Weather context updated'})
  }
  return changes
}
