# M1 Prospective Phase 1 Opening Receipt

Status: `OPENED_NOT_EXECUTED`

Program identity: `FV2-PROS-M1-MARKETSTATE-01`

Phase: `PROSPECTIVE PHASE 1 — CONTRACT ALIGNMENT AND CAPTURE QUALIFICATION`

Opening main SHA: `931c18063d03e5f1e5fa46732fb8fd36532696ff`

Opening branch: `research/ats-m1-prospective-phase1-opening`

## Authority and immutable scientific boundary

This phase executes the already-preregistered M1 market-state program. It does not create M1-v2, alter the frozen mechanism, choose a new target, change the null, add model families, or reopen historical fitting.

The authoritative scientific contract remains `research/ats-frontier-v2/M1_PREREGISTRATION.md`.

Frozen primary decision horizon remains `T-120`.

Predictor context may use only captures at or before `T-2160`, `T-720`, `T-360`, and `T-120`.

`T-60`, `T-30`, and latest-pre-kick are later-market diagnostic/evaluation states and may not enter the T-120 predictor. Existing `T-45` research infrastructure is not part of the frozen M1 predictor and may not be substituted for a missing M1 horizon.

The frozen 12-feature family, ridge model family, `{10,100}` regularization choice set, same-horizon market-state null, CPL proper-score primary endpoint, and path-feature ablation requirement remain unchanged.

Historical M1 remains `BLOCKED_PENDING_PAID_SOURCE`. No historical M1 fitting is authorized by this phase.

## Why this is the next authorized phase

The cross-program ATS roadmap is now merged on `main` and identifies M1 as the primary still-open new-information hypothesis. Frontier V2 already authorizes prospective M1 point-in-time capture/research while historical M3/M4 remain closed.

The repository already contains substantial generic prospective market infrastructure, so Phase 1 begins with qualification and contract alignment rather than rebuilding a collector.

## Outcome-blind opening evidence

At phase opening:

- `research_market_capture_v2.yml` runs a five-minute scheduled research collector and persists its append-only ledger away from `main`;
- `research_market_state_v1.yml` can derive a missingness-preserving point-in-time market-state artifact after a successful capture;
- current generic due logic uses `T-120m`, `T-60m`, `T-45m`, and `T-30m`;
- current generic market-state derivative is built around those same four horizons and post-T-120 movement pairs;
- the M1 predictor instead requires pre-decision context at `T-2160`, `T-720`, `T-360`, and `T-120`;
- the current research-data branch does not contain a `market_state_v1` derivative artifact;
- the latest preserved generic capture status at opening reports zero qualified rows and a missed `2026_03_ATL_GB:T-45m` attempt because event identity was unresolved.

These are infrastructure/provenance observations only. No completed-2026 game outcome was loaded or inspected to open this phase.

## Phase-1 objective

Make the existing prospective capture stack demonstrably capable of producing the exact point-in-time inputs required by frozen M1, with fail-closed semantics and without contaminating other research identities.

This is a data-contract and infrastructure qualification phase, not an M1 performance phase.

## Required Phase-1 work

1. Produce an exact implementation-to-preregistration field/horizon matrix.
2. Add or isolate the missing pre-decision M1 capture horizons `T-2160`, `T-720`, and `T-360` while preserving exact at-or-before timing semantics.
3. Preserve `T-120` as the decision-state horizon.
4. Preserve `T-60`, `T-30`, and latest-pre-kick as diagnostic/evaluation-only states; they must be inaccessible to the T-120 predictor.
5. Exclude existing `T-45` state from the M1 predictor identity.
6. Resolve event-identity matching under a deterministic, testable, point-in-time contract; unresolved identity must remain missing rather than repaired with later information.
7. Certify that the raw/derived schema can materialize all 12 frozen M1 features without outcome access.
8. Define one self-contained M1 book-count/quote-freshness eligibility contract rather than relying on ambiguous generic defaults.
9. Preserve append-only raw captures and an M1-specific immutable derivative/audit artifact away from production surfaces.
10. Add tests proving no after-horizon quote, post-kickoff observation, later diagnostic state, completed-game outcome, or production forecast can enter the M1 T-120 feature row.

## Phase-1 exit gate

Phase 1 may close only when all of the following are true:

- all frozen M1 predictor horizons are represented in tested capture logic;
- later diagnostic horizons are mechanically barred from predictor construction;
- event identity and kickoff revision handling are deterministic and fail closed;
- all 12 frozen feature families have explicit source-field provenance and missingness behavior;
- live/prospective storage remains append-only and research-only;
- an outcome-blind synthetic/fixture validation demonstrates exact M1 row construction;
- research firewall and research validation pass on the exact head;
- completed-2026 outcomes used for architecture, qualification, parameter tuning, or scoring remain `0`.

A future real-game capture is useful operational evidence but is not required to claim that code-level Phase-1 contract alignment is implemented. It is required before any empirical M1 prospective training/evaluation dataset can exist.

## Explicitly unauthorized in Phase 1

- outcome scoring;
- ATS accuracy or ROI inspection;
- fitting ridge coefficients;
- regularization selection;
- retrospective 2026 reconstruction;
- historical paid-source acquisition;
- changing the M1 feature family, model family, null, target, or evaluation metric;
- combining M1 with M2 or V3;
- production deployment or mutation.

## Exact next action

Perform the M1 implementation-gap audit in `M1_PROSPECTIVE_PHASE1_GAP_AUDIT.md`, then implement only the minimum research-only changes required to satisfy the frozen capture/input contract before any M1 outcome access.
