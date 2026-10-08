# Phase 4B — original official F-ST lock provenance audit (2026-10-08)

**Decision: FIRST-GIT-OCCURRENCE AUDIT IMPLEMENTED / FIRST-PUBLICATION UNPROVED / CAPTURE DISABLED.**

## Actual source finding

`outputs/prediction_history.csv` on inspected main includes game identity, `lock_status`, `lock_timestamp_utc`, `prediction_timestamp_utc`, locked F-ST and market probability and strategy IDs. Its current column header **does not include** `market_snapshot_timestamp_utc` or `market_freshness_status`, both required by `two_stage_gateway.seal_against_lock`. Consequently the original-row conversion must reject even a historical `LOCKED` row: these fields cannot be invented from `lock_timestamp_utc` or latest odds.

`src/nfl_forecast/publish.py` creates LOCKED rows locally before `.github/workflows/pregame.yml` commits/pushes `outputs/` to `main`. Git author/committer timestamps may precede or differ from actual first public availability, particularly when the workflow retries after branch races, fails its push, or market refresh later rewrites the same CSV. Existing `lock_verify.py` validates internal T-120, not external publication.

## Concrete original-lock first-occurrence forensic example

An actual repository audit of game `2026_01_NE_SEA` found the row in historical Git commit [`fc88ef398a310b75eea2bf189ab21d2296237d4e`](https://github.com/levine26/nfl-forecast-model/commit/fc88ef398a310b75eea2bf189ab21d2296237d4e), titled `Refresh LevLine final forecasts`. Its prior commit `8f16596ce1ffdce1a2d13e4ad327380161c63061` lacks that game row. At the first observed Git history blob, the row was marked `LOCKED` with `final_home_prob=0.6042095144550527`, `market_home_prob=0.6037569709421778`, `prediction_timestamp_utc=2026-09-09T22:43:57.474413+00:00`, `lock_timestamp_utc=2026-09-09T22:43:57.537836+00:00`, and kickoff `2026-09-10T00:20:00+00:00`. The Git commit author/committer clock is `2026-09-09T22:43:58Z` and the historical CSV blob Git SHA is `15eadd75d4a39fd0e76a4fda59915426ecc2f05d`.

**This is evidence of a Git-content transition, not authenticated original publication.** The Git parent and commit timestamps do not prove when the new commit first became visible; nor can its row create the missing original market source/freshness fields. It is useful to validate the offline auditor, **not** eligible for retroactive prospective Candidate C capture.

## Read-only original-blob audit

`original_lock_audit.py` takes **oldest-first actual Git history blobs** and their parent commit chain; rejects missing contents, noncontiguous sequences, malformed/duplicate rows and `RECOVERED_MISSED_LOCK`. Records earliest observed `LOCKED` CSV row, raw field digest, original entire history-blob digest and original probabilities *before any later CSV grade/market revision*. Explicitly records `first_publication_independently_verified=false` even if historical Git commit metadata are supplied. Does not create, infer or expose a verified gateway `lock_verifier` callback. Synthetic QA exercises first-vs-later row, missing market metadata and failed publication claims.

**Limit:** old first-parent Git traversal is NOT itself proof that every externally visible commit/event was observed at the time, nor proof of first-publication UTC. This adapter provides a verifiable immutable *content candidate*, not a trustworthy temporal receipt. A signed externally witnessed capture of the exact original SHA/row/received UTC must precede kickoff.

## Minimal future-facing receipt design (research-only)

Use a separate observer reading public GitHub state; it may run independently of the production lock writer. When a LOCKED row first becomes externally observable, register:
- UTC clock from an independently authenticated witness and error bound, witnessed commit SHA + Git blob SHA, exact original raw CSV row SHA, origin snapshot/receipt timestamp, and target game's official kickoff; distinguish first *observed* from first *published*.
- Continuous polling/coverage records or first-availability proof that excludes earlier records; prior observed absence is useful but not definitive proof of server-side first publication.
- Signed/TSA-anchored or independently audited append-only receipt with immutable retention + independently obtained nonce/receipt digest. Local `O_EXCL`, fsync and Github commit author time are insufficient.
- Market observation provenance from the actual original lock's source, not current history or subsequent market refresh. If absent, mark **ineligible**; do not change production writer under this research scope.

The response must fail closed on clock drift, delayed API visibility, missed polling intervals, retries, non-LOCKED recoveries, mutated original row, rescheduling, missing market source timestamps, or a proof received after kickoff.

## Remaining blockers

1. No independently authenticated actual original first-published/first-observed UTC receipt with continuous monitoring/durable timestamp authority.
2. Historical **missing original market snapshot/freshness columns** prevents this gateway's required verified market-time contract, even if Git first-row provenance is recovered.
3. No protected external append-only storage configured for received and scored research objects.
4. No live provider/schedule/capture qualification.

**Zero original-lock records have been qualified prospectively.** Source, frozen C model, official lock writer, published predictions and ATS remain unchanged.
