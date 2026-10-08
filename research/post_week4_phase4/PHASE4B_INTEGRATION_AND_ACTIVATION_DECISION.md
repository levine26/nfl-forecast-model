# Phase 4B — cross-adapter gateway QA and live capture decision (2026-10-08)

**Status: LIVE_SOURCE_QUALIFICATION_BLOCKED; RESEARCH TESTED; NO UNATTENDED COLLECTION.**
The official `F-ST-01-FROZEN-2026` incumbent, frozen Candidate C artifact and public forecasts are unchanged. This is not a new backtest and the synthetic fixtures never count toward prospective performance.

## Independent results in linked workstreams

- [PR #642](https://github.com/levine26/nfl-forecast-model/pull/642): source qualification and read-only NFLverse EPA adapter, fresh 2026 parquet verified in an isolated CI run. The 2026 asset SHA-256 was `9229849dc5bb221890beb64682707a9af9c0c872a60767c2614a48f12a4b83fe` at the 2026-10-08 16:57 UTC acquisition; against an independently downloaded NFLverse schedule, **64/64 listed completed REG game IDs** were present and each had some non-null EPA. No independently complete play manifest, pre-cutoff release witness, audited server clock, or legally reviewed retention configuration was obtained. The older October 7 PBP release hash differs, showing why the current file cannot reconstruct the historical pregame state.
- [PR #643](https://github.com/levine26/nfl-forecast-model/pull/643): first Git-history occurrence auditor and genuine lock blocker. Historical `LOCKED` row content may be recovered from actual original Git blobs, but commit author/committer timestamps are **not independently authenticated first-publication times**. The inspected `outputs/prediction_history.csv` does **not** contain the original `market_snapshot_timestamp_utc` or `market_freshness_status` required by the frozen two-stage gateway. Inserting these after publication would create an unqualified retroactive record.

## Synthetic integration contract

`test_phase4b_cross_adapter_integration.py` intentionally connects the actual **EPA adapter functions** and **read-only original lock auditor** to the existing `two_stage_gateway` in offline tests only. It covers:
1. deterministic regular-season team-game offense/defense EPA -> exact C prior-eight/current-all/previous-season-league means -> raw football stage -> unchanged frozen scorer -> idempotent post-lock seal, with explicitly synthetic verifier callbacks;
2. fake live qualification explicitly rejected before any football stage bytes are stored, with a failure ledger;
3. post-stage EPA revision cannot overwrite or revise a sealed input;
4. real-shaped historical Git commit/row with no independently witnessed first-published time cannot pass the gateway;
5. wrong team identity, missing previous game, late provider receipt and already-started game fail closed.

The positive path uses **test fakes** for the source and first-publication proof. It is **not evidence of any actual prospective capture**, even though the gateway emits a synthetic test record.

## Actual activation trust boundary and minimal safe future architecture

A qualified external source adapter must bind (a) actual provider payload hash, version, download completion time, verified independent response/source age, permitted private retention; (b) a separately complete fixture and per-game play manifest (including source revisions), 2025 season league reference and all prior 2026 games; (c) before-lock football snapshots containing **only** earlier-game information; (d) external GitHub first-seen/first-published evidence for the **same original** F-ST LOCKED row, including original market as-of and unmodified probability; and (e) an auditable trusted UTC clock and immutably persisted pre-kickoff scoring receipt.

Persist private raw bytes only after rights verification, via a non-public write-once storage service or independently signed/timestamped append-only audit ledger with retention policy and immutable object digests. A Git repository, local `O_EXCL` and `fsync` alone do **not** prove independent timestamps or WORM. Do not store licensed raw football data, provider credentials or pregame information in public `main`. A separately authorized research observer can monitor public Git commits; no modification to production `publish.py` or `pregame.yml` is permitted here.

If a provider revises the same file or a first-publication witness arrives after the initial kickoff, retain the rejection receipt. No timestamp reinterpretation, retrospective score or denominator filtering is permitted.

## Eligibility and evaluation

**Activation decision: NO.** No unattended collector, timer, scheduled task or production integration added. No genuinely sealed prospective Candidate C forecasts have been independently demonstrated by these PRs, so the Phase 4B verified numerator/denominator remain **0 candidate seals / 0 qualifying non-ties / 0 qualified weeks**. This report makes no inference that other unrelated repository experiments lack records; only this newly qualified Phase 4B trust chain is zero.

Formal review is prohibited until at least **200 newly eligible non-ties over at least 14 distinct NFL weeks**. Preserve paired F-ST comparison, week-block confidence intervals, Brier/log loss, calibration, complete missingness/ties, and the three legacy misclassified ties caveat. User retains explicit production-promotion approval.

## Next concrete milestone

1. **Highest scientific priority:** establish independent pre-lock source publication/capture clocks and complete game/play manifests at a trusted external append-only receipt endpoint.
2. **Next:** independently witness first publication of a *future* original F-ST LOCKED row and authenticate its original market source time/probability, or document the structurally missing fields as permanent non-eligibility.
3. **Then:** verify private lawful retention, robust schedule denominator, trusted clock bounds and end-to-end pre-kickoff seal; activate a **research-only** prospective collector if and only if all gates pass. No backfill.

All tests in this phase are engineering checks, not new accuracy evidence. Frozen C identity: `EARLY-STATE-SHRINKAGE-V1-SHADOW-2026-10-07`; immutable canonical SHA-256 `6af9358922321c3a03f9285df384e96cbe2d59f6d9780d2cd1ddf7d39c1ccdd5`.
