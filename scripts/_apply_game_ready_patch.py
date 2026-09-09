from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if text.count(old) != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {text.count(old)}")
    return text.replace(old, new, 1)


app_path = Path("site/src/AppPublication.jsx")
app = app_path.read_text(encoding="utf-8")

# 1) Movement attribution + conditional-scenario guardrail components.
anchor = "function GameModal({ game, runs, evidence=[], preview, locked, onClose }) {"
components = r'''function MovementAttribution({ game, rows=[] }) {
  const row=[...rows].filter(item=>item.game_id===game.game_id).sort((a,b)=>new Date(a.to_timestamp_utc)-new Date(b.to_timestamp_utc)).at(-1)
  if (!row) return <section className="pub-article-block movement-panel"><div className="pub-block-head"><span>WHAT MOVED THE NUMBER?</span></div><p className="pub-empty">Attribution appears after two comparable forecast snapshots.</p></section>
  const parts=[
    ['Football model',num(row.model_component_pp)],
    ['Market',num(row.market_component_pp)],
    ['Residual',num(row.residual_component_pp)],
  ]
  return <section className="pub-article-block movement-panel"><div className="pub-block-head"><span>WHAT MOVED THE NUMBER?</span><b>{row.largest_driver||'Latest run'}</b></div><div className="movement-grid">{parts.map(([label,value])=><div key={label}><span>{label}</span><b>{value==null?'—':`${value>=0?'+':''}${value.toFixed(2)} pp`}</b></div>)}</div><p>The latest published move was <b>{num(row.pick_delta_pp)==null?'—':`${num(row.pick_delta_pp)>=0?'+':''}${num(row.pick_delta_pp).toFixed(2)} percentage points`}</b> toward the current pick. Personnel, weather and staff notes are not credited as causes because they are not numerical LevLine inputs unless separately validated.</p></section>
}

function ScenarioBoard({ game, evidence=[], locked }) {
  const candidates=evidence.filter(item=>['injury','personnel','weather','travel','scenario'].includes(String(item.category||'').toLowerCase())).slice(0,5)
  return <section className="pub-article-block scenario-board"><div className="pub-block-head"><span>CONDITIONAL SCENARIO BOARD</span><b>{locked?'OFFICIAL LOCKED':'PREGAME'}</b></div><p className="scenario-lead">This is the line Sunday Signal will not cross: no made-up injury points and no fake weather delta. A conditional probability appears only when the underlying scenario can be recomputed from a numerically validated feature.</p>{candidates.length?<div className="scenario-list">{candidates.map((item,index)=><div key={`${item.title}-${index}`}><span>{String(item.category||'context').toUpperCase()}</span><b>{item.title}</b><p>{item.summary}</p><em>Context only · no validated probability delta</em></div>)}</div>:<p className="pub-empty">No material conditional scenario is active right now.</p>}<small>{locked?'The official T−120 forecast is immutable even if explanatory context changes later.':'Current forecast can still update through the validated pipeline before the official lock.'}</small></section>
}

'''
app = replace_once(app, anchor, components + "function GameModal({ game, runs, movement=[], evidence=[], preview, locked, onClose }) {", "GameModal anchor")

# Put attribution and scenario logic directly in the dossier.
old = "</div></div><MarketGap game={game}/><div className=\"pub-modal-grid\"><article>"
new = "</div></div><MarketGap game={game}/><MovementAttribution game={game} rows={movement}/><div className=\"pub-modal-grid\"><article><ScenarioBoard game={game} evidence={evidence} locked={locked}/>"
app = replace_once(app, old, new, "dossier insert")

# 2) Deep team dossier from feeds already produced by the model/context jobs.
old_team = "function TeamModal({ team,onClose }) { return <div className=\"pub-modal-backdrop\" onClick={onClose}><div className=\"pub-team-modal\" onClick={e=>e.stopPropagation()}><button className=\"pub-close\" onClick={onClose}>×</button><TeamMark team={team.team} size=\"lg\"/><span>POWER RANK #{team.rank}</span><h2>{teamName(team.team)}</h2><div className=\"pub-number-grid\"><Stat label=\"Elo+\" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label=\"Off EPA\" value={three(team.off_epa)}/><Stat label=\"Def EPA allowed\" value={three(team.def_epa_allowed)}/><Stat label=\"Pass EPA\" value={three(team.pass_epa)}/><Stat label=\"Recent\" value={pct(team.recent_win_pct,0)}/><Stat label=\"Next win\" value={pct(team.next_win_prob)}/></div></div></div> }"
new_team = r'''function TeamModal({ team, games=[], runs=[], evidence={}, history=[], autopsies={}, powerEditorial, onClose }) {
  const note=(powerEditorial?.teams||[]).find(item=>item.team===team.team)||{}
  const game=games.find(item=>item.game_id===team.next_game_id)
  const board=evidence[team.next_game_id]||[]
  const personnel=board.filter(item=>['injury','personnel'].includes(String(item.category||'').toLowerCase())).slice(0,4)
  const snapshots=runs.filter(row=>row.game_id===team.next_game_id).sort((a,b)=>new Date(a.prediction_timestamp_utc)-new Date(b.prediction_timestamp_utc))
  const teamProb=row=>{const hp=num(row?.final_home_prob);if(hp==null)return null;return row.home_team===team.team?hp:1-hp}
  const first=teamProb(snapshots[0]), current=teamProb(snapshots.at(-1)), delta=first==null||current==null?null:(current-first)*100
  const official=history.filter(row=>row.lock_status==='LOCKED'&&(row.home_team===team.team||row.away_team===team.team)).sort((a,b)=>(num(b.week)||0)-(num(a.week)||0))
  const postgames=official.map(row=>autopsies[row.game_id]).filter(Boolean)
  return <div className="pub-modal-backdrop" onClick={onClose}><div className="pub-team-modal team-dossier" onClick={e=>e.stopPropagation()}><button className="pub-close" onClick={onClose}>×</button><div className="team-dossier-head"><TeamMark team={team.team} size="lg"/><div><span>POWER RANK #{team.rank} · {note.movement_text||'steady'}</span><h2>{teamName(team.team)}</h2><p>{note.why_here||`Elo+ currently places ${team.team} at No. ${team.rank}.`}</p></div></div><div className="pub-number-grid"><Stat label="Elo+" value={num(team.elo_plus)==null?'—':Math.round(num(team.elo_plus))}/><Stat label="Off EPA" value={three(team.off_epa)}/><Stat label="Def EPA allowed" value={three(team.def_epa_allowed)}/><Stat label="Pass EPA" value={three(team.pass_epa)}/><Stat label="Recent" value={pct(team.recent_win_pct,0)}/><Stat label="Next win" value={pct(team.next_win_prob)}/></div><section className="team-dossier-section"><span>TEAM READ</span><h3>Why they are here</h3><p>{note.why_here||'The published power rank is the current Elo+ ordering.'}</p><small><b>What could move them:</b> {note.what_moves_them||'New game data will determine the next meaningful move.'}</small></section><section className="team-dossier-grid"><div><span>NEXT GAME</span><h3>{team.next_opponent?`${team.next_site==='HOME'?'vs':'@'} ${team.next_opponent}`:'TBD'}</h3><p>{game?kickoffText(game):team.next_game_date||'Schedule pending'}</p><b>{pct(team.next_win_prob)} win · {one(team.next_projected_points)} projected points</b></div><div><span>FORECAST TRAJECTORY</span><h3>{current==null?'—':pct(current)}</h3><p>{delta==null?'Waiting for comparable snapshots':`${delta>=0?'+':''}${delta.toFixed(1)} pp since first published run`}</p><b>{snapshots.length} model snapshot{snapshots.length===1?'':'s'}</b></div></section><section className="team-dossier-section"><span>PERSONNEL BOARD</span><h3>Current matchup availability</h3>{personnel.length?<div className="team-personnel-list">{personnel.map((item,index)=><div key={`${item.title}-${index}`}><b>{item.title}</b><p>{item.summary}</p><small>{item.strength||'Context'}</small></div>)}</div>:<p className="pub-empty">Nothing material on the current official availability board.</p>}</section><section className="team-dossier-section"><span>OFFICIAL FORECAST HISTORY</span><h3>The immutable record for {team.team}</h3>{official.length?<div className="team-history-list">{official.slice(0,8).map(row=>{const auto=autopsies[row.game_id];const hp=num(row.final_home_prob);const p=hp==null?null:(row.home_team===team.team?hp:1-hp);return <div key={row.game_id}><b>W{row.week} · {row.away_team} @ {row.home_team}</b><span>{pct(p)}</span><em>{auto?.winner_correct==null?'Pending':auto.winner_correct?'✓ Right':'✕ Miss'}</em></div>})}</div>:<p className="pub-empty">This fills after the first official T−120 lock involving {team.team}.</p>}{postgames.length>0&&<small>{postgames.length} postgame review{postgames.length===1?'':'s'} available in History.</small>}</section></div></div>
}'''
app = replace_once(app, old_team, new_team, "TeamModal replacement")

# 3) Postgame review cards + fix the old `correct` field name to the actual schema.
history_anchor = "function HistoryPage({ history, autopsies, scoreboard, calibration }) {"
postgame = r'''function PostgameReviews({ autopsies }) {
  const rows=Object.values(autopsies||{})
  if (!rows.length) return null
  return <section className="history-panel postgame-reviews"><span>POSTGAME REVIEW</span><h2>What the locked forecast got right—and what it missed.</h2><p>These notes are written from the immutable pregame snapshot. Hindsight can diagnose the miss; it cannot rewrite the forecast.</p><div className="postgame-grid">{rows.map(row=><article key={row.game_id}><div><b>{row.matchup}</b><span className={row.winner_correct?'result-good':'result-bad'}>{row.winner_correct?'Winner right':'Winner missed'}</span></div><h3>{row.projected_score||'Projection'} → {row.actual_score||'Result'}</h3>{(row.what_went_right||[]).map((text,index)=><p key={`r-${index}`}>✓ {text}</p>)}{(row.what_missed||[]).map((text,index)=><p key={`m-${index}`}>× {text}</p>)}{row.error_tags?.length>0&&<small>Error tags: {row.error_tags.join(' · ')}</small>}<em>{row.causal_analysis_status}</em></article>)}</div></section>
}

'''
app = replace_once(app, history_anchor, postgame + history_anchor, "PostgameReviews anchor")
app = app.replace("autopsies[row.game_id]?.correct!=null", "autopsies[row.game_id]?.winner_correct!=null")
app = app.replace("String(autopsies[row.game_id].correct).toLowerCase()==='true'", "String(autopsies[row.game_id].winner_correct).toLowerCase()==='true'")
old_history_tail = "}</div>:<div className=\"pub-empty-state\">The official ledger begins with the first T−120 lock.</div>}<p className=\"history-note\">No ROI is displayed unless Sunday Signal defines and timestamps a betting rule before the games. Prediction performance and betting performance are not the same thing.</p></main>"
new_history_tail = "}</div>:<div className=\"pub-empty-state\">The official ledger begins with the first T−120 lock.</div>}<PostgameReviews autopsies={autopsies}/><p className=\"history-note\">No ROI is displayed unless Sunday Signal defines and timestamps a betting rule before the games. Prediction performance and betting performance are not the same thing.</p></main>"
app = replace_once(app, old_history_tail, new_history_tail, "History tail")

# 4) Load the existing movement-attribution feed and pass richer data into dossiers.
app = replace_once(app,
    "const [powerEditorial,setPowerEditorial]=useState({teams:[]}), [scoreboard,setScoreboard]=useState({})",
    "const [powerEditorial,setPowerEditorial]=useState({teams:[]}), [scoreboard,setScoreboard]=useState({}), [movement,setMovement]=useState([])",
    "movement state")
app = replace_once(app,
    "const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto,pe,hs]=await Promise.all([",
    "const [g,r,e,p,s,st,pr,ml,h,tp,cal,auto,pe,hs,mv]=await Promise.all([",
    "fetch destructuring")
app = replace_once(app,
    "fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchJSON('history_scoreboard.json',{}),",
    "fetchJSON('postgame_autopsies.json',{}),fetchJSON('power_editorial.json',{teams:[]}),fetchJSON('history_scoreboard.json',{}),fetchCSV('movement_attribution.csv'),",
    "movement fetch")
app = replace_once(app,
    "setCalibration(cal);setAutopsies(auto);setPowerEditorial(pe);setScoreboard(hs)",
    "setCalibration(cal);setAutopsies(auto);setPowerEditorial(pe);setScoreboard(hs);setMovement(mv)",
    "movement setter")
app = replace_once(app,
    "<GameModal game={selected} runs={runs} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} onClose={()=>setSelected(null)}/>",
    "<GameModal game={selected} runs={runs} movement={movement} evidence={evidence[selected.game_id]||[]} preview={previews[selected.game_id]} locked={locked.has(selected.game_id)} onClose={()=>setSelected(null)}/>",
    "GameModal props")
app = replace_once(app,
    "<TeamModal team={team} onClose={()=>setTeam(null)}/>",
    "<TeamModal team={team} games={games} runs={runs} evidence={evidence} history={history} autopsies={autopsies} powerEditorial={powerEditorial} onClose={()=>setTeam(null)}/>",
    "TeamModal props")

app_path.write_text(app, encoding="utf-8")

# Add systematic error tags to the quantitative postgame autopsy. This remains
# diagnosis only and does not feed 2026 outcomes back into model selection.
diag_path = Path("src/nfl_forecast/diagnostics.py")
diag = diag_path.read_text(encoding="utf-8")
old = '''        gid = str(r.get("game_id"))\n        out[gid] = {\n            "game_id": gid,'''
new = '''        error_tags: list[str] = []\n        if winner_correct is False:\n            error_tags.append("winner_miss")\n        if margin_error is not None and margin_error > 7.0:\n            error_tags.append("margin_miss")\n        if total_error is not None and total_error > 7.0:\n            error_tags.append("total_miss")\n        if not error_tags:\n            error_tags.append("no_major_error_flag")\n\n        gid = str(r.get("game_id"))\n        out[gid] = {\n            "game_id": gid,'''
diag = replace_once(diag, old, new, "autopsy tags insertion")
diag = replace_once(diag,
    '            "what_missed": missed,\n            "causal_analysis_status":',
    '            "what_missed": missed,\n            "error_tags": error_tags,\n            "causal_analysis_status":',
    "autopsy tags output")
diag_path.write_text(diag, encoding="utf-8")

# CSS is additive and deliberately lightweight: no new charting/runtime dependency.
css_path = Path("site/src/accountability.css")
css = css_path.read_text(encoding="utf-8")
marker = "/* game-ready-dossiers-v1 */"
if marker not in css:
    css += r'''

/* game-ready-dossiers-v1 */
.movement-panel{max-width:940px;margin:0 auto 16px!important}.movement-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:12px 0}.movement-grid>div{padding:12px;border:1px solid rgba(148,163,184,.13);background:#0a1722;display:flex;flex-direction:column;gap:5px}.movement-grid span,.scenario-list span,.team-dossier-section>span,.team-dossier-grid>div>span{font-size:9px;letter-spacing:.1em;color:#68d8c7;font-weight:850}.movement-grid b{font-size:17px}.movement-panel>p,.scenario-board>p{color:#98a9bb;font-size:12px;line-height:1.55}.scenario-board{border-color:rgba(104,216,199,.24)!important}.scenario-lead{margin-top:0}.scenario-list{display:flex;flex-direction:column;border-top:1px solid rgba(148,163,184,.13);margin:14px 0}.scenario-list>div{padding:12px 0;border-bottom:1px solid rgba(148,163,184,.1)}.scenario-list b{display:block;margin:4px 0;font-size:13px}.scenario-list p{margin:0 0 6px;color:#95a6b8;font-size:12px;line-height:1.45}.scenario-list em{font-style:normal;font-size:10px;color:#f0c56c}.scenario-board>small{display:block;color:#75879a;line-height:1.45}.team-dossier{max-width:980px!important;padding:28px!important;background:#07131d!important;border:1px solid #29465a!important;border-radius:22px!important;position:relative}.team-dossier-head{display:flex;align-items:center;gap:16px;margin-bottom:20px}.team-dossier-head>div>span{font-size:9px;letter-spacing:.11em;color:#68d8c7;font-weight:850}.team-dossier-head h2{font-size:34px;margin:4px 0}.team-dossier-head p{margin:0;color:#9aabba;line-height:1.5}.team-dossier-section{margin-top:18px;padding:18px;border:1px solid rgba(148,163,184,.14);background:#0a1722}.team-dossier-section h3{margin:6px 0 8px;font-size:20px}.team-dossier-section p{color:#9aabba;line-height:1.55}.team-dossier-section>small{color:#7f92a7}.team-dossier-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:18px}.team-dossier-grid>div{padding:18px;border:1px solid rgba(148,163,184,.14);background:#0a1722}.team-dossier-grid h3{font-size:24px;margin:6px 0}.team-dossier-grid p{color:#91a2b5;margin:4px 0 10px}.team-personnel-list>div{padding:10px 0;border-top:1px solid rgba(148,163,184,.1)}.team-personnel-list>div:first-child{border-top:0}.team-personnel-list p{margin:4px 0}.team-personnel-list small{color:#6ed9c9}.team-history-list{display:flex;flex-direction:column}.team-history-list>div{display:grid;grid-template-columns:1fr 80px 70px;gap:12px;padding:9px 0;border-top:1px solid rgba(148,163,184,.1);align-items:center}.team-history-list span{color:#dce7ef}.team-history-list em{font-style:normal;color:#8da0b4;text-align:right}.postgame-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-top:14px}.postgame-grid article{padding:16px;border:1px solid rgba(148,163,184,.13);background:#081620}.postgame-grid article>div{display:flex;justify-content:space-between;gap:12px;align-items:center}.postgame-grid h3{font-size:17px;margin:10px 0}.postgame-grid p{margin:5px 0;color:#a9b7c5}.postgame-grid small{display:block;margin-top:10px;color:#f0c56c}.postgame-grid em{display:block;margin-top:9px;color:#718499;font-size:10px;line-height:1.45}@media(max-width:700px){.movement-grid,.team-dossier-grid,.postgame-grid{grid-template-columns:1fr}.team-dossier{width:100vw!important;border-radius:0!important;padding:20px 14px!important}.team-history-list>div{grid-template-columns:1fr 62px 58px}.team-dossier-head h2{font-size:28px}}
'''
css_path.write_text(css, encoding="utf-8")

# Temporary patcher and workflow remove themselves before committing so the PR
# contains only product/test changes.
Path("scripts/_apply_game_ready_patch.py").unlink(missing_ok=True)
Path(".github/workflows/_apply-game-ready-patch.yml").unlink(missing_ok=True)
