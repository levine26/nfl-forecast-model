# Sunday Signal ATS Grading Contract

## Purpose

Sunday Signal spread-pick performance is graded against the **actual market spread published with the ATS pick at the applicable official lock/snapshot**, not against any LevLine-generated fair spread, probability-implied presentation line, or expected-margin diagnostic.

## Canonical grading rule

For every published ATS pick, persist an immutable grading tuple at lock:

- `game_id`
- `ats_pick_team`
- `ats_market_spread_at_lock`
- `ats_locked_utc`
- market/source provenance sufficient to identify the captured line

Settlement uses the final game margin against `ats_market_spread_at_lock` from that tuple.

If the selected team's final margin plus its locked ATS spread is:

- greater than 0: **WIN**
- equal to 0: **PUSH**
- less than 0: **LOSS**

The locked grading tuple must not be changed because the market subsequently moves.

## Explicit non-grading fields

The following are analytical/presentation outputs and MUST NOT be used to settle or grade an ATS pick:

- LevLine fair spread
- probability-implied presentation line
- coherent public score
- expected-margin diagnostic
- any model-generated spread or margin estimate

Those fields may explain why LevLine likes a side, but they are not the bet's settlement line.

## Example

If LevLine's probability-implied fair/presentation line is San Francisco -6.5, but Sunday Signal publishes and locks San Francisco -3.5, a five-point San Francisco win is graded **WIN**. The -6.5 model line has no role in settlement.

## Invariants

1. ATS grading requires a captured market spread attached to the published pick. A missing locked market spread is a grading-data failure; the grader must not silently substitute a LevLine line.
2. Once the ATS pick is officially locked, the pick team and grading spread are immutable. Grading remains a separate postgame operation.
3. Model methodology, LevLine probabilities, `F-ST-01-FROZEN-2026`, and the public-forecast bridge are unchanged by this contract.
4. Historical ATS records should identify the exact spread used for settlement so results are reproducible and auditable.
5. Any automated ATS grader must test explicitly that model fair/presentation spread fields cannot be selected as fallback grading inputs.
