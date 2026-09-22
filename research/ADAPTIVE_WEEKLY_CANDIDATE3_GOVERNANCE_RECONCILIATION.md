# Candidate 3 governance reconciliation

Status: **final closeout governance record**

Candidate ID: `ADAPTIVE-MARKET-PATH-INNOVATION-V1`

## First-freeze precedence

Two parallel research lanes created preregistration artifacts before the first successful target score:

1. **Authoritative first freeze** — commit `52cf402cd33da0e535ef963c7d98f9b4304ea208`, committed 2026-09-22T16:52:47Z.
   - primary lambda: **0.50**
   - primary EARLY band: T-2160..T-1440
   - primary LOCK band: T-360..T-120
   - evaluation implementation explicitly binds to this SHA.

2. Later parallel preregistration — commit `97a974228f202b6dcfb1ec4f72267d6e7216774b`, committed 2026-09-22T16:58:52Z.
   - primary lambda: 0.25
   - overlapping but non-identical robustness grid.

Both commits preceded the first successful target computation. Therefore the later file is not outcome-contaminated. However, the same Candidate ID cannot have two primary definitions. The program uses **first-freeze precedence**: `52cf402...` is the only authoritative Candidate 3 preregistration. The later `97a9742...` artifact is retained as a parallel-lane pre-outcome sensitivity record and may not replace the first-frozen primary after results are known.

This resolution is based on commit chronology only, not on which lambda scored better.

## Final-market reporting control chronology

The authoritative first-freeze preregistration at `52cf402...` already required a later-information final-market-only descriptive control.

A parallel JSON preregistration omitted that control initially and added it at commit `f204a38839991f98f76cd88336fb87fd88cad8b3` at 2026-09-22T16:59:38Z, before the first successful target computation.

A later duplicate documentation commit `56de02d2e2d20ca39d567c03fc6bbe887c69b71a` was committed at 2026-09-22T17:01:10Z, after a target result had already been computed. That duplicate addendum is therefore **post-result documentation**, not a new preregistration event. It does not change the candidate and is redundant because the final-market control was already present in the authoritative first freeze.

## Canonical execution binding

The canonical successful workflow run is `35757935130`.

Its machine evidence explicitly records:

- preregistration SHA: `52cf402cd33da0e535ef963c7d98f9b4304ea208`
- Candidate ID: `ADAPTIVE-MARKET-PATH-INNOVATION-V1`
- primary lambda: 0.50
- target sample: 272 regular-season 2025 games
- no completed 2026-season outcomes loaded
- no production changes.

No result from the later parallel preregistration is allowed to redefine the Candidate 3 primary finding.
