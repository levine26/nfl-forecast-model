# Phase 4B — live-source readiness, denominator and two-stage integration (2026-10-08)

**STATUS: OFFLINE ADAPTERS/QA IMPLEMENTED; LIVE PROSPECTIVE COLLECTION NOT ACTIVATED.** Research only. Frozen Candidate C and official F-ST/published picks are not modified.

## Evidence captured

- Source lane: PR #642 and `PHASE4B_NFLVERSE_SOURCE_AUDIT.md`. A one-shot public 2026 PBP parquet download independently matched the GitHub release digest `9229849dc5bb221890beb64682707a9af9c0c872a60767c2614a48f12a4b83fe` (asset ID 622369252; 4,849,370 bytes). NFLverse current schedule displayed 64 completed REG games and the parquet held all 64 game IDs with no game lacking valid EPA. This does **not** prove per-play completeness, historical release availability, independent time attestation or storage rights.
- Lock lane: PR #643 and `PHASE4B_ORIGINAL_LOCK_AUDIT.md`. A directly inspected example: parent Git commit `8f16596ce1ffdce1a2d13e4ad327380161c63061` did not contain game `2026_01_NE_SEA`, while later commit `fc88ef398a310b75eea2bf189ab21d2296237d4e` has an original LOCKED row; its Git committer field reads 2026-09-09T22:43:58Z. Neither commit/author time nor the later API retrieval independently proves original public availability. The original CSV blob lacks original market observation/freshness columns, and Week 1's historic file predates certain frozen-F-ST metadata.
- Live contract: the current `two_stage_gateway` cannot truthfully accept public source and official-lock callbacks: the new source adapter explicitly refuses live verification, the lock auditor explicitly returns `gateway_live_verifier_ready=false`, and no independent append-only timestamp authority is deployed.
- The initial 2026 football PBP feed must be current, hash-pinned, complete to the exact pre-lock cutoff, and *retained only where permitted*; a six-hour nflreadpy cache or historic PBP fallback cannot substitute for a current-season source. A release's `updated_at` is not proof that it was available at every historical lock.
- The gateway's 2-hour source-as-of freshness constraint must not be bypassed by relabeling a fresh downloader's response time as the provider's original as-of version. A Sunday run using a much older nightly release will be rejected without a separately sufficient, actual source freshness record.

## New local integrity/denominator audit

`phase4b_integrity_audit.py` consumes an explicit separate schedule (not a list of favorable predictions) and read-only staged/prediction/failure objects. It verifies expected universe, uniqueness, schedule week/kickoff, stage hashes, forecast-to-stage link, frozen model digest, and score-clock cutoff; it detects local object corruption, missing stages, revision and records outside the denominator. It reports both missing and synthetic sealed games **without treating any as genuine qualified prospective observations**. The audit does not rewrite or grade a prediction, expose underlying raw game data, nor independently certify provider or official lock history.

`test_phase4b_integrity_audit.py` exercises the complete offline synthetic two-stage path and adapter-verifier refusal, in addition to corruption, schedule revision, unauthorized object, missing stage and duplicate schedule failure. All synthetic results remain `0` independently qualified.

## Minimum safe operational architecture still needed

1. **Source proof:** Source-specific 2025 + current 2026 complete play-by-play coverage, verified per-game manifest, corrections/version chronology, and original source license/retention terms with strict private storage.
2. **Original lock proof:** A pre-kickoff independent observer capturing original public LOCKED row, original probabilities/market fields, SHA-256 of exact CSV original and Git blob, an externally witnessed first-seen time and no earlier unseen first lock. `lock_timestamp_utc` and Git commit time cannot fill this.
3. **Durability:** Private append-only write-once storage (e.g. versioned Object Lock with legally verified retention and separated auditing credentials) or third-party signed timestamp authority, hash-chain failure and success receipts, clock drift bounds, monitored retries and independent external audit. A local `O_EXCL` is only a concurrency tool, not WORM.
4. **Chronology & source condition:** Independent schedule denominator, no after-cutoff response, wrong week/team, reschedule, source update or later market replacement; source clock/market clock/lock received/score-seal all independently bound before kickoff.
5. **Scientific outcome gate:** Retain all rejected/missing games in denominator, then later grade only official postgame outcomes; tie excluded but counted; >=200 genuinely new eligible non-ties across >=14 weeks before formal paired win-accuracy inference, week-block CIs, Brier/log loss/calibration and sensitivity. No training on 2026 results and no model promotion without explicit user approval.

### Count and decision

- Genuinely sealed, independently qualified Candidate C predictions: **0**.
- Qualified non-tie games: **0**. Qualified distinct weeks: **0**.
- External spending: **none authorized or incurred by this program**.
- Live automatic collection: **OFF**. Production promotion: **OFF**.
- Primary next engineering milestone: independently timestamped, retention-permitted original football source + original-F-ST-lock receipts prior to an actual future NFL kickoff; only then begin enrollment. Existing offline local QA must not be described as statistical evidence.
