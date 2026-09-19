# LevLine Props 2.0 — Prospective Football Shadow B Capture Contract

Status: **FROZEN BEFORE SHADOW B PROSPECTIVE GRADING**  
Version: `levline-props-v2-football-shadow-b-v0.1.0`  
Candidate: `P2-SHADOW-B-DEFENSE-ROLE`  
Production authorization: **NONE**  
Live-generation provenance amendment: 2026-09-19, before first Shadow B receipt

## Candidate identity

Shadow B is the secondary candidate frozen by the master combination policy:

**Published Props V1 + frozen opponent defensive-efficiency residuals + Dynamic Role V0.1 full.**

It is distinct from Shadow A. Outcomes occurring before Shadow B's first immutable receipt are not
prospective Shadow B evidence.

## Point-in-time inputs

The listener may consume only:
- the full audit artifact of a successful **main-branch** `LevLine Props live refresh`;
- pre-2026 frozen defensive-efficiency coefficients;
- NFL history strictly before the target week for opponent defense state;
- NFL snap-count history strictly before the target week for Dynamic Role V0.1.

Target-week and target-game results are excluded.


## Live-generation provenance freeze

The source workflow trigger SHA and the SHA that actually generated the live artifact are distinct
provenance concepts. Shadow B requires exactly one `source_provenance.json` under
`levline-props-live-source-provenance-v0.1.0` and verifies its forecast/manifest/market hashes plus market-provider identity before
simulation.

Every receipt preserves the source workflow run ID, actual generation-base SHA
(`source_head_sha`), workflow trigger SHA (`source_trigger_head_sha`), market provider, market
credential mode and source-provenance SHA-256. Both trigger and generation SHAs must already contain
this provenance-aware listener and the frozen Dynamic Role/defense dependencies.

Runs predating this amendment are permanently ineligible. Provider failover changes neither Dynamic
Role V0.1 nor the defensive-efficiency candidate; it is immutable source metadata that must remain
matched between Shadow A and Shadow B.

## Dynamic Role V0.1

The exact tested V0.1 engine is reused:
- short snap-share half-life: 2 games;
- long snap-share half-life: 8 games;
- prior equivalent games: 2;
- multiplier bounds: 0.20 to 2.00;
- route level from short snap share / frozen position route prior;
- target and carry multipliers from short-vs-long snap-share trend;
- mode: `full`.

The role transform is applied to V1's captured opportunity artifact.

Before applying any non-unit multiplier the listener must reconstruct the captured V1 carry,
target and route distributions from the evidence retained in that artifact. Any mismatch fails the
slate closed. This proves the algebraic transformation remains the same opportunity engine used by
the tested candidate.

## Defense mechanism

Identical to canonical Shadow A / PR #394:
- frozen coefficients fit through 2025;
- opponent prior 8 defensive games;
- 80-event shrinkage to the prior league mean;
- strictly prior-week rushing and receiving events;
- role-adjusted opportunities are simulated first;
- the exact PR #394 post-simulation defense overlay then regenerates only rushing-yard and
  receiving-yard arrays from those role-adjusted carry/reception samples;
- the defense overlay uses the same retrospective mechanism version in its deterministic RNG
  namespace as PR #394.

## Pairing and receipts

For each eligible market-backed rushing-yard or receiving-yard source forecast:
1. replay V1 from the exact frozen source manifest;
2. verify V1 Fair Line / probabilities against the published source artifact;
3. construct Shadow B from the exact captured opportunity evidence plus strictly lagged role state;
4. apply frozen defense coefficients;
5. simulate with the source seed and simulation count;
6. record an immutable pre-kickoff receipt.

Every receipt preserves source forecast and manifest hashes, V1 and Shadow B distribution summaries,
immutable empirical distribution snapshots sufficient for later proper-score grading, market
line/probability, role multiplier/estimate provenance, defense-state provenance, and explicit
research-only governance.

## Fail-closed rules

No receipt if:
- source run is not successful on main;
- source or shadow recording is post-kickoff;
- complete two-way market evidence is unavailable;
- captured V1 opportunity distributions cannot be reconstructed;
- stable snap identity is unavailable;
- target-week history enters the role or defense state;
- source V1 replay differs from the published source artifact.

A source run is ineligible if its main-branch SHA predates the Shadow B listener itself; historical
live runs may not be replayed later to manufacture prospective evidence.

No production Props V1, Sunday Signal, F-ST model, calibration, or betting policy is modified.
