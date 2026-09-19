# Props 2.0 Market Archive Contract

Status: **FROZEN PROSPECTIVE DATA CAPTURE / RESEARCH ONLY**  
Version: `levline-props-v2-market-archive-v0.1.0`  
Exact-source provenance amendment: 2026-09-19, before first persistent archive capture

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
- exact source live-workflow head SHA.

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

## Exact source-run boundary

The workflow-run event is only a trigger. Every archive capture must:
1. resolve the requested GitHub Actions run;
2. require workflow name `LevLine Props live refresh`, branch `main`, and conclusion `success`;
3. require that source head SHA to already contain the versioned exact-source archive listener;
4. check out that exact source head SHA;
5. download artifacts only from that exact workflow run;
6. persist both the source workflow run ID and source head SHA into the archive rows, manifest, and status.

A live run predating the exact-source listener is permanently ineligible for prospective archive evidence.
Manual dispatch may not be used to backfill an older run after the listener is merged. Missing captures stay
missing.

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

