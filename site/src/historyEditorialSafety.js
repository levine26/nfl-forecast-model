export function canUseCurrentPreviewForReceipt({ gameId, currentGame, preview }) {
  const id = String(gameId || '').trim()
  if (!id || !currentGame || !preview) return false
  if (String(currentGame.game_id || '').trim() !== id) return false
  if (String(preview.game_id || '').trim() !== id) return false

  // Historical editorial must fail closed. game_previews.json is a mutable
  // current-slate artifact, so a receipt may consume it only while that exact
  // matchup is still in the immutable FINAL_PREGAME lifecycle. Once the game
  // starts, is graded, or disappears from the current slate, the receipt must
  // not relabel mutable/current prose as the original pregame Signal.
  const lifecycle = String(currentGame.lifecycle_status || '').trim().toUpperCase()
  if (lifecycle !== 'FINAL_PREGAME') return false

  const lock = Date.parse(currentGame.lock_timestamp_utc || '')
  const kickoff = Date.parse(currentGame.kickoff_utc || '')
  if (Number.isFinite(lock) && Number.isFinite(kickoff) && lock > kickoff) return false

  return true
}
