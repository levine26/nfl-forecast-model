# Week 5: successful Groq execution without a persisted accepted HUMAN Read

**Incident:** On October 10, 2026, failed-game recovery validated its 14 ChatGPT candidates but could not assemble all 15 games. Workflow [38104883036](https://github.com/levine26/nfl-forecast-model/actions/runs/38104883036) failed with `successful provider game 2026_05_TB_DAL is missing both published HUMAN prose and a validated Groq checkpoint`.

**Verified diagnosis:** `groq_provider_fallback.games` recorded 14 failed Groq games, but its absence of a failure for `2026_05_TB_DAL` did **not** establish authoritative accepted HUMAN prose. The current Week 5 preview was a deterministic fallback; the prior published provider artifact was Week 4; the same-roster validated Groq checkpoint did not restore. A historical Groq fragment retained outside the release is not publication-grade because it cites an unsuitable viewing/odds story.

## Generalized repair

`missing_accepted_editorial_authority` audits all current canonical game IDs against accepted provider records, recovered validated checkpoints and (only in legacy same-week mode) explicitly provider-researched preview artifacts. It distinguishes (a) Groq provider failure from (b) *missing accepted editorial persistence*, independent of the upstream API outcome.

The manifest importer allows a replacement for (b) **only when that game lacks accepted existing HUMAN authority**. A valid previously accepted Groq entry/checkpoint disqualifies it, preserving all existing successful articles. After full focused and slate-level validation, recovery status records `editorial_recovery_reason: missing_accepted_human_authority` without fabricating a Groq transport failure. All other games continue to obey existing authorization and immutable numerical forecast gates.

The updated manifest requests 15 games including TB–DAL. Its replacement candidate is a **pre-kickoff-focused research draft**, not a revision to the already immutable Thursday official forecast. Two direct first-party pregame reports are cited:

- Tampa Bay Buccaneers: [2026 Game Preview: Buccaneers-Cowboys, Week 5](https://www.buccaneers.com/news/2026-game-preview-buccaneers-cowboys-week-5) — published October 7, 2026.
- Dallas Cowboys: [Quinnen Williams on quick turnaround for Cowboys vs. Buccaneers](https://www.dallascowboys.com/news/quinnen-williams-on-quick-turnaround-for-cowboys-vs-buccaneers-i-m-not-tired) — published October 7, 2026.

The content discusses Jalon Daniels' protection and Williams' interior rush, with Tampa Bay's quick-release/movement counter and Dallas's passing response versus Bowles. Both sources predate the Thursday kickoff and no postgame result, hindsight result, or revised lock enters the human layer.

## Limitations and gates

This fixes a demonstrated **authority classification and recovery-authorization** gap in the legacy compatibility importer. It does not prove the fallback consumer session can generate autonomously in GitHub Actions. It does not bypass the verified-source/semantic-entailment requirement introduced in the shadow evidence contract, nor automatically promote shadow reads. The terminal workflow must still validate every game, run full-slate checks, preserve numerical locks and pass publication/Pages verification. An externally sourced live replacement does **not** become launch-grade solely by passing an existing URL-shape validator.

Any later promotion to a single editorial-ledger authority must retire this importer compatibility rule rather than retaining two parallel authorities.
