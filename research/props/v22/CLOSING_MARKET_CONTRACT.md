# LevLine Props 2.2 — Prospective Closing-Market / CLV Contract

Status: **FROZEN BEFORE FIRST PROPS 2.2 FUTURE-HOLDOUT RECEIPT**  
Research-only: yes  
Production authorization: no  
Contract: `levline-props-2.2-closing-market-v0.1`

This contract adds prospective closing-market evidence to the already frozen Props 2.2 holdout. It does not alter any forecast, challenger coefficient, signal, grading rule, or production output.

## 1. Source of truth

Closing observations come only from the append-only prospective Props market archive on `research-data/props-v2-market-archive`.

No sportsbook result page, outcome, later reconstructed quote, synthetic line, or retrospective API request may be used to manufacture a close.

Week 2 may not be backfilled. Closing evidence is available only for Props 2.2 source forecasts captured at or after the frozen Props 2.2 prospective boundary.

## 2. Immutable identity

Each closing event is keyed by the original immutable Props 2.1 source forecast SHA-256 and ID.

The exact source identity is:

- source Props 2.1 forecast SHA-256;
- source Props 2.1 forecast ID;
- game ID;
- player ID;
- prop type;
- kickoff UTC.

A closing event never mutates the source forecast or any Props 2.2 challenger receipt.

Conflicting duplicate closing events for the same source forecast SHA fail closed. Exact replay is idempotent.

## 3. Closing-capture chronology

For an original source forecast at time `F` and kickoff `K`, an eligible closing capture must satisfy:

`F <= capture_time < K`

The selected close is the **latest** eligible archived capture.

If multiple archive rows share the same latest timestamp, deterministic tie-breaking uses snapshot ID and market-artifact SHA-256.

A capture at or after kickoff is never eligible. A capture before the source forecast is not a valid close for that forecast.

## 4. Identity gate

Archive matching is exact on:

- game ID;
- player ID;
- prop type.

The archived kickoff must equal the source forecast kickoff.

Wrong game/player/prop rows cannot be substituted.

## 5. Original market basis

The original point-in-time market remains the source forecast's frozen market state.

For price CLV only, the archive is also used to recover an executable original-price basis. The original archive row must:

- match the exact source identity;
- be captured no later than the source forecast time;
- have the same original market threshold as the frozen source receipt for continuous props;
- when a source no-vig probability exists, agree with that original market probability within a small deterministic numerical tolerance.

The latest archive row satisfying those conditions is the original-price basis.

If it cannot be proved, price CLV is unavailable rather than inferred.

## 6. Line CLV

For continuous line markets:

- raw line move = closing consensus line - original market line;
- frozen model side = OVER when the frozen source model probability is >= 0.5, otherwise UNDER;
- side-oriented line CLV is positive when the original threshold was better than the closing threshold for that frozen side.

Thus:

- OVER: `closing_line - original_line`;
- UNDER: `original_line - closing_line`.

Binary touchdown markets do not receive continuous line CLV.

Line CLV is descriptive market movement, not a betting recommendation.

## 7. Same-threshold price CLV

Price CLV is reported only when an archived original quote and archived closing quote exist for the **identical threshold and frozen side**.

For continuous props, individual-book prices must have line exactly equal to the original frozen market line.

For binary yes/no props, the same event definition is required.

The best available archived price at each point is selected deterministically by decimal-odds value.

Report:

- original best American/decimal price;
- closing best American/decimal price;
- original and closing book keys;
- decimal-odds CLV = original decimal odds - closing decimal odds;
- implied-probability CLV in percentage points = 100 * (closing implied probability - original implied probability).

Positive values mean the original captured price was better than the later close for the same side and threshold.

If the threshold changed and no closing book still offers the original threshold, same-threshold price CLV is unavailable. It must not be approximated from a different line.

## 8. Evidence retained

Each immutable closing event preserves:

- source forecast identity and source receipt hash;
- source forecast timestamp and kickoff;
- frozen model side;
- original market line/probability;
- closing consensus line/probability;
- line CLV fields;
- original-price archive snapshot/timestamp/provider/provenance;
- closing archive snapshot/timestamp/provider/provenance;
- book count/dispersion where available;
- same-threshold price CLV fields when eligible;
- event SHA-256;
- `research_only=true`;
- `production_authorized=false`.

## 9. Evaluation boundary

Closing evidence is joined into Props 2.2 reporting by immutable source forecast SHA.

The evaluator must report original-market matched N and closing-market matched N separately.

CLV is secondary descriptive evidence. It does not change the frozen promotion minimums, challenger coefficients, Holm-Bonferroni family, or primary market-relative evaluation.

No automatic promotion is authorized by CLV.

## 10. Fail-closed rules

The matcher must fail closed on:

- conflicting duplicate source identities;
- conflicting duplicate closing events;
- malformed timestamps;
- post-kickoff archive rows considered as eligible evidence;
- kickoff mismatch for an otherwise exact identity;
- archive rows that are not research-only / production-unauthorized;
- partial or contradictory market provenance when provenance fields are present.

Missing eligible closing evidence is a valid unmatched state, not a zero CLV.

## 11. Governance

- no Week 2 closing backfill;
- no target outcomes consulted by selection;
- no F-ST or winner-model changes;
- no production Props label changes;
- no retrospective threshold search;
- no forecast or receipt mutation.
