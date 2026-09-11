import React from 'react'
import './impact-monitor.css'

export default function ImpactMonitor({ gameMonitor }) {
  const players = Array.isArray(gameMonitor?.players) ? gameMonitor.players : []
  if (!players.length) return null

  return (
    <section className="co-section co-impact-monitor" aria-label="Impact Monitor">
      <div className="co-section-head">
        <span>IMPACT MONITOR</span>
        <small>Player context · explainability only · does not change the forecast</small>
      </div>
      <div className="co-impact-list">
        {players.map(player => (
          <article key={`${player.team}-${player.player_id}`} className="co-impact-card">
            <div className="co-impact-player">
              <b>{player.player_name}</b>
              <span>{player.team} · {player.position}</span>
            </div>
            {player.availability && (
              <p>
                <strong>Availability:</strong> {player.availability.game_status || player.availability.practice_status || 'status unavailable'}
                {player.availability.source_name ? ` · ${player.availability.source_name}` : ''}
              </p>
            )}
            {Array.isArray(player.levline_impacts) && player.levline_impacts.length > 0 && (
              <div className="co-impact-modeled">
                {player.levline_impacts.map((impact, index) => (
                  <p key={`${impact.metric || 'impact'}-${index}`}>
                    <strong>LevLine modeled:</strong> {impact.interpretation || impact.metric || 'player impact context'}
                  </p>
                ))}
              </div>
            )}
            {Array.isArray(player.observed_statistics) && player.observed_statistics.length > 0 && (
              <div className="co-impact-observed">
                {player.observed_statistics.map((stat, index) => (
                  <p key={`${stat.metric || 'stat'}-${index}`}>
                    <strong>Source observed:</strong> {stat.metric}: {String(stat.value)}{stat.unit ? ` ${stat.unit}` : ''}
                  </p>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
      <p className="co-impact-note">Only publication-approved source rows are shown. Player context is not an authorized F-ST probability feature.</p>
    </section>
  )
}
