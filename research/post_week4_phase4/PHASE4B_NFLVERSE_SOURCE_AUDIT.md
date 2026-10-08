# Phase 4B — NFLverse prospective EPA adapter qualification (2026-10-08)

**Decision: OFFLINE ADAPTER IMPLEMENTED / LIVE SOURCE UNQUALIFIED / CAPTURE DISABLED.** This work does not claim a real current-season PBP fetch or a prospective forecast.

## Independent public-source assessment

- nflverse-data releases store season PBP including the reported `play_by_play_2026.parquet`. An earlier October 7 asset inspection reported SHA-256 `1037ecb3e4cd2eddceea3be71d26fafc83475fc2979f32597c30d33141036ec5` with created 16:23:50 UTC/updated 16:23:52 UTC. **Historical observation only; not a current verified version or independent availability witness.** The current parquet bytes, asset response headers and exact expected play counts were **not acquired** in this research iteration; therefore the 2026 data are **not independently validated as complete**.
- nflverse-data advertises **CC BY 4.0** for its released data: https://github.com/nflverse/nflverse-data/blob/main/LICENSE.md . Reuse/transform under the licensor's grant is generally permitted with attribution if shared, subject to upstream/third-party rights and other applicable restrictions. This is *not* a legal clearance for uploading third-party raw game data publicly. No raw football data or secrets have been uploaded.
- nflverse's publication schedule describes regular PBP updates after game days and additional corrections Wednesday–Thursday: https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html . Current asset content may include corrections unavailable before earlier locks; thus each capture must save its exact byte hash and trusted acquisition receipt. Asset updated timestamps, response time, Git metadata and game completion time are distinct facts.
- `src/nfl_forecast/data.py` sets `NFLREADPY_CACHE_DURATION=21600` (six hours) and explicitly falls back to earlier seasons if current season PBP is absent. That is acceptable for production's graceful degradation but **unacceptable** for Candidate C's exact prior-2026-game requirement. The research adapter **never** uses fallback or a transparent nflreadpy cache. It only accepts explicit row material, a full regular-season schedule and a separate play-count manifest.

## Adapter

`nflverse_epa_adapter.py` deterministically reproduces the offense/defense EPA means of `features.aggregate_team_games` for valid REG PBP: possession-team mean and defending-team mean of non-null EPA after filtering plays without possession/defense. It reconstructs the frozen model's **eight previous-season games**, **all prior current-season games** and **previous-season league mean** without changing formula/weights.

It rejects duplicate/unexpected play IDs, season/week/team mismatch, nonfinite EPA, absent per-game observations, incorrect independent play counts, non-regular fixtures, target leakage and late acquisition. Fixture coverage and PBP payload completeness **cannot be proved by comparing a dataset only against itself**. A separate signed, complete fixture inventory and independently observed raw asset/play manifest are required. The function intentionally does not return a live `source_verifier` approval.

`acquisition_evidence` hashes actual response bytes and preserves the caller's observed receipt clock. It explicitly marks `publication_independently_attested=false`. The caller-supplied observed clock, prior completion claims or expected play counts are **not** trustworthy without separate evidence; a successful synthetic test never changes this status.

## Blockers ranked

1. Independently witnessed 2025 full-league + 2026 complete-to-cutoff game/PBP coverage and verified 2026 asset digest/response timestamp, with external fixture denominator and provider-version trace.
2. Independent clock/first-available evidence and tamper-evident private read-only storage. The gateway also imposes a 2-hour source-as-of freshness cutoff. A nightly asset that last changed more than two hours earlier cannot qualify merely because a client downloaded it now; **do not re-label retrieval time as provider-as-of**.
3. Actual retention/attribution policy for private raw payloads, including third-party upstream rights.
4. Same pre-lock immutable football stage and original F-ST first-publication receipt before kickoff.

No requests for paid Alexandria or other external data were made. **No live collection job was enabled.** Tests are synthetic feature-identity and rejection checks only.
