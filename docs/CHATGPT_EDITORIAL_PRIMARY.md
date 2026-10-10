# Sunday Signal editorial provider authority — October 2026

This document supersedes the historical ChatGPT-primary experiment that temporarily
retired autonomous Groq dispatch. The official forecasting system remains
`F-ST-01-FROZEN-2026`, with an immutable prediction-lock history.

## Production authority

Groq is the primary automated human-matchup writer. The
`Sunday Signal Groq post-context dispatcher` observes successful contextual
intelligence runs and dispatches the existing Groq media writer only when the
current slate lacks complete validated human layers, material freshness
advisories exist, or the current provider artifact is older than 36 hours.

Provider spend is bounded by deduplication against active writer runs and a
six-hour retry cooldown after a failed provider run. The writer itself still
requires fresh contextual inputs and enforces focused game validation,
independent direct reporting, full-slate validation, and exact deterministic
F-ST numerical paragraph parity before publication.

## ChatGPT recovery

The ChatGPT consumer application cannot be invoked autonomously by GitHub
Actions. The `inputs/chatgpt_media/fallback/<game_id>.json` and
`inputs/chatgpt_media/fallback/manifest.json` contract is an honest,
explicit human handoff for failed Groq games. The `ChatGPT primary editorial
ingestion` workflow remains manual-only as an emergency recovery surface.
It must not automatically overwrite newer validated Groq human prose.

Successful Groq games survive unrelated contextual and numerical refreshes.
Fresh deterministic paragraph 2 comes only from canonical F-ST/market
data. Missing ChatGPT payloads do not count as successful recoveries.

## Operational conditions

1. If a current game is absent from the provider artifact, expect an
   autonomous Groq dispatch after the next successful contextual run.
2. If a writer is already active, do not dispatch another writer.
3. If the last writer failed within six hours, report the failure and wait
   for the next eligible context heartbeat rather than repeatedly billing
   the provider.
4. If the Groq secret is absent, the writer fails; no generic text is
   promoted as provider-authored content.
5. A green Groq workflow is not a live editorial acceptance receipt:
   inspect the current complete output and the deployed site.
6. If the context workflow fails, leave the last published canonical
   model and validated human content intact; do not run a provider
   against stale source evidence.

The official model, official win probabilities, historical locks,
grading, and research firewall are out of scope for editorial changes.
