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
