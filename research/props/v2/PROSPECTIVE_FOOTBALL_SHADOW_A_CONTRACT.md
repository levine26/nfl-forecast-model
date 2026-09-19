# LevLine Props 2.0 — Prospective Football Shadow A Capture Contract

Status: **FROZEN BEFORE SHADOW A PROSPECTIVE GRADING**  
Version: `levline-props-v2-football-shadow-a-v0.1.0`  
Production authorization: **NONE**  
Live-generation provenance amendment: 2026-09-19, before first Shadow A receipt

## Candidate

`P2-SHADOW-A-DEFENSE`

Published Props V1 plus only:
- strictly lagged opponent defensive-efficiency residual for rushing yards/carry;
- strictly lagged opponent defensive-efficiency residual for receiving yards/reception.

This is the primary football-mechanism candidate already defined by the master prospective shadow
contract. The implementation here starts immutable collection; it does not alter that candidate.

## Source boundary

A receipt may be created only from the full audit artifact of a **successful main-branch
`LevLine Props live refresh`**.

The runner must consume the frozen per-game integration manifests from that exact live run. V1's:
- player state;
- opportunity distributions;
- availability state;
- TD state;
- residual team efficiency;
- market snapshot;
- seed;
- simulation count;
- forecast timestamp;
remain unchanged.

The defense shadow may regenerate only rushing-yard and receiving-yard arrays.


## Live-generation provenance freeze

The GitHub workflow-run trigger SHA is not assumed to be the generation SHA. The source live audit
artifact must contain exactly one `source_provenance.json` under
`levline-props-live-source-provenance-v0.1.0` and its forecast/manifest hashes must verify before
Shadow A executes.

Every receipt preserves:
- source workflow run ID;
- actual generation-base SHA as `source_head_sha`;
- workflow trigger SHA as `source_trigger_head_sha`;
- source market provider and credential mode;
- SHA-256 of the live source-provenance record.

Both the trigger SHA and generation-base SHA must already contain this provenance-aware listener.
Runs predating this amendment are permanently ineligible for prospective Shadow A evidence. Provider
failover is metadata/provenance only and does not alter the frozen defensive-efficiency candidate.

## Frozen defense coefficients

Canonical file:
`research/props/v2/DEFENSIVE_EFFICIENCY_SHADOW_FROZEN.json`

It is the successful pre-2026 freeze from workflow `35421236153`, artifact `10577713358`.
The coefficients may never be refit because of 2026 grades.

## Current defensive state

For target season/week:
- use regular-season PBP strictly before the target week;
- apply V1's nflverse scramble normalization;
- rushing event = official rush attempt;
- receiving event = completed pass;
- league mean = all qualified prior event yards/event since 2019;
- opponent state = most recent 8 defensive games;
- shrink opponent event rate to league mean with 80 pseudo-events;
- feature = shrunk opponent yards/event minus league yards/event.

Same-week and target-game outcomes are excluded by construction.

## Paired simulation

1. Replay V1 from the frozen integration manifest using the manifest's exact simulation controls.
2. Deep-copy the V1 result.
3. Preserve all sampled opportunity arrays.
4. Regenerate only:
   - rushing yards from the existing carry array and adjusted yards/carry mean;
   - receiving yards from the existing reception array and adjusted yards/reception mean.
5. Use the exact deterministic RNG namespace from the passed retrospective candidate `levline-props-v2-defensive-efficiency-pregame-v0.1.0`; changing the wrapper/shadow version may not change the candidate draws.
6. Serialize only rushing-yard and receiving-yard shadow forecasts.

A receipt is invalid if any paired opportunity array changes.

## Immutable receipt

Every receipt must preserve:
- source workflow run;
- source season and NFL week;
- source forecast ID and SHA-256;
- source manifest SHA-256;
- game/player/prop identity;
- source and shadow timestamps;
- kickoff;
- original market line/probability;
- original V1 Fair Line/probability;
- lossless empirical V1 yardage distribution (support + counts) for proper-score grading;
- Shadow A Fair Line/probability/distribution summary;
- lossless empirical Shadow A yardage distribution (support + counts) for proper-score grading;
- frozen coefficient version and values;
- defensive-state feature and provenance;
- explicit production_authorized=false.

The receipt identity is source forecast ID + Shadow A version. Rewrites are prohibited.

## Eligibility

Fail closed unless:
- source workflow is successful and from main;
- source forecast and market are pregame;
- shadow recording occurs pregame;
- source manifest fingerprint verifies;
- prop type is rushing_yards or receiving_yards;
- stable player identity exists;
- target opponent defense state is available;
- no target-week outcome enters defensive state.

Started games are skipped, never reconstructed later.

Timing is evaluated twice for each game: before simulation and again after simulation immediately
before receipt creation. The authoritative receipt `recorded_utc` is the post-simulation timestamp.
If the job crosses kickoff while computing, no receipt may be written for that game.


## No retrospective backfill

Prospective evidence begins only after this listener is merged to `main`.

The capture job downloads and verifies the exact live artifact first, then checks out its recorded actual
generation-base SHA and executes the recorder from that source state. A live refresh whose source SHA predates the listener cannot be replayed later and
labeled prospective evidence. Missing or delayed pregame receipts remain missing; they are never
reconstructed after kickoff.

## Shadow B

`P2-SHADOW-B-DEFENSE-ROLE` remains frozen by the master contract but is **not implemented by this
listener**. Dynamic Role V0.1 changes opportunity generation and must be reproduced exactly before
its own prospective receipts begin. Do not approximate it post-simulation.

Any outcomes that occur before Shadow B's first immutable receipt cannot count toward Shadow B's
prospective sample.

## Evaluation boundary

No outcome is read by this capture workflow. Future grading is separate.

No production Props V1, Sunday Signal output, F-ST model, calibration, signal threshold, or betting
policy is modified.
