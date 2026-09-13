# Immediate Groq -> ChatGPT editorial recovery

Sunday Signal keeps Groq as the primary autonomous human-Read provider, but provider failure is now game-scoped rather than slate-scoped.

For a specific matchup, a Groq request failure, focused validation failure, or a full-slate validator failure that names that game immediately invokes the ChatGPT editorial safety bridge. The bridge selects the freshest valid ChatGPT payload for that game from `inputs/chatgpt_media/fallback/` or `inputs/chatgpt_media/current/`; if neither is fresh, it may reuse the last already-validated human Read only as a continuity bridge and leaves `requires_chatgpt_refresh=true`.

Successful Groq games are never replaced merely because another game failed. Every mixed Groq/ChatGPT slate must still pass focused validation, full-slate source/prose/uniqueness/pick validation, deterministic LevLine paragraph-2 rendering, latest-main reconciliation, and the final publication gate.

The fallback is editorial-only. It cannot modify `F-ST-01-FROZEN-2026`, final probabilities, probability-implied presentation lines, model coefficients/features, locks, grading, or market inputs.
