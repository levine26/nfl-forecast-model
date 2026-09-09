from pathlib import Path
import re

app_path = Path('site/src/AppPublicationVNext.jsx')
css_path = Path('site/src/publication-vnext.css')
text = app_path.read_text(encoding='utf-8')


def replace(pattern: str, replacement: str, label: str) -> None:
    global text
    text, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise SystemExit(f'{label}: expected one replacement, found {count}')


week_page = r'''function WeekPage({ games, evidence, previews, history, status, setSelected, onPreviousWeek }) {
  const [sortMode,setSortMode] = useState('kickoff')
  const locked = new Set(history.filter(row => row.lock_status==='LOCKED').map(row => row.game_id))
  const editorialScore = game => {
    const preview = previews[game.game_id] || {}
    const items = evidence[game.game_id] || []
    const marketGap = Math.abs((game.pickP ?? .5) - (game.marketPickP ?? game.pickP ?? .5)) * 100
    const closeness = (1 - Math.min(1, Math.abs((game.pickP ?? .5) - .5) * 2)) * 4
    const spreadEdge = Math.min(12, Math.abs(game.pickEdge || 0)) * .35
    const sourceDepth = Math.min(5, items.length * .3 + (preview.key_factors?.length || 0) * .35)
    const storyText = [preview.headline, ...(preview.paragraphs || []), ...items.flatMap(item => [item.title,item.summary])].join(' ').toLowerCase()
    const eventBonus = /rivalry|australia|melbourne|international|first-ever|record|milestone|reunion|revenge|return|debut/.test(storyText) ? 7 : 0
    const peopleBonus = /quarterback|coach|coordinator|stafford|purdy|injury|questionable|out|returning/.test(storyText) ? 2.5 : 0
    return marketGap * 1.15 + closeness + spreadEdge + sourceDepth + eventBonus + peopleBonus
  }
  const spotlight = [...games].sort((a,b)=>editorialScore(b)-editorialScore(a))[0]
  const watch = useMemo(() => [...games].filter(g => g.game_id !== spotlight?.game_id).sort((a,b)=>editorialScore(b)-editorialScore(a)).slice(0,3), [games,spotlight?.game_id,evidence,previews])
  const sorted = useMemo(() => {
    const copy=[...games]
    if (sortMode==='strength') return copy.sort((a,b)=>(b.pickP||0)-(a.pickP||0))
    if (sortMode==='edge') return copy.sort((a,b)=>(b.pickEdge??-999)-(a.pickEdge??-999))
    if (sortMode==='close') return copy.sort((a,b)=>Math.abs((a.pickP||.5)-.5)-Math.abs((b.pickP||.5)-.5))
    return copy.sort((a,b)=>(easternKickoff(a)?.getTime()||0)-(easternKickoff(b)?.getTime()||0))
  },[games,sortMode])
  return <main className="pub-main">
    <CompactHero games={games} history={history} status={status} onPreviousWeek={onPreviousWeek} />
    <Spotlight game={spotlight} preview={previews[spotlight?.game_id]} onOpen={setSelected} />
    <GamesToWatch games={watch} previews={previews} locked={locked} onOpen={setSelected} />
    <section className="pub-slate vnext-slate">
      <div className="pub-section-head"><div><span>FULL BOARD</span><h2>Every game, one clean read.</h2></div><div className="pub-sort">{[['kickoff','Kickoff'],['strength','Strongest'],['edge','Biggest edge'],['close','Closest']].map(([key,label])=><button key={key} className={sortMode===key?'active':''} onClick={()=>setSortMode(key)}>{label}</button>)}</div></div>
      <div className="pub-card-grid">{sorted.map(game => <GameCard key={game.game_id} game={game} preview={previews[game.game_id]} evidence={evidence[game.game_id]||[]} locked={locked.has(game.game_id)} onOpen={()=>setSelected(game)} />)}</div>
    </section>
  </main>
}'''
replace(r'function WeekPage\(\{ games, evidence, previews, history, status, setSelected, onPreviousWeek \}\) \{.*?\n\}\n\nfunction ModelConsensus', week_page + '\n\nfunction ModelConsensus', 'WeekPage')

model_consensus = r'''function ModelConsensus({ game }) {
  const engines = [
    ['Logistic',game.logistic_home_prob],['Extra Trees',game.extra_trees_home_prob],['XGBoost',game.xgboost_home_prob],['CatBoost',game.catboost_home_prob],['Elo',game.elo_home_prob],
  ].map(([label,value]) => ({label,value:pickProbability(game,value)})).filter(row => row.value != null)
  const pure = pickProbability(game,game.pure_home_prob)
  const market = pickProbability(game,game.market_home_prob)
  const final = game.pickP
  const bullish = engines.filter(row=>row.value>.5).length
  const highest = [...engines].sort((a,b)=>b.value-a.value)[0]
  const lowest = [...engines].sort((a,b)=>a.value-b.value)[0]
  const spread = highest && lowest ? (highest.value-lowest.value)*100 : 0
  const summary = engines.length ? `${bullish} of ${engines.length} football engines lean ${game.pick}. ${spread >= 15 ? `${highest.label} is the high case and ${lowest.label} is the low case.` : `The engines are relatively compact, with ${highest.label} highest.`}` : 'Component probabilities are not available yet.'
  return <section className="vnext-consensus">
    <div className="pub-block-head"><span>MODEL CONSENSUS</span><b>{summary}</b></div>
    <div className="vnext-consensus-list">
      {engines.map(row=><div className="vnext-consensus-row" key={row.label}><div><span>{row.label}</span><b>{pct(row.value,0)}</b></div><div className="vnext-consensus-track"><i className="mid"/><em style={{left:`${probabilityAxisPosition(row.value)}%`}}/></div></div>)}
    </div>
    <div className="pub-gap-scale vnext-axis-scale"><span>40%</span><span>50</span><span>60</span><span>70</span><span>80%+</span></div>
    <div className="vnext-consensus-output vnext-consensus-formula"><span><small>PURE</small><b>{pct(pure)}</b><em>football only</em></span><i>× 75%</i><span><small>MARKET</small><b>{pct(market)}</b><em>vig-free signal</em></span><i>× 25%</i><span className="final"><small>LEVLINE</small><b>{game.pick} {pct(final)}</b><em>published probability</em></span></div>
    <p className="vnext-consensus-note">Each row uses the same probability scale. Exact values stay visible even when several engines cluster together.</p>
  </section>
}'''
replace(r'function ModelConsensus\(\{ game \}\) \{.*?\n\}\n\nfunction QuickNumbers', model_consensus + '\n\nfunction QuickNumbers', 'ModelConsensus')

matchup_meter = r'''function MatchupMeter({ rows=[], evidence=[], game }) {
  if (!rows.length) return null
  const detailFor = row => evidence.find(item => item.title === row.title) || {}
  return <section className="pub-article-block vnext-meter-block"><div className="pub-block-head"><span>MATCHUP EDGES</span><b>Qualitative unless the underlying evidence supplies a real numeric differential</b></div><div className="vnext-meter">{rows.map((row,index)=>{const detail=detailFor(row);const leader=row.leader||'Mixed';return <div className="vnext-meter-row vnext-edge-card" key={`${row.label}-${index}`}><div className="vnext-meter-head"><span>{row.label}</span><b>{['Watch','Mixed','Even'].includes(leader)?leader:`Edge ${leader}`} · {row.strength || 'Context'}</b></div><h4>{row.title || detail.title || 'Matchup signal'}</h4><p>{detail.summary || row.summary || 'This signal is worth monitoring as the matchup develops.'}</p></div>})}</div></section>
}'''
replace(r'function MatchupMeter\(\{ rows=\[\], evidence=\[\], game \}\) \{.*?\n\}\n\nfunction ForecastMovement', matchup_meter + '\n\nfunction ForecastMovement', 'MatchupMeter')

movement_component = r'''
function MovementAttribution({ movement }) {
  if (!movement) return null
  const driver = movement.largest_driver || 'No material move'
  const move = num(movement.pick_delta_pp)
  const model = num(movement.model_component_pp)
  const market = num(movement.market_component_pp)
  const residual = num(movement.residual_component_pp)
  const pp = value => value == null ? '—' : `${value>=0?'+':''}${value.toFixed(2)} pp`
  return <section className="vnext-movement-note"><div className="pub-block-head"><span>WHAT MOVED THE NUMBER</span><b>{driver}</b></div><div className="vnext-movement-grid"><Stat label="Latest LevLine move" value={pp(move)}/><Stat label="Football-model component" value={pp(model)}/><Stat label="Market component" value={pp(market)}/><Stat label="Residual / data transition" value={pp(residual)}/></div><p>This is arithmetic attribution of the latest forecast change. It does not claim that a contemporaneous injury, weather or news item caused the move unless that information is actually an input to the numerical model.</p></section>
}
'''
replace(r'(function ForecastMovement\(\{ game, runs \}\) \{.*?\n\}\n)\nfunction GameModal', r'\1' + movement_component + '\nfunction GameModal', 'MovementAttribution insert')

text = text.replace('function GameModal({ game, runs, evidence=[], preview, locked, sources, onClose }) {','function GameModal({ game, runs, evidence=[], preview, locked, sources, movement, onClose }) {')
text = text.replace('    <ForecastMovement game={game} runs={runs}/>\n\n    <section className="pub-article-block pub-wrong vnext-wrong">','    <ForecastMovement game={game} runs={runs}/>\n    <MovementAttribution movement={movement}/>\n\n    <section className="pub-article-block pub-wrong vnext-wrong">')

teams_block = r'''function TeamsPage({ profiles, setTeam, powerEditorial }) {
  const rows=[...profiles].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  const editorialByTeam=Object.fromEntries((powerEditorial?.teams||[]).map(row=>[row.team,row]))
  return <main className="pub-inner"><PageHead kicker="32 TEAM PROFILES" title="The league, one team at a time." copy="Current strength, efficiency, the next LevLine forecast, and the short explanation for why each team sits where it does."/><div className="pub-team-grid vnext-team-grid-rich">{rows.map(row=>{const note=editorialByTeam[row.team]||{};return <button key={row.team} onClick={()=>setTeam({...row,editorial:note})}><TeamMark team={row.team}/><span>#{row.rank} {note.movement||''}</span><h3>{teamName(row.team)}</h3><div><small>Elo+</small><b>{num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</b></div><div><small>Next</small><b>{row.next_opponent?`${row.next_site==='HOME'?'vs':'@'} ${row.next_opponent}`:'TBD'}</b></div><div><small>Win</small><b>{pct(row.next_win_prob)}</b></div>{note.why_here&&<p>{note.why_here}</p>}</button>})}</div></main>
}
function TeamModal({ team,onClose }) {
  const note=team.editorial||{}
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-team-modal vnext-team-modal-rich" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><TeamMark team={team.team} size="lg"/><span>POWER RANK #{team.rank} {note.movement||''}</span><h2>{teamName(team.team)}</h2>{note.why_here&&<p className="vnext-team-thesis">{note.why_here}</p>}<div className="pub-number-grid"><Stat label="Elo+" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label="Off EPA" value={num(team.off_epa)==null?'—':num(team.off_epa).toFixed(3)}/><Stat label="Def EPA allowed" value={num(team.def_epa_allowed)==null?'—':num(team.def_epa_allowed).toFixed(3)}/><Stat label="Pass EPA" value={num(team.pass_epa)==null?'—':num(team.pass_epa).toFixed(3)}/><Stat label="Recent" value={pct(team.recent_win_pct,0)}/><Stat label="Next win" value={pct(team.next_win_prob)}/><Stat label="Next projected points" value={one(team.next_projected_points)}/><Stat label="Next game" value={team.next_opponent?`${team.next_site==='HOME'?'vs':'@'} ${team.next_opponent}`:'TBD'} sub={team.next_game_date||''}/></div>{note.what_moves_them&&<div className="vnext-team-pressure"><span>WHAT MOVES THEM</span><p>{note.what_moves_them}</p></div>}</div></div>
}
'''
replace(r'function TeamsPage\(\{ profiles, setTeam \}\) \{.*?\n\}\nfunction TeamModal\(\{ team,onClose \}\) \{.*?\n\}\n\nfunction RatingsPage', teams_block + '\nfunction RatingsPage', 'Teams/TeamModal')

ratings = r'''function RatingsPage({ rows, editorial }) {
  const sorted=[...rows].sort((a,b)=>(num(a.rank)||999)-(num(b.rank)||999))
  const byTeam=Object.fromEntries((editorial?.teams||[]).map(row=>[row.team,row]))
  return <main className="pub-inner"><PageHead kicker="POWER RATINGS" title="LevLine's current league table." copy="Elo+ sets the published rank. Recent efficiency is shown as supporting or conflicting evidence rather than being quietly blended into a second hidden ranking."/><div className="vnext-power-list">{sorted.map(row=>{const note=byTeam[row.team]||{};const metrics=Object.entries(note.supporting_metric_ranks||{}).sort((a,b)=>a[1]-b[1]).slice(0,3);return <article key={row.team}><div className="vnext-power-rank"><b>#{row.rank}</b><span>{note.movement||'→'} {note.movement_text||'steady'}</span></div><div className="vnext-power-team"><TeamMark team={row.team}/><div><h3>{teamName(row.team)}</h3><span>Elo+ {num(row.elo_plus)==null?'—':Math.round(num(row.elo_plus))}</span></div></div><div className="vnext-power-copy"><p>{note.why_here||'The published rank comes from Elo+; supporting efficiency context is still being assembled.'}</p>{note.what_moves_them&&<small>{note.what_moves_them}</small>}</div><div className="vnext-power-metrics">{metrics.map(([label,rank])=><span key={label}><b>#{rank}</b> {label}</span>)}</div></article>})}</div></main>
}'''
replace(r'function RatingsPage\(\{ rows \}\) \{.*?\n\}\n\nfunction HistoryPage', ratings + '\n\nfunction HistoryPage', 'RatingsPage')

history = r'''function HistoryPage({ history, autopsies, calibration, weekFilter, setWeekFilter }) {
  const visible = weekFilter ? history.filter(row=>Number(row.week)===Number(weekFilter)) : history
  const correctFor = row => {
    const item=autopsies[row.game_id]||{}
    const value=item.winner_correct ?? item.correct
    if (value == null || value === '') return null
    return String(value).toLowerCase()==='true'
  }
  const graded=history.filter(row=>correctFor(row)!=null)
  const wins=graded.filter(row=>correctFor(row)===true).length
  return <main className="pub-inner"><PageHead kicker="OFFICIAL HISTORY" title="The receipts stay on the table." copy="Only the first valid pregame lock is graded. No hindsight edit, no quiet probability swap, no pretending the miss was actually a win."/>
    {weekFilter && <button className="vnext-clear-filter" onClick={()=>setWeekFilter(null)}>← All official history</button>}
    <div className="pub-history-summary vnext-history-summary"><Stat label="Official locks" value={history.length} sub="Immutable snapshots"/><Stat label="Record" value={graded.length?`${wins}-${graded.length-wins}`:'—'} sub={graded.length?`${pct(wins/graded.length,0)} winner accuracy`:'Starts after games finish'}/><Stat label="Calibration" value={calibration.length?`${calibration.length} buckets`:'Forward test'} sub="Probability quality, not just picks"/><Stat label="Policy" value="No edits" sub="After official lock"/></div>
    {calibration.length>0 && <section className="vnext-history-cal"><span>CALIBRATION</span><h3>When LevLine says 70%, does reality look like 70%?</h3><div>{calibration.map((row,index)=><div key={index}><b>{row.bucket||row.probability_bucket||`${pct(row.bin_low||0,0)}–${pct(row.bin_high||0,0)}`}</b><span>{row.games||row.n||'—'} games</span><em>{row.actual_win_rate||row.observed_rate||row.observed_home_win||'—'}</em></div>)}</div></section>}
    {visible.length?<div className="pub-table"><table><thead><tr><th>Week</th><th>Matchup</th><th>Pick</th><th>Probability</th><th>Projected</th><th>Result</th></tr></thead><tbody>{visible.map((row,index)=>{const correct=correctFor(row);return <tr key={`${row.game_id}-${index}`}><td>{row.week||'—'}</td><td>{row.away_team&&row.home_team?`${row.away_team} @ ${row.home_team}`:row.game_id}</td><td><b>{row.pick||'—'}</b></td><td>{pct(row.pick_prob||row.final_pick_prob||row.final_home_prob)}</td><td>{row.projected_score||'—'}</td><td>{correct!=null?(correct?'✓ Correct':'✕ Miss'):'Pending'}</td></tr>})}</tbody></table></div>:<div className="pub-empty-state">The ledger starts with the first official lock.</div>}
  </main>
}'''
replace(r'function HistoryPage\(\{ history, autopsies, calibration, weekFilter, setWeekFilter \}\) \{.*?\n\}\n\nfunction MethodPage', history + '\n\nfunction MethodPage', 'HistoryPage')

# Simplify the Method pipeline without changing model semantics.
text = text.replace("  const nodes=[\n    ['NFL DATA','EPA · success · explosives · turnovers · Elo · QB · rest/travel'],\n    ['FEATURE ENGINEERING','Recent form + matchup-independent football signals'],\n    ['MODEL ENSEMBLE','Logistic · Extra Trees · XGBoost · CatBoost · Elo/SuJaR'],\n    ['PURE','Football-only win probability'],\n    ['MARKET','Consensus implied probability'],\n    ['LEVLINE','75% PURE + 25% MARKET'],\n    ['T−120 LOCK','First valid pregame forecast becomes official'],\n    ['AUDIT','Brier · calibration · log loss · score/margin error'],\n  ]", "  const nodes=[\n    ['FOOTBALL DATA','EPA · success · explosives · turnovers · QB/team strength · rest/travel'],\n    ['PURE','Logistic · Extra Trees · XGBoost · CatBoost · Elo/SuJaR → football-only probability'],\n    ['MARKET','Vig-free consensus probability, kept separate from PURE'],\n    ['LEVLINE','75% PURE + 25% MARKET'],\n    ['T−120 LOCK','First valid pregame forecast becomes immutable'],\n    ['AUDIT','Brier · calibration · log loss · margin/total error · market comparison'],\n  ]")

# Add power editorial and movement attribution feeds to app state/loading.
text = text.replace("  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [calibration,setCalibration]=useState([]), [autopsies,setAutopsies]=useState({})", "  const [ratings,setRatings]=useState([]), [models,setModels]=useState([]), [history,setHistory]=useState([]), [profiles,setProfiles]=useState([]), [calibration,setCalibration]=useState([]), [autopsies,setAutopsies]=useState({}), [powerEditorial,setPowerEditorial]=useState({teams:[]}), [movement,setMovement]=useState([])")
text = text.replace("    const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto]=await Promise.all([", "    const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto,pe,mv]=await Promise.all([")
text = text.replace("      fetchCSV('this_week.csv'),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('context_source_status.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchCSV('calibration.csv'),fetchJSON('postgame_autopsies.json',{}),", "      fetchCSV('this_week.csv'),fetchCSV('run_history.csv'),fetchJSON('contextual_evidence.json',{}),fetchJSON('game_previews.json',{}),fetchJSON('context_source_status.json',{}),fetchJSON('status.json',{}),fetchCSV('power_ratings.csv'),fetchCSV('model_leaderboard.csv'),fetchCSV('prediction_history.csv'),fetchCSV('team_profiles.csv'),fetchCSV('calibration.csv'),fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchCSV('movement_attribution.csv'),")
text = text.replace("    setGames(g.map(normalizeGame));setRuns(r);setEvidence(e);setPreviews(p);setSources(s);setStatus(st);setRatings(pr);setModels(ml);setHistory(h);setProfiles(tp);setCalibration(cal);setAutopsies(auto)", "    setGames(g.map(normalizeGame));setRuns(r);setEvidence(e);setPreviews(p);setSources(s);setStatus(st);setRatings(pr);setModels(ml);setHistory(h);setProfiles(tp);setCalibration(cal);setAutopsies(auto);setPowerEditorial(pe);setMovement(mv)")
text = text.replace("    {tab==='teams'&&<TeamsPage profiles={profiles} setTeam={setTeam}/>} ", "    {tab==='teams'&&<TeamsPage profiles={profiles} setTeam={setTeam} powerEditorial={powerEditorial}/>} ")
text = text.replace("    {tab==='ratings'&&<RatingsPage rows={ratings}/>} ", "    {tab==='ratings'&&<RatingsPage rows={ratings} editorial={powerEditorial}/>} ")
text = text.replace("    {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} sources={sources} onClose={()=>setSelected(null)}/>} ", "    {selected&&<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} sources={sources} movement={movement.find(row=>row.game_id===selected.game_id)} onClose={()=>setSelected(null)}/>} ")

app_path.write_text(text, encoding='utf-8')

css = css_path.read_text(encoding='utf-8')
marker = '/* FRONTEND-POLISH-2026 */'
if marker not in css:
    css += r'''

/* FRONTEND-POLISH-2026 */
.vnext-consensus-list{display:grid;gap:9px;margin:18px 0 8px}.vnext-consensus-row{display:grid;grid-template-columns:96px 1fr;gap:12px;align-items:center}.vnext-consensus-row>div:first-child{display:flex;align-items:baseline;justify-content:space-between;gap:8px}.vnext-consensus-row span{font-size:8px;color:#8298a8;letter-spacing:.05em}.vnext-consensus-row b{font-size:11px;color:#c6d1d9}.vnext-consensus-track{position:relative;height:8px;border-radius:999px;background:linear-gradient(90deg,#172c39,#254758)}.vnext-consensus-track .mid{position:absolute;left:25%;top:-4px;width:1px;height:16px;background:#557083}.vnext-consensus-track em{position:absolute;top:50%;transform:translate(-50%,-50%);width:11px;height:11px;border-radius:50%;background:var(--signal);border:2px solid #07131d;box-shadow:0 0 10px rgba(104,216,199,.28)}.vnext-consensus-formula{grid-template-columns:1fr 54px 1fr 54px 1.35fr}.vnext-consensus-formula>i{font-size:8px}.vnext-consensus-formula em{font-style:normal;color:#667f91;font-size:7px;margin-top:2px}.vnext-consensus-note{margin:10px 0 0;color:#6f8798;font-size:8px;line-height:1.45}
.vnext-edge-card h4{margin:9px 0 6px;font-family:Georgia,"Times New Roman",serif;font-size:14px;color:#d1d9df}.vnext-edge-card .vnext-meter-head b{color:var(--signal)}
.vnext-movement-note{max-width:1060px;margin:10px auto 18px;border:1px solid #183041;border-radius:14px;background:#081721;padding:17px}.vnext-movement-note .pub-block-head{margin-bottom:10px}.vnext-movement-note .pub-block-head>b{color:#9cb0bd;font-size:9px}.vnext-movement-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:8px}.vnext-movement-grid .pub-stat{min-height:70px;background:#091822}.vnext-movement-note>p{margin:10px 0 0;color:#7890a1;font-size:9px;line-height:1.5}
.vnext-power-list{display:grid;gap:9px}.vnext-power-list article{display:grid;grid-template-columns:68px 220px minmax(0,1fr) minmax(220px,.65fr);gap:16px;align-items:center;border:1px solid #183041;border-radius:14px;background:#091822;padding:15px 17px}.vnext-power-rank b{display:block;font-size:23px}.vnext-power-rank span{display:block;color:#6f8798;font-size:8px;margin-top:4px}.vnext-power-team{display:flex;align-items:center;gap:10px}.vnext-power-team h3{margin:0;font-size:15px}.vnext-power-team span{display:block;color:#71899a;font-size:8px;margin-top:3px}.vnext-power-copy p{margin:0;color:#c0ccd4;font-family:Georgia,"Times New Roman",serif;font-size:12px;line-height:1.5}.vnext-power-copy small{display:block;color:#71899a;font-size:8px;line-height:1.45;margin-top:5px}.vnext-power-metrics{display:flex;flex-wrap:wrap;gap:5px;justify-content:flex-end}.vnext-power-metrics span{border:1px solid #1b3445;border-radius:999px;padding:5px 7px;color:#7e94a5;font-size:7px}.vnext-power-metrics b{color:#b9c7d0}
.vnext-team-grid-rich>button>p{grid-column:1/-1;margin:8px 0 0;color:#8ea2b0;font-family:Georgia,"Times New Roman",serif;font-size:9px;line-height:1.45;text-align:left}.vnext-team-thesis{max-width:680px;margin:8px auto 16px;color:#c4d0d7;font-family:Georgia,"Times New Roman",serif;font-size:14px;line-height:1.6;text-align:center}.vnext-team-pressure{margin-top:14px;border-top:1px solid #183041;padding-top:12px}.vnext-team-pressure span{font-size:8px;color:var(--signal);letter-spacing:.12em}.vnext-team-pressure p{margin:5px 0 0;color:#879ba9;font-size:10px;line-height:1.5}
@media(max-width:900px){.vnext-power-list article{grid-template-columns:54px 1fr}.vnext-power-copy,.vnext-power-metrics{grid-column:1/-1}.vnext-power-metrics{justify-content:flex-start}.vnext-movement-grid{grid-template-columns:1fr 1fr}.vnext-consensus-row{grid-template-columns:82px 1fr}.vnext-consensus-formula{grid-template-columns:1fr 42px 1fr}.vnext-consensus-formula>i:nth-of-type(2),.vnext-consensus-formula .final{grid-column:auto}.vnext-consensus-formula .final{grid-column:1/-1;margin-top:8px}}
'''
    css_path.write_text(css, encoding='utf-8')

print('Applied front-facing Sunday Signal polish: consensus rows, qualitative matchup edges, editorial spotlight, movement attribution, richer Power/Teams, and History fix.')
