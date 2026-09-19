# Props 2.0 Market Archive Contract

Status: **FROZEN PROSPECTIVE DATA CAPTURE / RESEARCH ONLY**  
Version: `levline-props-v2-market-archive-v0.1.0`  
Exact-source provenance amendment: 2026-09-19, before first persistent archive capture  
Live-generation provenance amendment: 2026-09-19, before first provenance-eligible persistent archive capture

## Objective

Preserve the multi-book player-prop market state already captured by the live Props pipeline before
its 30-day GitHub Actions audit artifacts expire.

This lane performs **no additional sportsbook API request**. It consumes successful live audit
artifacts and archives their normalized `market.json` snapshots to an off-main research-data
branch.

## Preserved state

For each player/game/prop market artifact the archive retains:
- capture timestamp;
- kickoff timestamp and exact minutes to kickoff;
- player/game/prop identity;
- consensus line and no-vig probability;
- individual sportsbook identities, lines and prices already present in the normalized artifact;
- dispersion, best-price and movement fields already computed by the frozen market engine;
- SHA-256 of the normalized market artifact;
- SHA-256 provenance of the raw provider payload when available;
- source live-workflow run ID;
- actual generation-base SHA (`source_head_sha`);
- workflow trigger SHA;
- selected market provider and credential mode;
- SHA-256 of the live source-provenance record.

Raw provider payload bytes are **not** copied to the persistent research branch. Their digest is
preserved for provenance while avoiding unnecessary data duplication.

## Point-in-time gate

A snapshot is eligible only if:
- `research_only == true`;
- `production_authorized == false`;
- it contains non-empty normalized market artifacts;
- every archived game has a source-qualified kickoff;
- capture time is strictly before kickoff.

Post-kickoff snapshots fail closed.

## Exact source-run and generation boundary

The workflow-run event is only a trigger; its head SHA is not assumed to be the generation SHA.
Every archive capture must:
1. resolve the successful main-branch `LevLine Props live refresh` run;
2. download that exact run before checkout;
3. require exactly one `source_provenance.json` under
   `levline-props-live-source-provenance-v0.1.0`;
4. verify its workflow-run ID and trigger SHA against GitHub Actions metadata;
5. verify the normalized `market.json` hash and provider against the provenance record;
6. require both trigger SHA and actual generation-base SHA to contain this provenance-aware listener;
7. check out the actual generation-base SHA;
8. persist workflow run, generation SHA, trigger SHA, provider/mode and provenance SHA-256.

A live run predating the live-generation provenance listener is permanently ineligible for
provenance-eligible archive evidence. The first persistence event occurred before this amendment became
active and archived one 1,033-row normalized snapshot from source run `35428763144`. That snapshot
remains immutable for auditability but is excluded from preregistered horizon/CLV selection and all
promotion thresholds. It may not be rewritten, deleted, or retroactively upgraded. Manual dispatch may
not backfill it. Missing captures stay missing.

## Horizon policy

This archive does not retroactively label captures as OPEN/T−48h/etc. It preserves exact
`minutes_to_kickoff`. A separate preregistered horizon-selection contract must define tolerances
before outcome evaluation.

## Immutability

Snapshot identity is content-addressed from the canonical normalized snapshot. Duplicate content is
idempotent. New live states create new archive files. Existing archive rows are never rewritten.

## Governance

- No completed 2026 result is consumed.
- No V1 or F-ST forecast changes.
- No edge threshold.
- No production output mutation.
- Persistent evidence lives only on `research-data/props-v2-market-archive`.

## Activation boundary

The automatic `workflow_run` collector is not active merely because this research branch exists.
Prospective evidence collection begins only after this workflow is merged to `main` and a subsequent
successful `LevLine Props live refresh` run triggers the archive job. Until the first persistent
commit exists on `research-data/props-v2-market-archive`, the archive must be described as
implementation-ready rather than as an active evidence stream.

