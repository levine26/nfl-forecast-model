export const PROP_LABELS = {
  passing_yards: 'Passing Yards', rushing_yards: 'Rushing Yards', receiving_yards: 'Receiving Yards', receptions: 'Receptions', passing_tds: 'Passing TDs', rushing_td: 'Rushing TD', receiving_td: 'Receiving TD', anytime_td: 'Anytime TD',
}
export function numberValue(value) { if (value === '' || value == null) return null; const parsed=Number(value); return Number.isFinite(parsed)?parsed:null }
export function formatPercent(value,digits=1){const n=numberValue(value);return n==null?'—':`${(n*100).toFixed(digits)}%`}
export function formatPoints(value,digits=1){const n=numberValue(value);return n==null?'—':`${n>=0?'+':''}${(n*100).toFixed(digits)} pp`}
export function formatAmerican(value){const n=numberValue(value);if(n==null)return '—';const r=Math.round(n);return r>0?`+${r}`:`${r}`}
export function formatLine(value,digits=1){const n=numberValue(value);return n==null?'—':Number.isInteger(n)?`${n}`:n.toFixed(digits)}
export function formatDifference(value,unit=''){const n=numberValue(value);if(n==null)return '—';return `${n>=0?'+':''}${n.toFixed(1)}${unit?` ${unit}`:''}`}
export function propLabel(propType){return PROP_LABELS[propType]||propType||'Player Prop'}
export function signalRank(state){return ({'MODEL EDGE':0,WATCH:1,'NO SIGNAL':2})[state]??3}
export function sortForecasts(rows=[]){return [...rows].sort((a,b)=>{const s=signalRank(a?.signal_state)-signalRank(b?.signal_state);if(s)return s;const ea=Math.abs(numberValue(a?.model?.probability_edge)??-1),eb=Math.abs(numberValue(b?.model?.probability_edge)??-1);if(ea!==eb)return eb-ea;return String(a?.player||'').localeCompare(String(b?.player||''))})}
export function primaryMarketPrice(forecast){const m=forecast?.market||{};return forecast?.market_kind==='BINARY_TD'?m.td_price_american:m.over_price_american}
export function rangeText(forecast){const i=forecast?.model?.prediction_interval||{},lo=numberValue(i.low),hi=numberValue(i.high);if(lo==null||hi==null)return '—';const c=numberValue(i.coverage);return `${c==null?'Model range':`${Math.round(c*100)}% model range`}: ${formatLine(lo)}–${formatLine(hi)}`}
export function qualityLabel(forecast){const q=forecast?.data_quality||{};return `${q.state||'UNKNOWN'} data · ${q.confidence||'UNAVAILABLE'} confidence`}


export const MARKET_FILTERS = {
  ALL: null,
  PASSING: ['passing_yards'],
  RUSHING: ['rushing_yards'],
  RECEIVING: ['receiving_yards'],
  RECEPTIONS: ['receptions'],
  TDS: ['passing_tds','rushing_td','receiving_td','anytime_td'],
}
export function marketFamily(propType){
  if (['passing_tds','rushing_td','receiving_td','anytime_td'].includes(propType)) return 'TDS'
  if (propType==='passing_yards') return 'PASSING'
  if (propType==='rushing_yards') return 'RUSHING'
  if (propType==='receiving_yards') return 'RECEIVING'
  if (propType==='receptions') return 'RECEPTIONS'
  return 'OTHER'
}
export function directionFor(forecast){
  if (forecast?.market_kind==='BINARY_TD') return String(PROP_LABELS[forecast?.prop_type] || 'TD').toUpperCase()
  const diff=numberValue(forecast?.model?.line_difference)
  if (diff==null) return 'UNAVAILABLE'
  if (Math.abs(diff)<1e-9) return 'MARKET ALIGNED'
  return diff>0?'OVER':'UNDER'
}
export function unitFor(forecast){
  if (forecast?.prop_type==='receptions') return 'REC'
  if (forecast?.prop_type==='passing_tds') return 'TD'
  return 'YDS'
}
export function kickoffValue(forecast){
  const value=Date.parse(forecast?.kickoff_utc||'')
  return Number.isFinite(value)?value:Number.MAX_SAFE_INTEGER
}
export function qualityRank(forecast){
  return ({HIGH:0,MEDIUM:1,LOW:2,INSUFFICIENT:3})[String(forecast?.data_quality?.state||'').toUpperCase()]??4
}
export function sortTopSignals(rows=[]){
  return rows.filter(row=>row?.signal_state==='MODEL EDGE').sort((a,b)=>{
    const edge=Math.abs(numberValue(b?.model?.probability_edge)??-1)-Math.abs(numberValue(a?.model?.probability_edge)??-1)
    if(edge) return edge
    const quality=qualityRank(a)-qualityRank(b)
    if(quality) return quality
    const kickoff=kickoffValue(a)-kickoffValue(b)
    if(kickoff) return kickoff
    return String(a?.forecast_id||a?.player||'').localeCompare(String(b?.forecast_id||b?.player||''))
  })
}
export function sortForBrowse(rows=[],mode='signal'){
  const copy=[...rows]
  if(mode==='kickoff') return copy.sort((a,b)=>kickoffValue(a)-kickoffValue(b)||String(a?.player||'').localeCompare(String(b?.player||'')))
  if(mode==='player') return copy.sort((a,b)=>String(a?.player||'').localeCompare(String(b?.player||''))||String(a?.prop_type||'').localeCompare(String(b?.prop_type||'')))
  if(mode==='fair-line-gap') return copy.sort((a,b)=>Math.abs(numberValue(b?.model?.line_difference)??-1)-Math.abs(numberValue(a?.model?.line_difference)??-1)||signalRank(a?.signal_state)-signalRank(b?.signal_state))
  return sortForecasts(copy)
}
export function formatTimestamp(value){
  if(!value) return '—'
  const date=new Date(value)
  if(Number.isNaN(date.getTime())) return '—'
  return new Intl.DateTimeFormat('en-US',{month:'short',day:'numeric',hour:'numeric',minute:'2-digit',timeZone:'America/Los_Angeles',timeZoneName:'short'}).format(date)
}
export function formatKickoff(value){
  if(!value) return 'TBD'
  const date=new Date(value)
  if(Number.isNaN(date.getTime())) return 'TBD'
  return new Intl.DateTimeFormat('en-US',{weekday:'short',hour:'numeric',minute:'2-digit',timeZone:'America/Los_Angeles'}).format(date)
}
